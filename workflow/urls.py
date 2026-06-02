from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ActionDefinitionViewSet,
    WorkflowViewSet,
    WorkflowStepViewSet,
    WorkflowRouteViewSet,
    ExecuteWorkflowView,
    TicketWorkflowStateAPIView
)

router = DefaultRouter()
router.register(r'actions', ActionDefinitionViewSet, basename='action')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'steps', WorkflowStepViewSet, basename='step')
router.register(r'routes', WorkflowRouteViewSet, basename='route')

urlpatterns = [
    path('', include(router.urls)),
    path('execute/', ExecuteWorkflowView.as_view(), name='execute-workflow'),
    path('state/<int:ticket_id>/', TicketWorkflowStateAPIView.as_view())
]