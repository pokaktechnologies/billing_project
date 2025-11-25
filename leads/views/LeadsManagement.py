from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasModulePermission
from ..serializers.LeadsSerializers import *
from accounts.models import SalesPerson, StaffProfile
from datetime import datetime, time
from ..utils import log_activity


class AdminLeadsView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'leads_management'

    def get(self, request):

        # Base queryset
        leads = Lead.objects.filter(lead_type="assigned_lead")
        print("Initial count:", leads.count())

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
            try:
                start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
                # Full datetime at start of the day
                start_dt = datetime.combine(start_date_parsed, time.min)
                leads = leads.filter(created_at__gte=start_dt)
            except Exception as e:
                print("Start date parse error:", e)

        if end_date:
            try:
                end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
                # Full datetime at end of the day
                end_dt = datetime.combine(end_date_parsed, time.max)
                leads = leads.filter(created_at__lte=end_dt)
            except Exception as e:
                print("End date parse error:", e)

        # Order
        leads = leads.order_by('-created_at')

        # Serialize
        serializer = LeadSerializerListDisplay(leads, many=True)

        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            lead = serializer.save(CustomUser=request.user,lead_type="assigned_lead" )
            log_activity(
                lead,
                "created",
                f"Lead created : {lead.name}",
                model="Lead",
                obj_id=lead.id
            )
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
        old_status = lead.lead_status
        old_label = lead.get_lead_status_display()
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # if admin changed status
            if "lead_status" in request.data and old_status != lead.lead_status:
                new_label = lead.get_lead_status_display()
                log_activity(
                    lead,
                    "status_change",
                    f"Lead status changed {old_label} → {new_label} by admin",
                    model="Lead",
                    obj_id=lead.id
                )

            return Response({"status": "1", "message": "Lead updated successfully"})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=400)

    def delete(self, request, pk):
        lead = self.get_object(pk)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)
        lead.delete()
        return Response({"status": "1", "message": "Lead deleted"}, status=200)



