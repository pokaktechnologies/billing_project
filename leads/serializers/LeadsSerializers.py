from rest_framework import serializers
from ..models import *
from datetime import datetime, date
from django.utils import timezone
from accounts.serializers.serializers import SalesPersonSerializer
from accounts.models import SalesPerson, StaffProfile


class LeadSerializer(serializers.ModelSerializer):
    lead_status_display = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = [
            'CustomUser', 
            'lead_type', 
        ]

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


class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = '__all__'
        read_only_fields = ['id', 'created_at']
    def validate_types(self, value):
        allowed = ["call", "meeting", "email", "whatsapp"]

        if not isinstance(value, list):
            raise serializers.ValidationError("types must be a list")

        for v in value:
            if v not in allowed:
                raise serializers.ValidationError(f"Invalid type value: {v}")

        return value

class MeetingSerializer(serializers.ModelSerializer):
    date = serializers.DateField()
    time = serializers.TimeField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'lead', 'title', 'meeting_type', 'meeting_place',
            'description', 'status', 'date', 'time'
        ]



class MeetingSerializerDisplay(serializers.ModelSerializer):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_id = serializers.IntegerField(source='lead.id', read_only=True)
    phone = serializers.CharField(source='lead.phone', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = [
            'id', 'lead_name', 'lead_id', 'title', 'meeting_type',
            'meeting_place', 'description', 'date', 'time',
            'status', 'phone'
        ]


    def get_status(self, obj):
        return obj.get_status_display()

class RemindersSerializer(serializers.ModelSerializer):
    lead = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all())
    class Meta:
        model = Reminders
        fields = ['id', 'lead', 'title', 'type', 'date', 'time', 'description', 'status']


    def validate_type(self, value):
        valid_types = ['call', 'email', 'meeting', 'whatsapp']
        if value and value not in valid_types:
            raise serializers.ValidationError(f"Type must be one of: {', '.join(valid_types)}")
        return value

    def validate(self, data):
        lead = data.get('lead')
        date_val = data.get('date')
        time_val = data.get('time')

        # Required fields
        if not data.get('title'):
            raise serializers.ValidationError({"title": "Title is required."})
        if not data.get('type'):
            raise serializers.ValidationError({"type": "Type is required."})
        if date_val is None:
            raise serializers.ValidationError({"date": "Date is required."})
        if time_val is None:
            raise serializers.ValidationError({"time": "Time is required."})

        # Ownership check: ensure the requester can create/update reminders for this lead
        request = self.context.get('request')
        if request and lead:
            user = request.user
            if not (lead.CustomUser == user or lead.salesperson and lead.salesperson.assigned_staff and lead.salesperson.assigned_staff.user == user):
                raise serializers.ValidationError({"lead": "You do not have permission for this lead."})

        return data
    
class RemindersGetSerializer(serializers.ModelSerializer):
    lead = serializers.StringRelatedField()
    salesperson_name = serializers.CharField(source='lead.name', read_only=True, default=None)
    salesperson_phone = serializers.CharField(source='lead.phone', read_only=True, default=None)
    salesperson_email = serializers.CharField(source='lead.email', read_only=True, default=None)
    salesperson_lead_status = serializers.CharField(source='lead.lead_status', read_only=True, default=None)
    salesperson_company = serializers.CharField(source='lead.company', read_only=True, default=None)


    class Meta:
        model = Reminders
        fields = ['id', 'lead', 'title', 'type', 'date', 'time', 'description', 'status', 'salesperson_name', 'salesperson_phone',
                  'salesperson_email', 'salesperson_lead_status', 'salesperson_company']
    