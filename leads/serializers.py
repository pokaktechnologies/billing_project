from rest_framework import serializers
from .models import *
from datetime import datetime
from django.utils import timezone
from .models import Lead

class LeadSerializer(serializers.ModelSerializer):
    lead_status_display = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = '__all__'  # or specify the fields you want to include
        read_only_fields = ['CustomUser']  # optional

    def get_lead_status_display(self, obj):
        return obj.get_lead_status_display()


class MeetingSerializer(serializers.ModelSerializer):
    date = serializers.DateField(write_only=True)
    time = serializers.TimeField(write_only=True)
    datetime = serializers.DateTimeField(read_only=True, source='date')

    class Meta:
        model = Meeting
        fields = ['id','lead', 'date', 'time', 'datetime', 'status']

    def create(self, validated_data):
        date = validated_data.pop('date')
        time = validated_data.pop('time')
        combined_datetime = datetime.combine(date, time)
        validated_data['date'] = combined_datetime
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'date' in validated_data and 'time' in validated_data:
            date = validated_data.pop('date')
            time = validated_data.pop('time')
            combined_datetime = datetime.combine(date, time)
            validated_data['date'] = combined_datetime
        return super().update(instance, validated_data)

class MeetingSerializerDisplay(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    status = serializers.SerializerMethodField()
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_id = serializers.IntegerField(source='lead.id', read_only=True)

    class Meta:
        model = Meeting
        fields = ['id', 'lead_name','lead_id', 'date', 'time','status']

    def get_date(self, obj):
        return obj.date.date().isoformat()

    def get_time(self, obj):
        return obj.date.time().isoformat()
    
    def get_status(self, obj):
        return obj.get_status_display()

