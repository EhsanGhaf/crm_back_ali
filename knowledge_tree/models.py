from django.db import models

from workflow.models import Workflow


# Create your models here.

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='نام تگ')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CategoryNode(models.Model):
    name = models.CharField(max_length=255,verbose_name='عنوان دسته بندی')

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='سرخاشه (موضوع اصلی)'
    )

    guideline = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات",
    )

    zammad_group = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='category_nodes',
        verbose_name='گردشکار متصل'
    )

    search_keywords = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='جستجو'
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='nodes',
        verbose_name='تگ ها'
    )

    is_active = models.BooleanField(default=True,verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'درخت دانش'
        verbose_name_plural = 'درخت دانش'
        ordering = ('-created_at',)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        self.search_keywords = self.name
        super().save(*args, **kwargs)