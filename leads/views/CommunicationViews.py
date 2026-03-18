from datetime import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from leads.models import CommunicationLog, CallDetail, EmailDetail, WhatsAppDetail
from leads.serializers.CommunicationSerializers import InitiateCommunicationSerializer, CallSummarySerializer, \
    CommunicationHistorySerializer


class InitiateCommunicationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateCommunicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_id = serializer.validated_data['lead_id']
        comm_type = serializer.validated_data['communication_type']
        phone = serializer.validated_data.get('phone')

        # Always outgoing
        communication = CommunicationLog.objects.create(
            lead_id=lead_id,
            communication_type=comm_type,
            direction='outgoing',
            status='initiated',
            created_by=request.user
        )

        # Create respective detail
        if comm_type == 'call':
            CallDetail.objects.create(
                communication=communication,
                phone_number=phone
            )

        elif comm_type == 'email':
            EmailDetail.objects.create(
                communication=communication,
                to_email=request.data.get('email'),
                subject=request.data.get('subject', ''),
                body=request.data.get('body', '')
            )

        elif comm_type == 'whatsapp':
            WhatsAppDetail.objects.create(
                communication=communication,
                phone_number=phone,
                message=request.data.get('message', '')
            )

        return Response({
            "message": "Communication initiated",
            "communication_id": communication.id
        })


class SubmitCallSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, communication_id):

        # Empty request check
        if not request.data:
            return Response(
                {"error": "No data provided"},
                status=400
            )

        try:
            communication = CommunicationLog.objects.get(id=communication_id)
            call_detail = communication.call_detail
            lead = communication.lead

        except CommunicationLog.DoesNotExist:
            return Response({"error": "Communication not found"}, status=404)

        # Prevent duplicate submission
        if communication.status == 'completed':
            return Response(
                {"error": "Summary already submitted"},
                status=400
            )

        serializer = CallSummarySerializer(
            call_detail,
            data=request.data  # ❗ removed partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update communication
        communication.status = 'completed'
        communication.notes = serializer.validated_data.get('summary')
        communication.save()

        # Update lead
        lead.last_contacted_at = timezone.now()

        if serializer.validated_data.get('follow_up_required'):
            lead.lead_status = 'follow_up'
        else:
            lead.lead_status = 'contacted'

        lead.save()

        return Response({
            "message": "Call summary saved successfully"
        })


class CommunicationHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):

        queryset = CommunicationLog.objects.filter(lead_id=lead_id)\
            .select_related('call_detail', 'email_detail', 'whatsapp_detail')\
            .order_by('-created_at')

        # filtering
        comm_type = request.query_params.get('type')
        if comm_type:
            queryset = queryset.filter(communication_type=comm_type)

        serializer = CommunicationHistorySerializer(queryset, many=True)
        return Response(serializer.data)


# incoming logs
class ManualCommunicationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lead_id = request.data.get("lead_id")
        comm_type = request.data.get("communication_type")
        notes = request.data.get("notes")
        phone = request.data.get("phone")

        communication = CommunicationLog.objects.create(
            lead_id=lead_id,
            communication_type=comm_type,
            direction='incoming',
            status='completed',
            notes=notes,
            created_by=request.user
        )

        # Create detail also
        if comm_type == 'call':
            CallDetail.objects.create(
                communication=communication,
                phone_number=phone,
                summary=notes
            )

        return Response({
            "message": "Incoming communication logged",
            "id": communication.id
        })
