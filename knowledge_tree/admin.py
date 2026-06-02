from django.contrib import admin
from .models import CategoryNode
# Register your models here.


@admin.register(CategoryNode)
class KnowledgeTopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'search_keywords')