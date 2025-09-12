from rest_framework import serializers
from .models import Certificate
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'full_name', 'start_date', 'end_date', 'designation', 'email', 'proof_document', 'category', 'status', 'requested_at', 'processed_at']
        read_only_fields = ['requested_at', 'processed_at']

    def validate(self, data):
        # Only validate dates if they are being updated
        if 'end_date' in data and 'start_date' in data and data['end_date'] < data['start_date']:
            raise serializers.ValidationError("End date must be after start date.")
        return data

    def update(self, instance, validated_data):
        try:
            if 'status' in validated_data and validated_data['status'] != instance.status:
                if validated_data['status'] in ['Approved', 'Rejected', 'Issued']:
                    validated_data['processed_at'] = timezone.now()
                elif validated_data['status'] == 'Pending' and instance.processed_at:
                    validated_data['processed_at'] = None
            return super().update(instance, validated_data)
        except Exception as e:
            logger.error(f"Error updating certificate {instance.id}: {str(e)}")
            raise  # Re-raise to propagate the error for debugging