from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
# Create your models here.


class ActionDefinition(models.Model):
    title = models.CharField(max_length=100, verbose_name='نام اکشن')
    code = models.CharField(max_length=100,unique=True,verbose_name='کد سیستمی')
    has_choices = models.BooleanField(default=False,verbose_name='آیا خروجی چندراهی دارد؟')
    description = models.TextField(blank=True, null=True,verbose_name='توضیخات اکشن')

    class Meta:
        verbose_name = 'تعریف اکشن'
        verbose_name_plural = 'تعریف اکشن ها'

    def __str__(self):
        return f"{self.title}({self.code})"


class Workflow(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='نام گردشکار')
    description = models.TextField(blank=True,null=True,verbose_name='توضیحات گردشگار')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'گردشکار'
        verbose_name_plural = 'گردشکارها'

    def __str__(self):
        return self.name



class WorkflowStep(models.Model):
    workflow = models.ForeignKey(Workflow,on_delete=models.CASCADE,related_name='steps')
    action = models.ForeignKey(ActionDefinition,on_delete=models.PROTECT,verbose_name='نوع اکشن')
    title = models.CharField(max_length=100, verbose_name='عنوان مرحله')
    is_start_node = models.BooleanField(default=False,verbose_name='آیا گره شروع است؟')
    config = models.JSONField(default=dict, blank=True,verbose_name='تنظیمات JSON')

    class Meta:
        verbose_name = 'مرحله گردشکار'
        verbose_name_plural = 'مراحل گردشکار'

    def __str__(self):
        return f"{self.workflow.title} -> {self.title}"


class WorkflowRoute(models.Model):
    workflow = models.ForeignKey(Workflow,on_delete=models.CASCADE,related_name='routes')
    from_step = models.ForeignKey(WorkflowStep,on_delete=models.CASCADE,related_name='outgoing_routes')
    to_step = models.ForeignKey(WorkflowStep,on_delete=models.CASCADE,related_name='incoming_routes')

    condition_value = models.CharField(max_length=255, blank=True,null=True,verbose_name='شرط عبور')

    class Meta:
        verbose_name = "مسیر گردش‌کار"
        verbose_name_plural = "مسیرهای گردش‌کار"

    def __str__(self):
        return f"From {self.from_step.title} To {self.to_step.title} (Condition: {self.condition_value})"


class TicketWorkflowState(models.Model):
    ticket_id = models.IntegerField(unique=True)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    current_step = models.ForeignKey(WorkflowStep, on_delete=models.SET_NULL, null=True)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='allowed_workflow_tickets',verbose_name='کاربران مجاز')
    def __str__(self):
        return f"Ticket {self.ticket_id} -> Step {self.current_step_id}"

