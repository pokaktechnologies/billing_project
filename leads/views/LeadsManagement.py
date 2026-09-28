from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import HasModulePermission
from ..views.LeadsViews import SalesPersonBaseView
from ..serializers.LeadsSerializers import *
from accounts.models import SalesPerson, StaffProfile
from datetime import datetime, time
from ..utils import log_activity


class AdminLeadsView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request):

        # Base queryset
        # leads = Lead.objects.filter(lead_type="assigned_lead")
        leads = Lead.objects.all()
        print("Initial count:", leads.count())

        # --- Filters ---
        salesperson_filter = request.query_params.get("salesperson")  # "null", "not_null"
        lead_source = request.query_params.get("lead_source")         # numeric id
        start_date = request.query_params.get("start_date")           # YYYY-MM-DD
        end_date = request.query_params.get("end_date")               # YYYY-MM-DD
        name = request.query_params.get("name")                       # string search
        lead_status = request.query_params.get("status")
        lead_category = request.query_params.get('lead_category')
        lead_type = request.query_params.get('lead_type')  # my_lead / assigned_lead
        course = request.query_params.get("course") 


        # Filter by lead category
        if lead_category:
            leads = leads.filter(lead_category=lead_category)

        # Filter salesperson null or not null
        if salesperson_filter == "null":
            leads = leads.filter(salesperson__isnull=True)

        if salesperson_filter == "not_null":
            leads = leads.filter(salesperson__isnull=False)

        # Filter by lead status
        if lead_status:
            leads = leads.filter(lead_status__icontains=lead_status)


        # Filter by lead source
        if lead_source:
            leads = leads.filter(lead_source=lead_source)

        # Filter by name (case-insensitive)
        if name:
            leads = leads.filter(name__icontains=name.strip())

        # Filter by lead type
        if lead_type:
            leads = leads.filter(lead_type=lead_type)


        # Filter by date range
        if start_date:
            try:
                start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
                # Full datetime at start of the day
                start_dt = datetime.combine(start_date_parsed, time.min)
                leads = leads.filter(lead_date__gte=start_dt)
            except Exception as e:
                print("Start date parse error:", e)

        if end_date:
            try:
                end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
                # Full datetime at end of the day
                end_dt = datetime.combine(end_date_parsed, time.max)
                leads = leads.filter(lead_date__lte=end_dt)
            except Exception as e:
                print("End date parse error:", e)
        
        if course:
            leads = leads.filter(course_id=course)
            

        # Order
        leads = leads.order_by('-lead_date')

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
    permission_classes = [IsAuthenticated]


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
    permission_classes = [IsAuthenticated]


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
    permission_classes = [IsAuthenticated]


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
        # 1. Validate lead exists
        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response({
                "status": "0",
                "message": "Lead not found"
            }, status=status.HTTP_404_NOT_FOUND)

        # 2. Get all activities related to this lead
        leads = Lead.objects.filter(id=lead_id).order_by('-timestamp')

        # 3. Serialize
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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]


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


# list all salespersons with their assigned lead counts,converted lead counts,rate 
class SalespersonLeadStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        salespersons = SalesPerson.objects.all()
        data = []

        for sp in salespersons:
            assigned_leads_count = Lead.objects.filter(salesperson=sp, lead_type="assigned_lead").count()
            converted_leads_count = Lead.objects.filter(salesperson=sp, lead_type="assigned_lead", lead_status="converted").count()
            conversion_rate = (converted_leads_count / assigned_leads_count * 100) if assigned_leads_count > 0 else 0.0

            data.append({
                "salesperson_id": sp.id,
                "salesperson_email": sp.email,
                "salesperson_name": f"{sp.first_name} {sp.last_name}",
                "assigned_leads_count": assigned_leads_count,
                "converted_leads_count": converted_leads_count,
                "conversion_rate": round(conversion_rate, 2)
            })

        return Response({
            "status": "1",
            "message": "success",
            "data": data
        }, status=200)


