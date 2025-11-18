from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasModulePermission
from ..serializers.LeadsSerializers import *
from accounts.models import SalesPerson, StaffProfile


class AdminLeadsView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'leads_management'

    def get(self, request):
        # Base queryset
        leads = Lead.objects.filter(lead_type="assigned_lead")

        # --- Filters ---
        salesperson_filter = request.query_params.get("salesperson")  # "null", "not_null"
        lead_source = request.query_params.get("lead_source")         # numeric id
        start_date = request.query_params.get("start_date")           # YYYY-MM-DD
        end_date = request.query_params.get("end_date")               # YYYY-MM-DD
        name = request.query_params.get("name")                       # string search

        # Filter salesperson null or not null
        if salesperson_filter == "null":
            leads = leads.filter(salesperson__isnull=True)

        if salesperson_filter == "not_null":
            leads = leads.filter(salesperson__isnull=False)

        # Filter by lead source
        if lead_source:
            leads = leads.filter(lead_source=lead_source)

        # Filter by name (case-insensitive)
        if name:
            leads = leads.filter(name__icontains=name.strip())

        # Filter by date range
        if start_date:
            leads = leads.filter(created_at__date__gte=start_date)

        if end_date:
            leads = leads.filter(created_at__date__lte=end_date)

        leads = leads.order_by('-created_at')

        serializer = LeadSerializerListDisplay(leads, many=True)

        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(CustomUser=request.user,lead_type="assigned_lead" )
            return Response({
                "status": "1",
                "message": "Lead created successfully"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "0",
            "message": "Lead creation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class AdminLeadDetailView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'leads_management'

    def get_object(self, pk):
        try:
            return Lead.objects.get(pk=pk)
        except Lead.DoesNotExist:
            return None

    def get(self, request, pk):
        lead = self.get_object(pk)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)
        serializer = LeadSerializerDetailDisplay(lead)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    def patch(self, request, pk):
        lead = self.get_object(pk)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Lead updated successfully"})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=400)

    def delete(self, request, pk):
        lead = self.get_object(pk)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)
        lead.delete()
        return Response({"status": "1", "message": "Lead deleted"}, status=200)
