import logging
from .models import *
from tickets.services import get_ticketing_service

logger = logging.getLogger(__name__)

class WorkflowEngine:

    def __init__(self):
        self.ticket_service = get_ticketing_service()

    def start_workflow(self,ticket_id,workflow_id,user_full_name='سیستم'):

        try:
            start_step = WorkflowStep.objects.get(workflow_id=workflow_id, is_start_node=True)
            logger.info(f"Starting Workflow {workflow_id} for ticket {ticket_id} at step {start_step.id} ")
            return self.execute_step(ticket_id,start_step, user_full_name)

        except WorkflowStep.DoesNotExist:
            return {"error": 'گره شروع برای این گردشکار تعریف نشده است'}


    def process_transition(self,ticket_id,current_step_id,condition_value="",user_full_name='سیستم'):

        route = WorkflowRoute.objects.filter(
            from_step_id=current_step_id,
            condition_value=condition_value
        ).first()

        if not route:
            route = WorkflowRoute.objects.filter(
                from_step=current_step_id,
                condition_value=""
            ).first()

        if route:
            target_step = route.to_step
            logger.info(f"Moving ticket {ticket_id} to step {target_step.title} ")
            return self.execute_step(ticket_id,target_step,user_full_name)
        else:
            logger.info(f"End of Workflow for ticket {ticket_id} ")
            return {
                "status": "completed",
                "message": 'به پایان مسیر رسیدیم عملیات دیگری وجود ندارد'
            }

    def execute_step(self,ticket_id,step:WorkflowStep , user_full_name='سیستم'):

        action_code = step.action.code
        config = step.config or {}

        TicketWorkflowState.objects.update_or_create(
            ticket_id=ticket_id,
            defaults={'workflow': step.workflow, 'current_step': step}
        )

        if action_code == "CHANGE_GROUP" :
            target_group = config.get('target_group')
            allowed_user_ids = config.get('allowed_users',[])
            if target_group:
                success = self.ticket_service.update_ticket_group(ticket_id, target_group, by_user=user_full_name)

                if not success:
                    return {"status": "error",
                            "message": f"خطا در انتقال تیکت. مطمئن شوید گروه «{target_group}» در سیستم تیکتینگ وجود دارد."}
                logger.info(f"ticket {ticket_id} move to group {target_group}")

            route = WorkflowRoute.objects.filter(from_step=step , condition_value="").first()

            if route:
                next_step = route.to_step
                state, created = TicketWorkflowState.objects.update_or_create(
                    ticket_id=ticket_id,
                    defaults={'workflow': next_step.workflow, 'current_step': next_step}
                )

                if allowed_user_ids:
                    state.allowed_users.set(allowed_user_ids)
                else:
                    state.allowed_users.clear()

            else:
                TicketWorkflowState.objects.filter(ticket_id=ticket_id).delete()

            return {
                "status": "completed",
                "message": f"تیکت با موفقیت به کارتابل تیم «{target_group}» ارجاع داده شد."
            }

        elif action_code == "SEND_SMS":
            sms_text = config.get('sms_text')
            if sms_text:
                logger.info(f"✉️ Sending SMS for ticket {ticket_id}: {sms_text}")

            return self.process_transition(ticket_id, step.id, condition_value="")

        elif action_code == 'SHOW_RESOLUTION_MODAL':
            return {
                "status": "waiting_for_user",
                "current_step_id": step.id,
                "ui_type": "modal",
                "ui_data": {
                    "title": step.title,
                    "choices": config.get('choices', [])
                }
            }

        elif action_code == 'CLOSE_TICKET':
            self.ticket_service.update_ticket_state(ticket_id, 'closed')
            self.ticket_service.add_ticket_note(ticket_id, f"🔒 این تیکت توسط «{user_full_name}» (بسته) شد.")
            logger.info(f"Ticket {ticket_id} closed.")
            return {
                "status": "completed",
                "message": "تیکت با موفقیت بسته شد."
            }

        return {"status": "unknown_action", "message": f"اکشن {action_code} ناشناخته است."}




