from rest_framework import serializers
from .models import ActionDefinition,Workflow,WorkflowStep,WorkflowRoute


class ActionDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionDefinition
        fields = '__all__'

class WorkflowRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowRoute
        fields = '__all__'

class WorkflowStepSerializer(serializers.ModelSerializer):

    action_detail = ActionDefinitionSerializer(source='action', read_only=True)
    class Meta:
        model = WorkflowStep
        fields = '__all__'

class WorkflowDetailSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)
    routes = WorkflowRouteSerializer(many=True, read_only=True)
    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at', 'steps', 'routes']


class WorkflowListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
