from django.db import models

# Create your models here.
#

class DynamicForm(models.Model):

    title = models.CharField(max_length=255, verbose_name='عنوان فرم')
    description = models.TextField(null=True, blank=True, verbose_name='توضیحات فرم')
    is_active = models.BooleanField(default=True, verbose_name='وضعیت فعال بودن فرم')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class FormField(models.Model):
    TYPE_CHOICES = (
        ('text', 'متن'),
        ('textarea', 'متن بلند'),
        ('int', 'عدد صحیح'),
        ('float', 'عدد اعشاری'),
        ('bool','تاییده (checkbox)'),
        ('select','انتخابی (selectBox)'),
        ('multiselect', 'چندانتخابی'),
        ('date','تاریخ و زمان')
    )

    form = models.ForeignKey(DynamicForm, on_delete=models.CASCADE, null=True,blank=True, related_name='fields')
    label = models.CharField(max_length=255, verbose_name="برچسب فیلد")
    field_type = models.CharField(max_length=55, choices=TYPE_CHOICES,verbose_name='نوع فیلد')

    options = models.CharField(max_length=1550, null=True,blank=True, verbose_name='گزینه ها')

    required = models.BooleanField(default=False,verbose_name='فیلد اجباری است؟')
    is_active = models.BooleanField(default=True,verbose_name='فعال')
    order = models.PositiveIntegerField(default=0,verbose_name='ترتیب نمایش')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.label}({self.get_field_type_display()})"


class CategoryField(models.Model):
    category_node = models.ForeignKey('knowledge_tree.CategoryNode', on_delete=models.CASCADE,related_name='category_fields')
    field = models.ForeignKey(FormField, on_delete=models.CASCADE)

    is_active = models.BooleanField(default=True, verbose_name='فعال در این دسته')
    is_required = models.BooleanField(default=False,verbose_name='اجباری در این دسته')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب نمایش در این دسته')

    class Meta:
        ordering = ['order']
        unique_together = ('category_node', 'field')

    def __str__(self):
        return f"فیلد {self.field.label} در دسته {self.category_node.title}"


class FormSubmissionValue(models.Model):
    zammad_ticket_id = models.IntegerField(db_index=True, verbose_name="آیدی تیکت در سیستم")
    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name='submissions')

    value_text = models.TextField(null=True, blank=True)
    value_int = models.IntegerField(null=True, blank=True)
    value_float = models.FloatField(null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)
    value_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"مقدارِ {self.field.label} برای تیکت #{self.zammad_ticket_id}"
