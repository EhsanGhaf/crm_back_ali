from django.urls import path , include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'admin/forms', DynamicFormViewSet, basename='admin-forms')
router.register(r'admin/fields', FormFieldViewSet, basename='admin-fields')

urlpatterns = [
    #  GET /api/forms/category/5/
    path('category/<int:category_id>/', CategoryFormAPIView.as_view(), name='category-form'),

    path('admin/category/<int:category_id>/apply-form/<int:form_id>/', ApplyFormToCategoryAPIView.as_view(), name='apply-form-category'),

    path('admin/category/<int:category_id>/field/<int:field_id>/update/', UpdateCategoryFieldAPIView.as_view(), name='update-category-field'),

    path('admin/category/<int:category_id>/custom-field/', AddCustomFieldToCategoryAPIView.as_view(), name='add-custom-field'),

    path('', include(router.urls)),
]