def get_academic_dashboard_data(request, leads):
    """
    Common Academic Dashboard logic.

    `leads` is already restricted according to
    Admin or Staff before calling this function.
    """

    # ------------------------------------------------
    # FILTERS
    # ------------------------------------------------

    course = request.query_params.get("course")
    salesperson = request.query_params.get("salesperson")
    name = request.query_params.get("name")

    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if course:
        leads = leads.filter(
            course_id=course
        )

    if salesperson:
        leads = leads.filter(
            salesperson_id=salesperson
        )

    if name:
        leads = leads.filter(
            name__icontains=name.strip()
        )

    # ------------------------------------------------
    # START DATE
    # ------------------------------------------------

    if start_date:

        try:

            parsed_start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

            leads = leads.filter(
                lead_date__gte=parsed_start_date
            )

        except ValueError:

            return None, Response(
                {
                    "status": "0",
                    "message":
                        "Invalid start_date format. "
                        "Use YYYY-MM-DD."
                },
                status=400
            )

    # ------------------------------------------------
    # END DATE
    # ------------------------------------------------

    if end_date:

        try:

            parsed_end_date = datetime.strptime(
                end_date,
                "%Y-%m-%d"
            ).date()

            leads = leads.filter(
                lead_date__lte=parsed_end_date
            )

        except ValueError:

            return None, Response(
                {
                    "status": "0",
                    "message":
                        "Invalid end_date format. "
                        "Use YYYY-MM-DD."
                },
                status=400
            )

    # ------------------------------------------------
    # COUNTS
    # ------------------------------------------------

    counts = {

        "new": leads.filter(
            academic_status__isnull=True
        ).count(),

        "hot": leads.filter(
            academic_status="hot"
        ).count(),

        "not_respond": leads.filter(
            academic_status="not_respond"
        ).count(),

        "number_not_valid": leads.filter(
            academic_status="number_not_valid"
        ).count(),

        "not_connected": leads.filter(
            academic_status="not_connected"
        ).count(),

        "invalid": leads.filter(
            academic_status="invalid"
        ).count(),
    }

    # ------------------------------------------------
    # TAB
    # ------------------------------------------------

    tab = request.query_params.get(
        "tab",
        "new"
    )

    allowed_tabs = {
        "new": None,
        "hot": "hot",
        "not_respond": "not_respond",
        "number_not_valid": "number_not_valid",
        "not_connected": "not_connected",
        "invalid": "invalid",
    }

    if tab not in allowed_tabs:

        return None, Response(
            {
                "status": "0",
                "message": (
                    "Invalid tab. Allowed values: "
                    "new, hot, not_respond, "
                    "number_not_valid, "
                    "not_connected, invalid"
                )
            },
            status=400
        )

    selected_status = allowed_tabs[tab]

    # NEW means academic_status is NULL
    if selected_status is None:

        leads = leads.filter(
            academic_status__isnull=True
        )

    else:

        leads = leads.filter(
            academic_status=selected_status
        )

    # ------------------------------------------------
    # FOLLOW-UP DATA
    # ------------------------------------------------

    today = timezone.localdate()

    leads = leads.annotate(

        call_count=Count(
            "follow_ups",
            filter=Q(
                follow_ups__types__contains=["call"]
            ),
            distinct=True
        ),

        next_call_followup_date=Min(
            "follow_ups__date",
            filter=Q(
                follow_ups__types__contains=["call"],
                follow_ups__status="new",
                follow_ups__date__gte=today
            )
        )
    )

    # ------------------------------------------------
    # ORDER
    # ------------------------------------------------

    leads = leads.order_by(
        "next_call_followup_date",
        "-lead_date"
    )

    return {
        "leads": leads,
        "counts": counts,
        "tab": tab,
    }, None

from django.db.models import Count, Q, Min
class AdminAcademicDashboardView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        # --------------------------------------------
        # ALL ACADEMIC / INTERN LEADS
        # --------------------------------------------

        leads = Lead.objects.filter(
            lead_category="intern"
        ).select_related(
            "course",
            "salesperson"
        )

        result, error_response = get_academic_dashboard_data(
            request,
            leads
        )

        if error_response:
            return error_response

        leads = result["leads"]
        counts = result["counts"]
        tab = result["tab"]

        # --------------------------------------------
        # PAGINATION
        # --------------------------------------------

        # paginator = Pagination()

        # paginated_leads = paginator.paginate_queryset(
        #     leads,
        #     request
        # )

        # if paginated_leads is not None:

        #     serializer = AcademicLeadDashboardSerializer(
        #         paginated_leads,
        #         many=True
        #     )

        #     return paginator.get_paginated_response({
        #         "status": "1",
        #         "message": "success",
        #         "tab": tab,
        #         "counts": counts,
        #         "data": serializer.data
        #     })

        serializer = AcademicLeadDashboardSerializer(
            leads,
            many=True
        )

        return Response({
            "status": "1",
            "message": "success",
            "tab": tab,
            "counts": counts,
            "data": serializer.data
        })
    
class StaffAcademicDashboardView(SalesPersonBaseView, APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        # --------------------------------------------
        # GET SALESPERSON
        # --------------------------------------------

        salesperson = self.get_salesperson(
            request.user
        )

        if not salesperson:

            return Response(
                {
                    "status": "0",
                    "message":
                        "No salesperson assigned to this staff"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # --------------------------------------------
        # ONLY THIS SALESPERSON'S INTERN LEADS
        # --------------------------------------------

        leads = Lead.objects.filter(
            salesperson=salesperson,
            lead_category="intern"
        ).select_related(
            "course",
            "salesperson"
        )

        result, error_response = get_academic_dashboard_data(
            request,
            leads
        )

        if error_response:
            return error_response

        leads = result["leads"]
        counts = result["counts"]
        tab = result["tab"]

        # --------------------------------------------
        # PAGINATION
        # --------------------------------------------

        # paginator = Pagination()

        # paginated_leads = paginator.paginate_queryset(
        #     leads,
        #     request
        # )

        # if paginated_leads is not None:

        #     serializer = AcademicLeadDashboardSerializer(
        #         paginated_leads,
        #         many=True
        #     )

        #     return paginator.get_paginated_response({
        #         "status": "1",
        #         "message": "success",
        #         "tab": tab,
        #         "counts": counts,
        #         "data": serializer.data
        #     })

        serializer = AcademicLeadDashboardSerializer(
            leads,
            many=True
        )

        return Response({
            "status": "1",
            "message": "success",
            "tab": tab,
            "counts": counts,
            "data": serializer.data
        })