from rest_framework import serializers
from ..models import PayrollPeriod

class PayrollPeriodSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    

    class Meta:
        model = PayrollPeriod
        fields = ['id', 'month', 'status', 'status_display', 'generated_at']
        read_only_fields = ['generated_at']
