from rest_framework import serializers
from ..models import Holiday
from django.utils import timezone

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'date', 'name', 'is_paid']
        
    def validate_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError(
                "Past dates cannot be added as holidays."
            )
        return value