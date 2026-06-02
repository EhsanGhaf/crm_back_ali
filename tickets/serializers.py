from rest_framework import serializers


class SubmitDynamicTicketSerializer(serializers.Serializer):
    # شناسه کاربر (شماره موبایل یا کد ملی)
    customer_identifier = serializers.CharField(max_length=50)

    firstname = serializers.CharField(max_length=150, default='کاربر', required=False, allow_blank=True)
    lastname = serializers.CharField(max_length=150, default='', required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=15, allow_null=True, required=False, allow_blank=True)
    national_id = serializers.CharField(max_length=15, allow_null=True, required=False, allow_blank=True)


    category_id = serializers.IntegerField()

    form_data = serializers.JSONField()