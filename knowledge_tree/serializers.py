from rest_framework import serializers
from .models import CategoryNode , Tag

class TagListField(serializers.ListField):
    child = serializers.CharField()
    def to_representation(self, data):
        return [tag.name for tag in data.all()]

class CategoryNodeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    tags = TagListField(read_only=True)

    class Meta:
        model = CategoryNode
        fields = [
            'id', 'name', 'guideline', 'zammad_group', 'workflow',
            'workflow_name', 'search_keywords','tags','children'
        ]

    def get_children(self, obj):
        active_children = obj.children.filter(is_active=True)

        if active_children.exists():
            return CategoryNodeSerializer(active_children, many=True).data
        return None

class CategoryNodeAdminSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False , write_only=True
    )

    class Meta:
        model = CategoryNode
        fields = [
            'id', 'name', 'parent', 'guideline', 'zammad_group',
            'workflow', 'tags', 'is_active'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['tags'] = [tag.name for tag in instance.tags.all()]
        return rep

    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        node = super().create(validated_data)
        self._set_tags(node, tags_data)
        return node

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)
        node = super().update(instance, validated_data)
        if tags_data is not None:
            self._set_tags(node, tags_data)
        return node

    def _set_tags(self, node, tags_data):
        tag_objs = []
        for t_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=t_name.strip())
            tag_objs.append(tag)
        node.tags.set(tag_objs)