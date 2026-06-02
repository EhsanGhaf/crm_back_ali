from django.urls import path , include
from rest_framework.routers import DefaultRouter
from .views import KnowledgeTreeAPIView , KnowledgeTreeSearchAPIView , CategoryNodeViewSet

router = DefaultRouter()
# This Router Address make These Addresses
# GET /api/knowledge/admin/nodes/ (لیست)
# POST /api/knowledge/admin/nodes/ (ساخت)
# PUT/DELETE /api/knowledge/admin/nodes/<id>/ (ویرایش و حذف)
router.register(r'admin/nodes', CategoryNodeViewSet, basename='admin-nodes')
urlpatterns = [
    path('tree/', KnowledgeTreeAPIView.as_view(), name='knowledge_tree'),
    path('search/', KnowledgeTreeSearchAPIView.as_view(), name='knowledge-search'),
    
    path('', include(router.urls)),
]