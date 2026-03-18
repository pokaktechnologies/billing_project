from rest_framework import serializers

from leads.models import CallDetail, CommunicationLog, EmailDetail, WhatsAppDetail


class InitiateCommunicationSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    communication_type = serializers.ChoiceField(choices=['call', 'email', 'whatsapp'])
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class CallSummarySerializer(serializers.ModelSerializer):

    class Meta:
        model = CallDetail
        fields = [
            'call_status',
            'duration',
            'summary',
            'follow_up_required',
            'follow_up_date'
        ]

    def validate(self, data):

        # Call status vldtion
        if not data.get('call_status'):
            raise serializers.ValidationError({
                "call_status": "This field is required."
            })

        # Summary vald
        if not data.get('summary'):
            raise serializers.ValidationError({
                "summary": "Summary is required."
            })

        # Follow-up validation
        if data.get('follow_up_required') and not data.get('follow_up_date'):
            raise serializers.ValidationError({
                "follow_up_date": "Follow-up date is required when follow-up is enabled."
            })

        return data


class CommunicationHistorySerializer(serializers.ModelSerializer):

    type = serializers.CharField(source='communication_type')
    date = serializers.DateTimeField(source='created_at')
    data = serializers.SerializerMethodField()

    class Meta:
        model = CommunicationLog
        fields = [
            'id',
            'type',
            'direction',
            'status',
            'date',
            'notes',
            'data',
        ]

    def get_data(self, obj):

        # CALL
        if obj.communication_type == 'call' and hasattr(obj, 'call_detail'):
            return {
                "phone": obj.call_detail.phone_number,
                "call_status": obj.call_detail.call_status,
                "duration": obj.call_detail.duration,
                "summary": obj.call_detail.summary,
                "follow_up_required": obj.call_detail.follow_up_required,
                "follow_up_date": obj.call_detail.follow_up_date,
            }

        # EMAIL
        if obj.communication_type == 'email' and hasattr(obj, 'email_detail'):
            return {
                "to_email": obj.email_detail.to_email,
                "subject": obj.email_detail.subject,
                "body": obj.email_detail.body,
                "is_read": obj.email_detail.is_read,
            }

        # WHATSAPP
        if obj.communication_type == 'whatsapp' and hasattr(obj, 'whatsapp_detail'):
            return {
                "phone": obj.whatsapp_detail.phone_number,
                "message": obj.whatsapp_detail.message,
            }
        return None


class EmailDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailDetail
        fields = ['to_email', 'subject', 'body']


class WhatsAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppDetail
        fields = ['phone_number', 'message']


