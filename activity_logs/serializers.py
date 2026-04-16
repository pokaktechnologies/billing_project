from rest_framework import serializers
from .models import ActivityLog


# Activity Log Serializer

class ActivityLogSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    class Meta:
        model = ActivityLog
        fields = '__all__'


class ActivityLogCreateSerializer(serializers.ModelSerializer):
    action = serializers.CharField()

    class Meta:
        model = ActivityLog
        fields = ['action', 'model_name', 'object_id', 'description']

    def validate_action(self, value):
        return value[:10]

    def validate_model_name(self, value):
        return value[:100]