# multiple assign leads to a salesperson
class AssignLeadsToSalespersonView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'leads_management'

    def post(self, request):
        lead_ids = request.data.get("lead_ids", [])
        salesperson_id = request.data.get("salesperson_id")

        if not lead_ids or not salesperson_id:
            return Response({
                "status": "0",
                "message": "lead_ids and salesperson_id are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            salesperson = SalesPerson.objects.get(id=salesperson_id)
        except SalesPerson.DoesNotExist:
            return Response({
                "status": "0",
                "message": "SalesPerson not found"
            }, status=status.HTTP_404_NOT_FOUND)

        leads = Lead.objects.filter(id__in=lead_ids, lead_type="assigned_lead")
        updated_count = leads.update(salesperson=salesperson)

        return Response({
            "status": "1",
            "message": f"{updated_count} leads assigned to {salesperson.first_name} {salesperson.last_name}"
        }, status=status.HTTP_200_OK)


# multiple delete leads
class DeleteMultipleLeadsView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'leads_management'

    def post(self, request):
        lead_ids = request.data.get("lead_ids", [])

        if not lead_ids:
            return Response({
                "status": "0",
                "message": "lead_ids are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        leads = Lead.objects.filter(id__in=lead_ids, lead_type="assigned_lead")
        deleted_count, _ = leads.delete()

        return Response({
            "status": "1",
            "message": f"{deleted_count} leads deleted successfully"
        }, status=status.HTTP_200_OK)





class LeadProgressView(APIView):
    permission_classes = [IsAuthenticated]
    LEAD_PROGRESS_MAP = {
        "new": 0,
        "contacted": 20,
        "follow_up": 40,
        "created": 50,
        "in_progress": 70,
        "converted": 100,
        "lost": 0,
    }
    def get(self, request, lead_id):
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        progress = self.LEAD_PROGRESS_MAP.get(lead.lead_status, 0)

        return Response({
            "status": "1",
            "message": "success",
            "data": {
                "lead_id": lead.id,
                "lead_status": lead.lead_status,
                "progress": progress,
            }
        }, status=200)


class LeadActivityLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            try:
                start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
                # Full datetime at start of the day
                start_dt = datetime.combine(start_date_parsed, time.min)
                leads = leads.filter(created_at__gte=start_dt)
            except Exception as e:
                print("Start date parse error:", e)

        if end_date:
            try:
                end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
                # Full datetime at end of the day
                end_dt = datetime.combine(end_date_parsed, time.max)
                leads = leads.filter(created_at__lte=end_dt)
            except Exception as e:
                print("End date parse error:", e)

        # Order
        leads = leads.order_by('-created_at')

        # Serialize
        serializer = LeadSerializerListDisplay(leads, many=True)

        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            lead = serializer.save(CustomUser=request.user,lead_type="assigned_lead" )
            log_activity(
                lead,
                "created",
                f"Lead created : {lead.name}",
                model="Lead",
                obj_id=lead.id
            )
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
        old_status = lead.lead_status
        old_label = lead.get_lead_status_display()
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # if admin changed status
            if "lead_status" in request.data and old_status != lead.lead_status:
                new_label = lead.get_lead_status_display()
                log_activity(
                    lead,
                    "status_change",
                    f"Lead status changed {old_label} → {new_label} by admin",
                    model="Lead",
                    obj_id=lead.id
                )

            return Response({"status": "1", "message": "Lead updated successfully"})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=400)

    def delete(self, request, pk):
        lead = self.get_object(pk)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)
        lead.delete()
        return Response({"status": "1", "message": "Lead deleted"}, status=200)



# multiple assign leads to a salesperson
class AssignLeadsToSalespersonView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'leads_management'

    def post(self, request):
        lead_ids = request.data.get("lead_ids", [])
        salesperson_id = request.data.get("salesperson_id")

        if not lead_ids or not salesperson_id:
            return Response({
                "status": "0",
                "message": "lead_ids and salesperson_id are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            salesperson = SalesPerson.objects.get(id=salesperson_id)
        except SalesPerson.DoesNotExist:
            return Response({
                "status": "0",
                "message": "SalesPerson not found"
            }, status=status.HTTP_404_NOT_FOUND)

        leads = Lead.objects.filter(id__in=lead_ids, lead_type="assigned_lead")
        updated_count = leads.update(salesperson=salesperson)

        return Response({
            "status": "1",
            "message": f"{updated_count} leads assigned to {salesperson.first_name} {salesperson.last_name}"
        }, status=status.HTTP_200_OK)


# multiple delete leads
class DeleteMultipleLeadsView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'leads_management'

    def post(self, request):
        lead_ids = request.data.get("lead_ids", [])

        if not lead_ids:
            return Response({
                "status": "0",
                "message": "lead_ids are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        leads = Lead.objects.filter(id__in=lead_ids, lead_type="assigned_lead")
        deleted_count, _ = leads.delete()

        return Response({
            "status": "1",
            "message": f"{deleted_count} leads deleted successfully"
        }, status=status.HTTP_200_OK)





class LeadProgressView(APIView):
    permission_classes = [IsAuthenticated]
    LEAD_PROGRESS_MAP = {
        "new": 0,
        "contacted": 20,
        "follow_up": 40,
        "created": 50,
        "in_progress": 70,
        "converted": 100,
        "lost": 0,
    }
    def get(self, request, lead_id):
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        progress = self.LEAD_PROGRESS_MAP.get(lead.lead_status, 0)

        return Response({
            "status": "1",
            "message": "success",
            "data": {
                "lead_id": lead.id,
                "lead_status": lead.lead_status,
                "progress": progress,
            }
        }, status=200)


class LeadActivityLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        logs = ActivityLog.objects.filter(lead=lead).order_by("-timestamp")
        serializer = ActivityLogManualSerializer(logs, many=True)

        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=200)


class LeadActivityCountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lead_id):
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        manual_types = ['call', 'email', 'whatsapp', 'quotation']
        data = {}
        total = 0
        for activity_type in manual_types:
            count = ActivityLog.objects.filter(lead=lead, activity_type=activity_type).count()
            data[activity_type] = count
            total += count
        
        data['total'] = total

        return Response({
            "status": "1",
            "message": "success",
            "data": data
        }, status=200)