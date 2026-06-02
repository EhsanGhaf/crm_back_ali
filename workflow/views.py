from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActionDefinition, Workflow, WorkflowStep, WorkflowRoute , TicketWorkflowState
from .engine import WorkflowEngine
from .serializers import (
    ActionDefinitionSerializer,
    WorkflowListSerializer,
    WorkflowDetailSerializer,
    WorkflowStepSerializer,
    WorkflowRouteSerializer
)
# Create your views here.

class ActionDefinitionViewSet(viewsets.ModelViewSet):
    """ API برای مدیریت ابزارهای پایه سیستم """
    queryset = ActionDefinition.objects.all()
    serializer_class = ActionDefinitionSerializer

class WorkflowViewSet(viewsets.ModelViewSet):
    """ API برای مدیریت ظرف‌های گردش‌کار """
    queryset = Workflow.objects.all()

    def get_serializer_class(self):
        # اگر درخواست برای دیدن یک رکورد خاص بود (Detail)، سریالایزر کامل را بده
        if self.action in ['retrieve']:
            return WorkflowDetailSerializer
        # در غیر این صورت (مثلاً دیدن لیست همه)، سریالایزر سبک را بده
        return WorkflowListSerializer

class WorkflowStepViewSet(viewsets.ModelViewSet):
    """ API برای ساخت و ویرایش گره‌ها = """
    queryset = WorkflowStep.objects.all()
    serializer_class = WorkflowStepSerializer

class WorkflowRouteViewSet(viewsets.ModelViewSet):
    """ API برای ساخت و ویرایش مسیرها (فلش‌ها) """
    queryset = WorkflowRoute.objects.all()
    serializer_class = WorkflowRouteSerializer

class ExecuteWorkflowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        ticket_id = request.data.get('ticket_id')
        workflow_id = request.data.get('workflow_id')
        current_step_id = request.data.get('current_step_id')
        condition_value = request.data.get('condition_value')

        if not ticket_id:
            return Response({"error": "آیدی تیکت (ticket_id) الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user_full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        engine = WorkflowEngine()

        try:
            if workflow_id and not current_step_id:
                result = engine.start_workflow(ticket_id, workflow_id, user_full_name=user_full_name)
                return Response(result, status=status.HTTP_200_OK)

            elif current_step_id:
                result = engine.process_transition(ticket_id, current_step_id, condition_value, user_full_name=user_full_name)
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "باید یا workflow_id برای شروع، یا current_step_id برای ادامه ارسال شود."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response({"error": f"خطای سیستمی در موتور اجرا: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TicketWorkflowStateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        state = TicketWorkflowState.objects.filter(ticket_id=ticket_id).first()
        if state and state.current_step:
            step = state.current_step
            return Response({
                "current_step_id": step.id,
                "ui_data": {
                    "title": step.title,
                    "choices": step.config.get('choices', []) if step.config else []
                }
            }, status=status.HTTP_200_OK)

        return Response({"current_step_id": None}, status=status.HTTP_200_OK)