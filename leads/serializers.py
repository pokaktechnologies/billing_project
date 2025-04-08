from rest_framework import serializers
from .models import Lead

class LeadSerializer(serializers.ModelSerializer):
    lead_status_display = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = '__all__'  # or specify the fields you want to include
        read_only_fields = ['CustomUser']  # optional

    def get_lead_status_display(self, obj):
        return obj.get_lead_status_display()
