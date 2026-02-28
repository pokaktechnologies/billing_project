from rest_framework import serializers
from .models import ActivityLog


# Activity Log Serializer

class ActivityLogSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    class Meta:
        model = ActivityLog
        fields = '__all__'