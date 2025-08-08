from rest_framework import serializers
from .models import *
from datetime import datetime
from django.utils import timezone
from accounts.serializers.serializers import SalesPersonSerializer

class LeadSerializer(serializers.ModelSerializer):
    lead_status_display = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = '__all__'  # or specify the fields you want to include
        read_only_fields = ['CustomUser']  # optional

    def get_lead_status_display(self, obj):
        return obj.get_lead_status_display()


class LeadSerializerListDisplay(serializers.ModelSerializer):
    lead_status_display = serializers.SerializerMethodField()
    salesperson_first_name = serializers.CharField(source='salesperson.first_name', read_only=True, default=None)
    salesperson_last_name = serializers.CharField(source='salesperson.last_name', read_only=True, default=None)
    quotation_number = serializers.CharField(source='quotation.quotation_number', read_only=True, default=None)
    qoutation_grand_total = serializers.DecimalField(source='quotation.grand_total', read_only=True, default=None, max_digits=10, decimal_places=2)

    class Meta:
        model = Lead
        fields = "__all__"  # or specify the fields you want to include

    def get_lead_status_display(self, obj):
        return obj.get_lead_status_display()

class LeadSerializerDetailDisplay(serializers.ModelSerializer):
    lead_status_display = serializers.SerializerMethodField()
    salesperson_detail = SalesPersonSerializer(source='salesperson', read_only=True, default=None)

    class Meta:
        model = Lead
        fields = '__all__' 

    def get_lead_status_display(self, obj):
        return obj.get_lead_status_display()

class MeetingSerializer(serializers.ModelSerializer):
    date = serializers.DateField(write_only=True)
    time = serializers.TimeField(write_only=True)
    datetime = serializers.DateTimeField(read_only=True, source='date')

    class Meta:
        model = Meeting
        fields = ['id','lead','subject', 'date', 'time', 'datetime', 'status']

    def create(self, validated_data):
        date = validated_data.pop('date')
        time = validated_data.pop('time')
        combined_datetime = datetime.combine(date, time)
        validated_data['date'] = combined_datetime
        # check the lead is cooresponding to the user
        lead = validated_data.get('lead')
        if lead and lead.CustomUser != self.context['request'].user:
            raise serializers.ValidationError("You do not have permission to create a meeting for this lead.")
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
    phone = serializers.CharField(source='lead.phone', read_only=True)

    class Meta:
        model = Meeting
        fields = ['id', 'lead_name','subject','lead_id', 'date', 'time','status','phone']

    def get_date(self, obj):
        return obj.date.date().isoformat()

    def get_time(self, obj):
        # return obj.date.time().isoformat()
        return obj.date.strftime("%I:%M %p")
    
    def get_status(self, obj):
        return obj.get_status_display()

