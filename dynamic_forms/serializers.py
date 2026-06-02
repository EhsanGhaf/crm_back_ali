from rest_framework import serializers
from .models import CategoryField , FormField , DynamicForm

class CategoryFormSerializer(serializers.ModelSerializer):
    field_id = serializers.IntegerField(source='field.id')
    label = serializers.CharField(source='field.label')
    field_type = serializers.CharField(source='field.field_type')
    options = serializers.CharField(source='field.options', read_only=True)
    required = serializers.BooleanField(source='is_required')

    class Meta:
        model = CategoryField
        fields = ['field_id', 'label', 'field_type','options', 'required', 'order']


class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = ['id', 'label', 'field_type','options', 'required', 'is_active', 'order']

class DynamicFormSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = DynamicForm
        fields = ['id', 'title', 'description', 'is_active', 'created_at', 'fields']