from django.contrib import admin
from .models import ActionDefinition, Workflow, WorkflowStep, WorkflowRoute, TicketWorkflowState

@admin.register(ActionDefinition)
class ActionDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'has_choices')
    search_fields = ('title', 'code')
    list_filter = ('has_choices',)

class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 1

class WorkflowRouteInline(admin.TabularInline):
    model = WorkflowRoute
    extra = 1
    fk_name = 'workflow'

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [WorkflowStepInline, WorkflowRouteInline]

@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ('title', 'workflow', 'action', 'is_start_node')
    list_filter = ('workflow', 'is_start_node', 'action')
    search_fields = ('title',)

@admin.register(WorkflowRoute)
class WorkflowRouteAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'from_step', 'to_step', 'condition_value')
    list_filter = ('workflow',)

@admin.register(TicketWorkflowState)
class TicketWorkflowStateAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'workflow', 'current_step')
    search_fields = ('ticket_id',)