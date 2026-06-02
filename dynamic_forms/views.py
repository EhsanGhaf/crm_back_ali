from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from django.db import transaction
from knowledge_tree.models import CategoryNode
from .serializers import CategoryFormSerializer , FormFieldSerializer , DynamicFormSerializer
from .models import FormSubmissionValue, FormField , CategoryField , DynamicForm

def save_ticket_dynamic_data(ticket_id, form_data):
    for field_id, user_val in form_data.items():
        try:
            field_obj = FormField.objects.get(id=field_id)
            submission = FormSubmissionValue(
                zammad_ticket_id=ticket_id,
                field=field_obj
            )

            ftype = field_obj.field_type

            if ftype in ['text', 'textarea', 'select', 'multiselect']:
                if isinstance(user_val, list):
                    submission.value_text = ",".join(map(str, user_val))
                else:
                    submission.value_text = str(user_val)

            elif ftype == 'int':
                submission.value_int = int(user_val)

            elif ftype == 'float':
                submission.value_float = float(user_val)

            elif ftype == 'bool':
                submission.value_bool = str(user_val).lower() in ['true', '1', 'yes']

            elif ftype == 'date':
                submission.value_date = user_val

            submission.save()

        except FormField.DoesNotExist:
            continue
        except (ValueError, TypeError):
            pass


class CategoryFormAPIView(APIView):
    def get(self, request, category_id):
        fields = CategoryField.objects.filter(
            category_node_id=category_id,
            is_active=True,
            field__is_active=True
        ).select_related('field')

        if not fields.exists():
            return Response(
                {"message": "هیچ فرمی برای این دسته‌بندی یافت نشد یا فرم غیرفعال است.", "data": []},
                status=status.HTTP_200_OK
            )

        serializer = CategoryFormSerializer(fields, many=True)

        return Response({
            "message": "فیلدهای فرم با موفقیت دریافت شد.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class DynamicFormViewSet(viewsets.ModelViewSet):
    queryset = DynamicForm.objects.all().order_by('-created_at')
    serializer_class = DynamicFormSerializer

class FormFieldViewSet(viewsets.ModelViewSet):
    queryset = FormField.objects.all()
    serializer_class = FormFieldSerializer

    def perform_create(self, serializer):
        form_id = self.request.data.get('form_id')
        serializer.save(form_id=form_id)


class ApplyFormToCategoryAPIView(APIView):
    """
    این API یک فرم (شابلون) را می‌گیرد و تمام فیلدهایش را به یک دسته‌بندی از درخت دانش وصل می‌کند.
    """

    @transaction.atomic  # برای اینکه اگه وسط کار ارور داد، دیتابیس خراب نشه
    def post(self, request, category_id, form_id):
        try:
            category = CategoryNode.objects.get(id=category_id)
            form = DynamicForm.objects.get(id=form_id)
        except (CategoryNode.DoesNotExist, DynamicForm.DoesNotExist):
            return Response({"error": "دسته‌بندی یا فرم یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # تمام فیلدهای این فرم رو می‌گیریم
        form_fields = FormField.objects.filter(form=form, is_active=True)

        created_count = 0
        for field in form_fields:
            _, created = CategoryField.objects.get_or_create(
                category_node=category,
                field=field,
                defaults={'order': field.order, 'is_active': True, 'is_required': field.required}
            )
            if created:
                created_count += 1

        return Response({
            "message": f"تعداد {created_count} فیلد از فرم '{form.title}' با موفقیت به دسته‌بندی '{category.name}' متصل شد."
        }, status=status.HTTP_200_OK)


class UpdateCategoryFieldAPIView(APIView):  # اسمش رو از Toggle عوض کردم چون حالا دو کار انجام میده
    def patch(self, request, category_id, field_id):
        category_field = get_object_or_404(CategoryField, category_node_id=category_id, field_id=field_id)

        # 🌟 آپدیت همزمان فعال بودن و اجباری بودن
        if 'is_active' in request.data:
            category_field.is_active = bool(request.data['is_active'])
        if 'is_required' in request.data:
            category_field.is_required = bool(request.data['is_required'])

        category_field.save()
        return Response({"message": "تنظیمات فیلد در این دسته بروزرسانی شد."})


class AddCustomFieldToCategoryAPIView(APIView):
    """
    این API یک فیلد کاملاً اختصاصی می‌سازد که به هیچ فرمی وصل نیست و فقط مال همین دسته‌است.
    """

    @transaction.atomic
    def post(self, request, category_id):
        category = get_object_or_404(CategoryNode, id=category_id)

        new_field = FormField.objects.create(
            form=None,
            label=request.data.get('label'),
            field_type=request.data.get('field_type'),
            required=request.data.get('is_required', False)
        )

        CategoryField.objects.create(
            category_node=category,
            field=new_field,
            is_active=True,
            is_required=new_field.required,
            order=99
        )

        return Response({"message": "فیلد اختصاصی با موفقیت اضافه شد."}, status=status.HTTP_201_CREATED)