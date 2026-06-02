from django.contrib.messages.api import success
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import requests
from sqlparse.engine.grouping import group

from .services import get_ticketing_service
from knowledge_tree.models import CategoryNode
from .serializers import SubmitDynamicTicketSerializer
from dynamic_forms.models import FormField, FormSubmissionValue

from workflow.engine import WorkflowEngine
from workflow.models import TicketWorkflowState


class TicketListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tab = request.query_params.get('tab', 'mine')
        page = int(request.query_params.get('page', 1))
        search_query = request.query_params.get('search', '').strip()

        user = request.user
        user_email = user.email if user.email else f"{user.username}@crm.local"
        zammad_query_parts = []

        workflow_ticket_ids = list(
            TicketWorkflowState.objects.filter(allowed_users=user).values_list('ticket_id', flat=True))
        workflow_ids_query = " OR ".join([f"id:{tid}" for tid in workflow_ticket_ids]) if workflow_ticket_ids else ""

        if tab == 'mine':
            if user.zammad_id:
                zammad_query_parts.append(f'owner.email:"{user_email}"')
            else:
                zammad_query_parts.append(f'owner.email:"{user_email}"')
        else:
            if user.is_superuser or user.is_staff:
                pass
            else:
                user_team_names = list(user.teams.filter(is_active=True).values_list('name', flat=True))

                if user_team_names:
                    groups_str = " OR ".join([f'group.name:"{name}"' for name in user_team_names])
                    base_group_query = f"({groups_str})"
                else:
                    base_group_query = f'group:"Users"'

                if workflow_ids_query:
                    zammad_query_parts.append(f"({base_group_query} OR {workflow_ids_query})")
                else:
                    zammad_query_parts.append(base_group_query)

        if search_query:
            zammad_query_parts.append(f"(title:*{search_query}* OR number:*{search_query}*)")

        final_query = " AND ".join(zammad_query_parts) if zammad_query_parts else "id:*"

        ticketing_service = get_ticketing_service()
        result = ticketing_service.get_paginated_tickets(query_string=final_query, page=page, per_page=10)

        if result is not None:
            return Response({
                "message": "لیست تیکت‌ها",
                "data": result["tickets"],
                "total_pages": result["total_pages"],
                "current_page": page
            }, status=status.HTTP_200_OK)

        return Response({"error": "خطا در دریافت لیست تیکت‌ها"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class SubmitTicketAPIView(APIView):
    def post(self, request):
        serializer = SubmitDynamicTicketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        identifier = data['customer_identifier']
        firstname = data.get('firstname', 'کاربر')
        lastname = data.get('lastname', 'مهمان')
        mobile = data.get('mobile')
        national_id = data.get('national_id')
        category_id = data['category_id']
        form_data = data['form_data']

        try:
            category = CategoryNode.objects.get(id=category_id, is_active=True)
        except CategoryNode.DoesNotExist:
            return Response(
                {"error": "دسته‌بندی مورد نظر در درخت دانش یافت نشد یا غیرفعال است."},
                status=status.HTTP_404_NOT_FOUND
            )

        message_body = f"یک درخواست جدید در دسته‌بندی «{category.name}» ثبت شد.\n\n(برای مشاهده اطلاعات تکمیل‌شده در فرم، به بخش جزئیات تیکت در پنل CRM مراجعه کنید)"

        field_ids = list(form_data.keys())
        fields_queryset = FormField.objects.filter(id__in=field_ids)
        fields_map = {str(f.id): f for f in fields_queryset}

        ticket_title = category.name

        user = request.user
        agent_email = user.email if user.email else f"{user.username}@crm.local"

        zammad_service = get_ticketing_service()
        zammad_res = zammad_service.create_ticket(
            title=ticket_title,
            identifier=identifier,
            message_body=message_body,
            firstname=firstname,
            lastname=lastname,
            mobile=mobile,
            national_id=national_id,
            group="Users",
            owner=agent_email,
        )

        if zammad_res:
            zammad_ticket_id = zammad_res.get('id')

            # ذخیره مقادیر فرم داینامیک
            for field_id_str, user_value in form_data.items():
                field_obj = fields_map.get(field_id_str)
                if not field_obj:
                    continue

                submission = FormSubmissionValue(
                    zammad_ticket_id=zammad_ticket_id,
                    field=field_obj
                )

                ftype = field_obj.field_type
                try:
                    if ftype in ['text', 'textarea', 'select','multiselect']:
                        submission.value_text = str(user_value)
                    elif ftype == 'int':
                        submission.value_int = int(user_value)
                    elif ftype == 'float':
                        submission.value_float = float(user_value)
                    elif ftype == 'bool':
                        submission.value_bool = str(user_value).lower() in ['true', '1', 'yes']
                    elif ftype == 'date':
                        submission.value_date = user_value

                    submission.save()
                except ValueError:
                    pass


            workflow_status = "completed"
            current_step_id = None
            ui_data = None

            if category.workflow:
                try:
                    user_full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
                    engine = WorkflowEngine()
                    engine_response = engine.start_workflow(zammad_ticket_id, category.workflow.id, user_full_name=user_full_name)

                    # بررسی اینکه آیا موتور روی نودِ SHOW_RESOLUTION_MODAL متوقف شده است؟
                    if engine_response and engine_response.get("status") == "waiting_for_user":
                        workflow_status = "waiting_for_user"
                        current_step_id = engine_response.get("current_step_id")
                        ui_data = engine_response.get("ui_data")

                except Exception as e:
                    # اگر موتور خطا داد، جلوی ساخته شدن تیکت را نمی‌گیریم، فقط لاگ می‌کنیم
                    print(f"❌ Workflow Engine Error on Submit: {e}")

            # بازگرداندن جواب نهایی به فرانت‌اِند
            return Response({
                "message": "تیکت با موفقیت ثبت شد.",
                "ticket_id": zammad_ticket_id,  # برای استفاده در اکشن‌های بعدی موتور
                "workflow_status": workflow_status,
                "current_step_id": current_step_id,
                "ui_data": ui_data
            }, status=status.HTTP_201_CREATED)

        return Response(
            {"error": "خطا در ارتباط با هسته تیکتینگ (Zammad)."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class CustomerProfileAPIView(APIView):
    def get(self, request, identifier):
        zammad_service = get_ticketing_service()

        # استخراج شماره بدون صفر اول برای جستجوی دقیق‌تر
        clean_id = identifier[1:] if identifier.startswith("09") else identifier
        search_query = f"email:\"{identifier}@crm.local\" OR mobile:*{clean_id}* OR national_id:\"{identifier}\""

        search_url = f"{zammad_service.base_url}/users/search?query={search_query}"

        try:
            search_res = requests.get(search_url, headers=zammad_service.headers)
            search_res.raise_for_status()
            users = search_res.json()

            if not users:
                return Response(
                    {"error": "کاربری با این شناسه یافت نشد."},
                    status=status.HTTP_404_NOT_FOUND
                )

            user = users[0]

            real_profile = {
                "identifier": identifier,
                "full_name": f"{user.get('firstname', '')} {user.get('lastname', '')}".strip(),
                "kyc_level": "ثبت شده در سیستم",
                "join_date": user.get('created_at', '')[:10]
            }

            # 🌟 استفاده از آیدیِ دقیقِ کاربرِ پیدا شده برای گرفتن تاریخچه
            user_id = user['id']
            tickets_url = f"{zammad_service.base_url}/tickets/search?query=customer_id:{user_id}&expand=true"
            tickets_res = requests.get(tickets_url, headers=zammad_service.headers)
            tickets_res.raise_for_status()
            raw_tickets = tickets_res.json()

            clean_tickets = []
            if isinstance(raw_tickets, list):
                # اگر متد get_resolution_codes در دسترس است از آن استفاده کنید، وگرنه هاردکد کنید
                NON_REOPENABLE_CODES = ['resolved_fl', 'duplicate']
                for t in raw_tickets:
                    state = t.get("state")
                    res_code = t.get("resolution_code")
                    created_at = t.get("created_at", "")
                    clean_tickets.append({
                        "id": t.get("id"),
                        "title": t.get("title"),
                        "state": "open" if state in ["open", "new"] else "closed",
                        "date": created_at[:10] if created_at else "",
                        "is_reopenable": False if (state == "closed" and res_code in NON_REOPENABLE_CODES) else True,
                        "resolution": res_code if state == "closed" else ""
                    })

            return Response({
                "message": "پروفایل مشتری با موفقیت دریافت شد.",
                "profile": real_profile,
                "tickets": sorted(clean_tickets, key=lambda x: x['id'], reverse=True)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"خطا در ارتباط با سرور: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TicketDetailAPIView(APIView):
    def get(self, request, ticket_id):
        zammad_service = get_ticketing_service()
        articles = zammad_service.get_ticket_articles(ticket_id)

        if articles:
            return Response({
                "ticket_id": ticket_id,
                "history": articles
            }, status=status.HTTP_200_OK)

        return Response({"message": "محتوایی برای این تیکت یافت نشد."}, status=status.HTTP_404_NOT_FOUND)


class TicketReplyAPIView(APIView):
    def post(self, request, ticket_id):
        body = request.data.get('body')

        if not body:
            return Response({"error": "متن یادداشت نمی‌تواند خالی باشد."}, status=status.HTTP_400_BAD_REQUEST)

        zammad_service = get_ticketing_service()
        result = zammad_service.add_ticket_note(ticket_id, body)

        if result:
            return Response({
                "message": "یادداشت شما با موفقیت ثبت شد.",
                "article_id": result.get('id')
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "خطا در ثبت یادداشت در Zammad."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TicketDynamicDataAPIView(APIView):
    """
    دریافت مقادیر فرمِ پر شده برای یک تیکت خاص (از دیتابیس لوکال خودمان)
    """

    def get(self, request, ticket_id):
        submissions = FormSubmissionValue.objects.filter(zammad_ticket_id=ticket_id).select_related('field')

        data = []
        for sub in submissions:
            ftype = sub.field.field_type
            val = None
            if ftype in ['text', 'textarea', 'select','multiselect']:
                val = sub.value_text
            elif ftype == 'int':
                val = sub.value_int
            elif ftype == 'float':
                val = sub.value_float
            elif ftype == 'bool':
                val = sub.value_bool
            elif ftype == 'date':
                val = sub.value_date

            data.append({
                "label": sub.field.label,
                "field_type": ftype,
                "value": val
            })

        return Response({"message": "دیتا با موفقیت دریافت شد", "data": data}, status=status.HTTP_200_OK)


class TicketStateUpdateAPIView(APIView):
    def patch(self, request, ticket_id):
        new_state = request.data.get('state')
        resolution_code = request.data.get('resolution_code')

        if new_state not in ['open', 'closed']:
            return Response({"error": "وضعیت نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        zammad_service = get_ticketing_service()
        success = zammad_service.update_ticket_state(ticket_id, new_state, resolution_code)

        if success:
            return Response({"message": f"وضعیت تیکت به {new_state} تغییر کرد."}, status=status.HTTP_200_OK)

        return Response({"error": "خطا در تغییر وضعیت تیکت."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ZammadGroupAPIView(APIView):

    def get(self, request):
        service = get_ticketing_service()
        groups = service.get_groups()
        return Response({
            "message": "لیست گروه ها دریافت شد",
            "data": groups
        }, status=status.HTTP_200_OK)

    def post(self, request):
        name = request.data.get('name')
        note = request.data.get('note','')

        if not name:
            return Response({"error": "نام گروه الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        service = get_ticketing_service()
        new_group = service.create_group(name=name, note=note)

        if new_group:
            return Response({
                "message": f"گروه '{name}' با موفقیت در سیستم تیکتینگ ساخته شد.",
                "data": new_group
            },status=status.HTTP_201_CREATED)

        return Response(
            {"error": "خطا در ارتباط با سرور تیکتینگ برای ساخت گروه."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ResolutionCodeListAPIView(APIView):

    def get(self, request):
        service = get_ticketing_service()
        codes = service.get_resolution_codes()

        if codes is not None:
            return Response({"message": "کدهای خاتمه دریافت شد.", "data": codes}, status=status.HTTP_200_OK)
        return Response({"error": "خطا در دریافت کدها از زمد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TicketAssignToMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        user = request.user
        agent_email = user.email if user.email else f"{user.username}@crm.local"

        full_name = f"{user.first_name} {user.last_name}".strip() or user.username

        zammad_service = get_ticketing_service()
        success = zammad_service.update_ticket_owner(ticket_id, agent_email)

        if success:
            system_message = f"✅ این درخواست توسط کارشناس «{full_name}» جهت بررسی و اقدام، به عهده گرفته شد."
            zammad_service.add_ticket_note(ticket_id, system_message)

            return Response({"message": "تیکت با موفقیت به کارتابل شخصی شما اضافه شد."}, status=status.HTTP_200_OK)
        return Response({"error": "خطا در تخصیص تیکت."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)