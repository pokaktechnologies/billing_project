from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics

from django.utils.timezone import make_aware
from django.utils.dateparse import parse_date
from datetime import datetime, date,time
from django.utils.timezone import make_aware
from django.db.models import Q

from accounts.permissions import HasModulePermission
from attendance.models import DailyAttendance
from attendance.serializers import DailyAttendanceSessionDetailSerializer

from ..models import *
from ..serializers.LeadsSerializers import *
from ..utils import log_activity


#------------
#  pagination class
#--------------
from rest_framework.pagination import PageNumberPagination
class Pagination(PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_page_size(self, request):
        page_size = request.query_params.get('page_size')
        if page_size is None:
            return None
        return int(page_size)

class SalesPersonBaseView(APIView):
    def get_salesperson(self, user):
        try:
            staff = StaffProfile.objects.get(user=user)
            return SalesPerson.objects.get(assigned_staff=staff)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist):
            return None

class StaffLeadView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        user = request.user
        try:
            staff_profile = StaffProfile.objects.get(user=user)
            salesperson = SalesPerson.objects.get(assigned_staff=staff_profile)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist):
            return Response(
                {"status": "0", "message": "No salesperson assigned to this staff"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Base queryset
        leads = Lead.objects.filter(salesperson=salesperson)

        # --- Filters ---
        lead_source = request.query_params.get('lead_source')
        location = request.query_params.get('location')
        lead_type = request.query_params.get('lead_type')  # my_lead / assigned_lead
        start_date = request.query_params.get('start_date')  # yyyy-mm-dd
        end_date = request.query_params.get('end_date')      # yyyy-mm-dd
        name = request.query_params.get('name')
        lead_status = request.query_params.get('lead_status')

        if name:
            leads = leads.filter(name__icontains=name)

        if lead_status:
            leads = leads.filter(lead_status=lead_status)
            
        if lead_source:
            leads = leads.filter(lead_source=lead_source)

        if location:
            leads = leads.filter(location=location)

        if lead_type:
            leads = leads.filter(lead_type=lead_type)



        if start_date:
            try:
                start_datetime = make_aware(datetime.combine(
                    datetime.strptime(start_date, "%Y-%m-%d").date(),
                    time.min
                ))
                leads = leads.filter(created_at__gte=start_datetime)
            except ValueError:
                return Response({"status": "0", "message": "Invalid start_date format"}, status=400)

        if end_date:
            try:
                end_datetime = make_aware(datetime.combine(
                    datetime.strptime(end_date, "%Y-%m-%d").date(),
                    time.max
                ))
                leads = leads.filter(created_at__lte=end_datetime)
            except ValueError:
                return Response({"status": "0", "message": "Invalid end_date format"}, status=400)

            
        leads = leads.order_by('-created_at')

        # Pagination 
        paginator = Pagination()
        paginated_leads = paginator.paginate_queryset(leads, request)

        if paginated_leads is not None:
            serializer = LeadSerializerListDisplay(paginated_leads, many=True)
            
            return paginator.get_paginated_response({
                "status": "1",
                "message": "success",
                "data": serializer.data
            })
        
        serializer = LeadSerializerListDisplay(leads, many=True)

        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        })


    def post(self, request):
        user = request.user
        
        # Lookup staff -> salesperson mapping
        try:
            staff_profile = StaffProfile.objects.get(user=user)
            salesperson = SalesPerson.objects.get(assigned_staff=staff_profile)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist):
            return Response(
                {"status": "0", "message": "No salesperson assigned to this staff"},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            lead = serializer.save(CustomUser=user, salesperson=salesperson , lead_type="my_lead")
            log_activity(
                lead,
                "created",
                f"Lead created: {lead.name}",
                model="Lead",
                obj_id=lead.id
            )
            return Response({"status": "1", "message": "Lead created successfully"}, status=201)

        return Response(
            {"status": "0", "message": "Lead creation failed", "errors": serializer.errors},
            status=400
        )




class StaffLeadDetailView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    # -----------------------
    # OBJECT FETCHER
    # -----------------------
    def get_object(self, pk, salesperson):
        try:
            return Lead.objects.get(pk=pk, salesperson=salesperson)
        except Lead.DoesNotExist:
            return None

    # -----------------------
    # GET ONE LEAD
    # -----------------------
    def get(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        lead = self.get_object(pk, salesperson)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        serializer = LeadSerializerDetailDisplay(lead)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    # -----------------------
    # UPDATE LEAD
    # -----------------------
    def patch(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        lead = self.get_object(pk, salesperson)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        old_status = lead.lead_status
        old_status_display = lead.get_lead_status_display()
        serializer = LeadSerializer(lead, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            # Optional logging
            if 'lead_status' in request.data and old_status != lead.lead_status:
                lead_status_display = lead.get_lead_status_display()
                log_activity(
                    lead,
                    "status_change",
                    f"Lead status changed from '{old_status_display}' to '{lead_status_display}'",
                    model="Lead",
                    obj_id=lead.id
                )

            return Response({"status": "1", "message": "Lead updated"})
        
        return Response(
            {"status": "0", "message": "Update failed", "errors": serializer.errors},
            status=400
        )

    # -----------------------
    # DELETE LEAD
    # -----------------------
    def delete(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        lead = self.get_object(pk, salesperson)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        lead.delete()
        return Response({"status": "1", "message": "Lead deleted"})




# -----------------------
# FOLLOW-UPS
# -----------------------

class StaffFollowUpView(SalesPersonBaseView,APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    # -----------------------
    # LIST FOLLOW-UPS
    # -----------------------
    def get(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response(
                {"status": "0", "message": "No salesperson assigned"},
                status=400
            )

        followups = FollowUp.objects.filter(
            lead__salesperson=salesperson
        )

        title = request.query_params.get("title")
        followup_type = request.query_params.get("type")
        status_param = request.query_params.get("status")
        filter_by = request.query_params.get("filter_by")  # today, upcoming, overdue, completed

        # TEXT FILTER
        if title:
            followups = followups.filter(title__icontains=title)

        # TYPE FILTER
        if followup_type:
            followups = followups.filter(types__contains=[followup_type])

        # DATE-BASED FILTER
        today = date.today()

        if filter_by:
            if filter_by == "today":
                followups = followups.filter(date=today)

            elif filter_by == "upcoming":
                followups = followups.filter(date__gt=today)

            elif filter_by == "overdue":
                followups = followups.filter(status="new", date__lt=today)

            elif filter_by == "completed":
                followups = followups.filter(status="completed")

            else:
                return Response({
                    "status": "0",
                    "message": "Invalid filter_by value"
                }, status=400)

        # STATUS FILTER (only if filter_by NOT used)
        else:
            if status_param:
                followups = followups.filter(status=status_param)

        followups = followups.order_by('-created_at')

        # PAGINATION
        paginator = Pagination()
        paginated_followups = paginator.paginate_queryset(followups, request)

        if paginated_followups is not None:
            serializer = FollowUpSerializer(paginated_followups, many=True)

            return paginator.get_paginated_response({
                "status": "1",
                "message": "success",
                "data": serializer.data
            })
        
        serializer = FollowUpSerializer(followups, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        })


    # -----------------------
    # CREATE FOLLOW-UP
    # -----------------------
    def post(self, request):
        user = request.user
        salesperson = self.get_salesperson(user)

        if not salesperson:
            return Response(
                {"status": "0", "message": "No salesperson assigned"},
                status=400
            )

        lead_id = request.data.get("lead")
        if not lead_id:
            return Response(
                {"status": "0", "message": "Lead ID is required"},
                status=400
            )

        # ensure lead belongs to this salesperson
        try:
            lead = Lead.objects.get(id=lead_id, salesperson=salesperson)
        except Lead.DoesNotExist:
            return Response(
                {"status": "0", "message": "Lead not found or unauthorized"},
                status=404
            )

        serializer = FollowUpSerializer(data=request.data)
        if serializer.is_valid():
            followup = serializer.save()
            log_activity(
                lead,
                "created",
                f"Follow-up created: {followup.title}",
                model="FollowUp",
                obj_id=followup.id
            )
            return Response(
                {"status": "1", "message": "Follow-up created successfully"},
                status=201
            )

        return Response(
            {"status": "0", "message": "Creation failed", "errors": serializer.errors},
            status=400
        )



class StaffFollowUpDetailView(SalesPersonBaseView,APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'



    def get_object(self, pk, salesperson):
        try:
            return FollowUp.objects.get(pk=pk, lead__salesperson=salesperson)
        except FollowUp.DoesNotExist:
            return None

    # -----------------------
    # GET ONE FOLLOW-UP
    # -----------------------
    def get(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        followup = self.get_object(pk, salesperson)
        if not followup:
            return Response({"status": "0", "message": "Follow-up not found"}, status=404)

        serializer = FollowUpSerializer(followup)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    def patch(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        followup = self.get_object(pk, salesperson)
        if not followup:
            return Response({"status": "0", "message": "Follow-up not found"}, status=404)

        old_status = followup.status
        old_label = followup.get_status_display()

        serializer = FollowUpSerializer(followup, data=request.data, partial=True)
        if serializer.is_valid():
            followup = serializer.save()

            if "status" in request.data and old_status != followup.status:
                new_label = followup.get_status_display()

                log_activity(
                    followup.lead, "status_change",
                    f"Follow-up status changed {old_label} → {new_label}",
                    model="FollowUp", obj_id=followup.id
                )

            return Response({"status": "1", "message": "Follow-up updated"})

        return Response({"status": "0", "message": "Update error", "errors": serializer.errors}, status=400)

    def delete(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        followup = self.get_object(pk, salesperson)
        if not followup:
            return Response({"status": "0", "message": "Follow-up not found"}, status=404)

        log_activity(
            followup.lead, "deleted",
            f"Follow-up deleted: {followup.title}",
            model="FollowUp", obj_id=followup.id
        )

        followup.delete()
        return Response({"status": "1", "message": "Follow-up deleted"})

# list all followups for a lead
class LeadFollowUpView(SalesPersonBaseView,APIView):
    def get(self, request, lead_id):
        followups = FollowUp.objects.filter(lead__id=lead_id, lead__salesperson=self.get_salesperson(request.user)).order_by('-created_at')
        serializer = FollowUpSerializer(followups, many=True)
        return Response(serializer.data)
    

class LeadsWithoutQuotationView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'
    def get(self, request):
        # Filter leads without quotation and select only required fields
        leads = Lead.objects.filter(quotation__isnull=True) \
            .values('id', 'lead_number', 'name','company')

        return Response(leads, status=status.HTTP_200_OK)

class LeadSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        name = request.query_params.get('name', '').strip()
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')
        status_filter = request.query_params.get('status', '').strip()
        sales_person = request.query_params.get('salesperson', '').strip()

        if (from_date_str and not to_date_str) or (to_date_str and not from_date_str):
            return Response(
                {"status": "0", "message": "Both 'from_date' and 'to_date' must be provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        leads = Lead.objects.all().order_by('-created_at')

        if from_date_str and to_date_str:
            try:
                from_parsed = parse_date(from_date_str)
                to_parsed = parse_date(to_date_str)

                if not from_parsed or not to_parsed:
                    raise ValueError

                if from_parsed > to_parsed:
                    return Response(
                        {"status": "0", "message": "'from_date' cannot be greater than 'to_date'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                from_date = make_aware(datetime.combine(from_parsed, datetime.min.time()))
                to_date = make_aware(datetime.combine(to_parsed, datetime.max.time()))
                leads = leads.filter(created_at__range=(from_date, to_date))

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format. Use 'YYYY-MM-DD'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if name:
            search_terms = name.strip().split()
            query = Q()
            for term in search_terms:
                query |= Q(name__icontains=term)
            leads = leads.filter(query)

        if status_filter:
            leads = leads.filter(lead_status=status_filter)
        
        if sales_person:
            leads = leads.filter(salesperson=sales_person)

        serializer = LeadSerializerListDisplay(leads, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class StaffFollowUpSummaryView(SalesPersonBaseView,APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)

        today = date.today()

        qs = FollowUp.objects.filter(lead__salesperson=salesperson)

        # Counts
        total = qs.count()
        today_count = qs.filter(date=today).count()
        upcoming = qs.filter(date__gt=today).count()
        completed = qs.filter(status="completed").count()
        overdue = qs.filter(status="new", date__lt=today).count()

        return Response({
            "status": "1",
            "message": "success",
            "data": {
                "total": total,
                "today": today_count,
                "upcoming": upcoming,
                "completed": completed,
                "overdue": overdue
            }
        })


# -----------------------
# MEETINGS VIEWS
# -----------------------

class MeetingsView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    # LIST MEETINGS
    def get(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)

        # Base queryset FIRST
        meetings = Meeting.objects.filter(
            lead__salesperson=salesperson
        ).order_by('-created_at')

        title = request.query_params.get("title")
        status = request.query_params.get("status")
        meeting_type = request.query_params.get("meeting_type")
        filter_by = request.query_params.get("filter_by")  # today, upcoming, overdue

        # Filters
        if title:
            meetings = meetings.filter(title__icontains=title)

        if status:
            meetings = meetings.filter(status=status)

        if meeting_type:
            meetings = meetings.filter(meeting_type=meeting_type)

        # Date-based filters
        if filter_by:
            today = date.today()

            if filter_by == "today":
                meetings = meetings.filter(date=today)
            elif filter_by == "upcoming":
                meetings = meetings.filter(date__gt=today)
            elif filter_by == "overdue":
                meetings = meetings.filter(date__lt=today)

        paginator = Pagination()
        paginated_meetings = paginator.paginate_queryset(meetings, request)
        if paginated_meetings is not None:

            serializer = MeetingSerializerDisplay(paginated_meetings, many=True)
            return paginator.get_paginated_response({"status": "1", "message": "success", "data": serializer.data})

        serializer = MeetingSerializerDisplay(meetings, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    # CREATE MEETING
    def post(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)

        lead_id = request.data.get("lead")
        if not lead_id:
            return Response({"status": "0", "message": "Lead ID is required"}, status=400)

        # validate lead ownership
        try:
            lead = Lead.objects.get(id=lead_id, salesperson=salesperson)
        except Lead.DoesNotExist:
            return Response({"status": "0", "message": "Lead not found or unauthorized"}, status=404)

        serializer = MeetingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            meeting = serializer.save()

            log_activity(
                lead, "created",
                f"Meeting created: {meeting.title}",
                model="Meeting", obj_id=meeting.id
            )
            return Response({"status": "1", "message": "Meeting created successfully"}, status=201)

        return Response({
            "status": "0",
            "message": "Meeting creation failed",
            "errors": serializer.errors
        }, status=400)


class MeetingDetailView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get_object(self, pk, user):
        salesperson = self.get_salesperson(user)
        if not salesperson:
            return None

        try:
            return Meeting.objects.get(pk=pk, lead__salesperson=salesperson)
        except Meeting.DoesNotExist:
            return None

    # GET SINGLE MEETING
    def get(self, request, pk):
        meeting = self.get_object(pk, request.user)
        if not meeting:
            return Response({"status": "0", "message": "Meeting not found"}, status=404)

        serializer = MeetingSerializerDisplay(meeting)
        return Response({"status": "1", "message": "success", "data": [serializer.data]})

    # UPDATE MEETING
    def patch(self, request, pk):
        meeting = self.get_object(pk, request.user)
        if not meeting:
            return Response({"status": "0", "message": "Meeting not found"}, status=404)
        old_status = meeting.status
        old_label = meeting.get_status_display()
        serializer = MeetingSerializer(meeting, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            meeting = serializer.save()

            if "status" in request.data and old_status != meeting.status:
                new_label = meeting.get_status_display()

                log_activity(
                    meeting.lead, "status_change",
                    f"Meeting status changed {old_label} → {new_label}",
                    model="Meeting", obj_id=meeting.id
                )
            return Response({"status": "1", "message": "Meeting updated successfully"})

        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=400)

    # DELETE MEETING
    def delete(self, request, pk):
        meeting = self.get_object(pk, request.user)
        if not meeting:
            return Response({"status": "0", "message": "Meeting not found"}, status=404)
        log_activity(
            meeting.lead, "deleted",
            f"Meeting deleted: {meeting.title}",
            model="Meeting", obj_id=meeting.id
        )
        meeting.delete()
        return Response({"status": "1", "message": "Meeting deleted successfully"}, status=200)

class MeetingSummaryView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)
        
        today = date.today()

        qs = Meeting.objects.filter(lead__salesperson=salesperson)
        # Counts
        total = qs.count()
        today_count = qs.filter(date=today).count()
        upcoming = qs.filter(date__gt=today).count()
        completed = qs.filter(status="completed").count()
        overdue = qs.filter(status="scheduled", date__lt=today).count()

        return Response({
            "status": "1",
            "message": "success",
            "data": {
                "total": total,
                "today": today_count,
                "upcoming": upcoming,
                "completed": completed,
                "overdue": overdue
            }
        })
    

class LeadMeetingView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request, lead_id):
        meetings = Meeting.objects.filter(lead__id=lead_id, lead__salesperson=self.get_salesperson(request.user)).order_by('-created_at')
        serializer = MeetingSerializerDisplay(meetings, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



#display all Todays meetings 
class MeetingRemiderView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        today = date.today()
        meetings = Meeting.objects.filter(date__date=today, lead__CustomUser=request.user).order_by('date')
        # meetings = Meeting.objects.filter(date__date=today, lead__CustomUser=request.user).order_by('-created_at')
        serializer = MeetingSerializerDisplay(meetings, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class ManualActivityLogView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated]

    # CREATE MANUAL LOG
    def post(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        lead_id = request.data.get("lead")
        if not lead_id:
            return Response({"status": "0", "message": "Lead ID required"}, status=400)

        try:
            lead = Lead.objects.get(id=lead_id, salesperson=salesperson)
        except Lead.DoesNotExist:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        serializer = ActivityLogManualSerializer(data=request.data)
        if serializer.is_valid():
            log = serializer.save(related_model="Lead", related_id=lead.id)
            return Response({"status": "1", "message": "Activity added", "data": serializer.data}, status=201)

        return Response({"status": "0", "message": "Error", "errors": serializer.errors}, status=400)


class ManualActivityLogDetailView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, salesperson):
        try:
            return ActivityLog.objects.get(
                id=pk,
                lead__salesperson=salesperson,
                activity_type__in=["call", "email", "whatsapp", "quotation"]
            )
        except ActivityLog.DoesNotExist:
            return None

    # UPDATE LOG
    def patch(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        log = self.get_object(pk, salesperson)

        if not log:
            return Response({"status": "0", "message": "Activity not found"}, status=404)

        serializer = ActivityLogManualSerializer(log, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Activity updated"})

        return Response({"status": "0", "errors": serializer.errors}, status=400)


    # DELETE LOG
    def delete(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        log = self.get_object(pk, salesperson)

        if not log:
            return Response({"status": "0", "message": "Activity not found"}, status=404)

        log.delete()
        return Response({"status": "1", "message": "Activity deleted"})


class RemindersView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response(
                {"status": "0", "message": "No salesperson assigned"},
                status=400
            )

        reminders = Reminders.objects.filter(lead__salesperson=salesperson)

        title = request.query_params.get('title')
        reminder_type = request.query_params.get('type')
        status_param = request.query_params.get('status')
        filter_by = request.query_params.get('filter_by')

        if title:
            reminders = reminders.filter(title__icontains=title)

        if reminder_type:
            reminders = reminders.filter(type=reminder_type)

        today = date.today()

        # filter_by has priority
        if filter_by:
            if filter_by == 'today':
                reminders = reminders.filter(date=today)

            elif filter_by == 'upcoming':
                reminders = reminders.filter(date__gt=today)

            elif filter_by == 'overdue':
                reminders = reminders.filter(
                    status='scheduled',
                    date__lt=today
                )

            elif filter_by == 'completed':
                reminders = reminders.filter(status='completed')

            else:
                return Response(
                    {"status": "0", "message": "Invalid filter_by value"},
                    status=400
                )
        else:
            if status_param:
                reminders = reminders.filter(status=status_param)

        reminders = reminders.order_by('-date')

        paginator = Pagination()
        paginated_reminders = paginator.paginate_queryset(reminders, request)

        if paginated_reminders is not None:

            serializer = RemindersGetSerializer(paginated_reminders, many=True)
            return paginator.get_paginated_response({
                "status": "1",
                "message": "success",
                "data": serializer.data
            })
        
        serializer = RemindersGetSerializer(reminders, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data})


    def post(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)

        lead_id = request.data.get('lead')
        if not lead_id:
            return Response({"status": "0", "message": "Lead ID is required"}, status=400)

        try:
            lead = Lead.objects.get(id=lead_id)
            if lead.CustomUser != request.user and lead.salesperson != salesperson:
                return Response({"status": "0", "message": "You do not have permission to create a reminder for this lead"}, status=403)
        except Lead.DoesNotExist:
            return Response({"status": "0", "message": "Lead not found"}, status=404)

        serializer = RemindersSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Reminder created successfully", "data": serializer.data}, status=201)
        return Response({"status": "0", "message": "Reminder creation failed", "errors": serializer.errors}, status=400)


class RemindersDetailView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get_object(self, pk, salesperson):
        try:
            return Reminders.objects.get(pk=pk, lead__salesperson=salesperson)
        except Reminders.DoesNotExist:
            return None

    def get(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        reminder = self.get_object(pk, salesperson)
        if not reminder:
            return Response({"status": "0", "message": "Reminder not found"}, status=404)

        serializer = RemindersGetSerializer(reminder)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    def patch(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        reminder = self.get_object(pk, salesperson)
        if not reminder:
            return Response({"status": "0", "message": "Reminder not found"}, status=404)

        serializer = RemindersSerializer(reminder, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Reminder updated", "data": serializer.data})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=400)

    def delete(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        reminder = self.get_object(pk, salesperson)
        if not reminder:
            return Response({"status": "0", "message": "Reminder not found"}, status=404)

        reminder.delete()
        return Response({"status": "1", "message": "Reminder deleted"}, status=200)


# list all reminders for a lead
class LeadRemindersView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request, lead_id):
        reminders = Reminders.objects.filter(lead__id=lead_id, lead__salesperson=self.get_salesperson(request.user)).order_by('-date')
        serializer = RemindersSerializer(reminders, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data})


class RemindersSummaryView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)

        today = date.today()
        qs = Reminders.objects.filter(lead__salesperson=salesperson)

        total = qs.count()
        today_count = qs.filter(date=today).count()
        upcoming = qs.filter(date__gt=today).count()
        completed = qs.filter(status='completed').count()
        overdue = qs.filter(status='scheduled', date__lt=today).count()

        return Response({
            "status": "1",
            "message": "success",
            "data": {
                "total": total,
                "today": today_count,
                "upcoming": upcoming,
                "completed": completed,
                "overdue": overdue
            }
        })


#Dashboard BDE ---------

from datetime import date, timedelta, datetime
from django.db.models import Count
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class BDEDashboardView(SalesPersonBaseView, APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    # required_module = 'marketing'

    def get(self, request):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)

        today = date.today()
        start_of_month = today.replace(day=1)
        start_of_week = today - timedelta(days=today.weekday())
        tomorrow = today + timedelta(days=1)

        # ================= LEADS =================
        all_leads = Lead.objects.filter(salesperson=salesperson)

        total_leads = all_leads.count()

        # Leads by status (SINGLE QUERY)
        lead_status_summary = {
            'new': 0,
            'contacted': 0,
            'follow_up': 0,
            'in_progress': 0,
            'converted': 0,
            'lost': 0,
        }

        status_counts = all_leads.values('lead_status').annotate(count=Count('id'))
        for item in status_counts:
            lead_status_summary[item['lead_status']] = item['count']

        # Leads by source (SINGLE QUERY)
        leads_by_source_qs = all_leads.values(
            'lead_source__name'
        ).annotate(count=Count('id'))

        leads_by_source_data = {
            item['lead_source__name'] or 'Unknown': item['count']
            for item in leads_by_source_qs
        }

        leads_this_month = all_leads.filter(created_at__gte=start_of_month).count()
        leads_this_week = all_leads.filter(created_at__gte=start_of_week).count()

        # ================= MEETINGS =================
        meetings_base = Meeting.objects.filter(
            lead__salesperson=salesperson
        )

        meetings_today_qs = meetings_base.filter(
            date=today,
            status='scheduled'
        ).select_related('lead').order_by('time')

        meetings_data = [
            {
                "client": m.lead.company or m.lead.name,
                "time": m.time.strftime("%I:%M %p") if m.time else "N/A",
                "type": m.get_meeting_type_display(),
                "date": "Today"
            }
            for m in meetings_today_qs
        ]

        meeting_counts = meetings_base.values('status').annotate(count=Count('id'))
        meeting_summary_map = {m['status']: m['count'] for m in meeting_counts}

        total_meetings = sum(meeting_summary_map.values())
        completed_meetings = meeting_summary_map.get('completed', 0)
        upcoming_meetings = meetings_base.filter(
            date__gte=today,
            status='scheduled'
        ).count()

        meeting_summary = {
            'total': total_meetings,
            'completed': completed_meetings,
            'upcoming': upcoming_meetings,
            'today': meetings_today_qs.count(),
            'conversion_rate': f"{round((completed_meetings / total_meetings * 100), 1) if total_meetings else 0}%"
        }

        # ================= REMINDERS =================
        reminders_today = Reminders.objects.filter(
            lead__salesperson=salesperson,
            date=today,
            status='scheduled'
        ).order_by('time')

        reminders_data = []
        current_time = datetime.now().time()

        for r in reminders_today:
            if r.time and r.time > current_time:
                diff = (
                    datetime.combine(today, r.time)
                    - datetime.combine(today, current_time)
                )
                hours, remainder = divmod(diff.seconds, 3600)
                minutes = remainder // 60
                time_display = (
                    f"In {hours} hour{'s' if hours != 1 else ''}"
                    if hours > 0 else
                    f"In {minutes} minute{'s' if minutes != 1 else ''}"
                )
            else:
                time_display = "Overdue"

            reminders_data.append({
                "text": r.title,
                "time": time_display
            })

        tomorrow_reminders = Reminders.objects.filter(
            lead__salesperson=salesperson,
            date=tomorrow,
            status='scheduled'
        ).order_by('time')[:2]

        for r in tomorrow_reminders:
            reminders_data.append({
                "text": r.title,
                "time": "Tomorrow"
            })

        # ================= FOLLOW UPS =================
        all_followups = FollowUp.objects.filter(lead__salesperson=salesperson)

        followup_counts = all_followups.values('status').annotate(count=Count('id'))
        followup_status_map = {f['status']: f['count'] for f in followup_counts}

        followup_summary = {
            'total': all_followups.count(),
            'today': all_followups.filter(date=today).count(),
            'upcoming': all_followups.filter(date__gt=today).count(),
            'overdue': all_followups.filter(date__lt=today, status='new').count(),
            'completed': followup_status_map.get('completed', 0),
        }

        # ================= Attendance =================
        staff_profile = salesperson.assigned_staff
        today = timezone.localdate()

        today_attendance = DailyAttendance.objects.filter(
            staff=staff_profile,
            date=today
        ).first()

        attendance = (
            DailyAttendanceSessionDetailSerializer(today_attendance).data
            if today_attendance else None
        )
        # ================= ACTIVITY LOGS =================
        # recent_activities = ActivityLog.objects.filter(
        #     lead__salesperson=salesperson
        # ).select_related('lead').order_by('-timestamp')[:5]

        # activities_data = [
        #     {
        #         'lead_name': a.lead.name,
        #         'activity_type': a.get_activity_type_display(),
        #         'action': a.action,
        #         'timestamp': a.timestamp.strftime("%b %d, %I:%M %p")
        #     }
        #     for a in recent_activities
        # ]

        # ================= CONVERSION METRICS =================
        # converted = lead_status_summary['converted']
        # lost = lead_status_summary['lost']

        # metrics = {
        #     'conversion_rate': f"{round((converted / total_leads * 100), 1) if total_leads else 0}%",
        #     'loss_rate': f"{round((lost / total_leads * 100), 1) if total_leads else 0}%",
        #     'converted_leads': converted,
        #     'lost_leads': lost,
        #     'pending_leads': total_leads - converted - lost
        # }

        return Response({
            "status": "1",
            "message": "success",
            "data": {
                "lead_overview": {
                    "total_leads": total_leads,
                    "leads_this_month": leads_this_month,
                    "leads_this_week": leads_this_week,
                    "by_status": lead_status_summary,
                    "by_source": leads_by_source_data,
                },
                "meetings": {
                    "today_list": meetings_data,
                    "summary": meeting_summary,
                },
                "reminders": reminders_data,
                "follow_ups": followup_summary,
                # "recent_activities": activities_data,
                # "conversion_metrics": metrics,
                "attendance": attendance,
            }
        })



from rest_framework.permissions import IsAuthenticated

from rest_framework.permissions import IsAuthenticated

class LeadReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        leads = Lead.objects.select_related(
            "lead_source",
            "salesperson",
            "location"
        ).all()

        # -----------------------------
        # GET QUERY PARAMS
        # -----------------------------
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        lead_status = request.GET.get("lead_status")
        lead_source = request.GET.get("lead_source")
        salesperson = request.GET.get("salesperson")
        location = request.GET.get("location")
        lead_type = request.GET.get("lead_type")
        ordering = request.GET.get("ordering")
        client_name = request.GET.get("client_name")

        # -----------------------------
        # DATE FILTERING (SAFE WAY)
        # -----------------------------
        if from_date:
            parsed_from = parse_date(from_date)
            if parsed_from:
                start_datetime = make_aware(
                    datetime.combine(parsed_from, datetime.min.time())
                )
                leads = leads.filter(created_at__gte=start_datetime)

        if to_date:
            parsed_to = parse_date(to_date)
            if parsed_to:
                end_datetime = make_aware(
                    datetime.combine(parsed_to, datetime.max.time())
                )
                leads = leads.filter(created_at__lte=end_datetime)

        # -----------------------------
        # OTHER FILTERS
        # -----------------------------
        if client_name:
            leads = leads.filter(name__icontains=client_name)

        if lead_status:
            leads = leads.filter(lead_status=lead_status)

        if lead_source:
            leads = leads.filter(lead_source_id=lead_source)

        if salesperson:
            leads = leads.filter(salesperson_id=salesperson)

        if location:
            leads = leads.filter(location__name__icontains=location)

        if lead_type:
            leads = leads.filter(lead_type=lead_type)

        # -----------------------------
        # ORDERING
        # -----------------------------
        if ordering == "oldest":
            leads = leads.order_by("created_at")
        else:
            leads = leads.order_by("-created_at")

        serializer = LeadReportSerializer(leads, many=True)

        return Response({
            "count": leads.count(),
            "results": serializer.data
        })
    







from django.db.models import Count, Q, F, Value, Avg, ExpressionWrapper, DurationField

from django.db.models import Count, Q, F, Value
from django.db.models.functions import Concat

class LeadPerformanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        leads = Lead.objects.select_related(
            "salesperson",
            "lead_source",
            "location"
        ).all()

        # =========================
        # ROLE RESTRICTION
        # =========================
        if not request.user.is_staff:
            leads = leads.filter(CustomUser=request.user)

        # =========================
        # FILTERING
        # =========================

        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        search = request.GET.get("search")

        # ✅ SAFE DATE RANGE FILTER
        if from_date:
            parsed_from = parse_date(from_date)
            if parsed_from:
                start_datetime = make_aware(
                    datetime.combine(parsed_from, time.min)
                )
                leads = leads.filter(created_at__gte=start_datetime)

        if to_date:
            parsed_to = parse_date(to_date)
            if parsed_to:
                end_datetime = make_aware(
                    datetime.combine(parsed_to, time.max)
                )
                leads = leads.filter(created_at__lte=end_datetime)

        # Other filters
        if request.GET.get("lead_status"):
            leads = leads.filter(lead_status=request.GET.get("lead_status"))

        if request.GET.get("lead_source"):
            leads = leads.filter(lead_source_id=request.GET.get("lead_source"))

        if request.GET.get("salesperson"):
            leads = leads.filter(salesperson_id=request.GET.get("salesperson"))

        if request.GET.get("location"):
            leads = leads.filter(location_id=request.GET.get("location"))

        if request.GET.get("lead_type"):
            leads = leads.filter(lead_type=request.GET.get("lead_type"))

        # Global Search
        if search:
            leads = leads.filter(
                Q(name__icontains=search) |
                Q(company__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search) |
                Q(lead_number__icontains=search)
            )

        # =========================
        # KPI Aggregation
        # =========================

        kpi = leads.aggregate(
            total=Count("id"),
            converted=Count("id", filter=Q(lead_status="converted")),
            lost=Count("id", filter=Q(lead_status="lost")),
            new=Count("id", filter=Q(lead_status="new")),
            in_progress=Count("id", filter=Q(lead_status="in_progress")),
            contacted=Count("id", filter=Q(lead_status="contacted")),
            qualified=Count("id", filter=Q(lead_status="created")),
        )

        total_leads = kpi["total"] or 0
        converted = kpi["converted"] or 0

        conversion_rate = round(
            (converted / total_leads) * 100, 2
        ) if total_leads else 0

        # =========================
        # FOLLOW-UP STATS
        # =========================

        followups = FollowUp.objects.filter(lead__in=leads)

        followup_stats = followups.aggregate(
            pending=Count("id", filter=Q(status="new")),
            completed=Count("id", filter=Q(status="completed")),
        )

        # =========================
        # AVG RESPONSE TIME
        # =========================

        response_time = followups.annotate(
            response_duration=ExpressionWrapper(
                F("created_at") - F("lead__created_at"),
                output_field=DurationField()
            )
        ).aggregate(avg_time=Avg("response_duration"))

        avg_response = response_time["avg_time"]

        avg_hours = round(
            avg_response.total_seconds() / 3600, 2
        ) if avg_response else 0

        # =========================
        # SALESPERSON PERFORMANCE
        # =========================

        salesperson_data = leads.filter(
            salesperson__isnull=False
        ).annotate(
            full_name=Concat(
                F("salesperson__first_name"),
                Value(" "),
                F("salesperson__last_name")
            )
        ).values(
            "salesperson_id",
            "full_name"
        ).annotate(
            total=Count("id"),
            contacted=Count("id", filter=Q(lead_status="contacted")),
            qualified=Count("id", filter=Q(lead_status="created")),
            converted=Count("id", filter=Q(lead_status="converted")),
        ).order_by("-total")

        salesperson_list = list(salesperson_data)

        for sp in salesperson_list:
            sp["conversion_rate"] = round(
                (sp["converted"] / sp["total"]) * 100, 2
            ) if sp["total"] else 0

        # =========================
        # FINAL RESPONSE
        # =========================

        return Response({
            "total_leads": total_leads,
            "contacted": kpi["contacted"],
            "qualified": kpi["qualified"],
            "converted_leads": converted,
            "lost_leads": kpi["lost"],
            "new_leads": kpi["new"],
            "in_progress_leads": kpi["in_progress"],
            "conversion_rate": conversion_rate,
            "follow_up_pending": followup_stats["pending"],
            "follow_up_completed": followup_stats["completed"],
            "avg_response_time_hours": avg_hours,
            "salesperson_performance": salesperson_list
        })



class LeadSourceReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # -------------------------
        # BASE QUERYSET
        # -------------------------
        leads = Lead.objects.all()

        if not request.user.is_superuser:
            leads = leads.filter(CustomUser=request.user)

        # -------------------------
        # FILTERS
        # -------------------------
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        location = request.GET.get("location")
        salesperson = request.GET.get("salesperson")
        lead_status = request.GET.get("lead_status")
        lead_source = request.GET.get("lead_source")

        if from_date:
            parsed_from = parse_date(from_date)
            if parsed_from:
                start_datetime = make_aware(datetime.combine(parsed_from, datetime.min.time()))
                leads = leads.filter(created_at__gte=start_datetime)

        if to_date:
            parsed_to = parse_date(to_date)
            if parsed_to:
                end_datetime = make_aware(datetime.combine(parsed_to, datetime.max.time()))
                leads = leads.filter(created_at__lte=end_datetime)

        if location:
            leads = leads.filter(location_id=location)

        if salesperson:
            leads = leads.filter(salesperson_id=salesperson)

        if lead_status:
            leads = leads.filter(lead_status=lead_status)

        if lead_source:
            leads = leads.filter(lead_source_id=lead_source)

        # -------------------------
        # GROUP BY LEAD SOURCE
        # -------------------------
        source_data = (
            leads
            .filter(lead_source__isnull=False)
            .values(
                "lead_source_id",
                "lead_source__name"
            )
            .annotate(
                total_leads=Count("id"),
                converted=Count("id", filter=Q(lead_status="converted")),
                lost=Count("id", filter=Q(lead_status="lost")),
                new=Count("id", filter=Q(lead_status="new")),
                in_progress=Count("id", filter=Q(lead_status="in_progress")),
            )
            .order_by("-total_leads")
        )

        source_list = []

        for item in source_data:
            total = item["total_leads"]
            converted = item["converted"]

            conversion_rate = round((converted / total) * 100, 2) if total > 0 else 0

            source_list.append({
                "source_id": item["lead_source_id"],
                "source_name": item["lead_source__name"],
                "total_leads": total,
                "converted": converted,
                "lost": item["lost"],
                "new": item["new"],
                "in_progress": item["in_progress"],
                "conversion_rate": conversion_rate,
            })

        # -------------------------
        # OVERALL STATS (Optimized)
        # -------------------------
        overall_stats = leads.aggregate(
            total_leads=Count("id"),
            total_converted=Count("id", filter=Q(lead_status="converted")),
        )

        overall_total = overall_stats["total_leads"] or 0
        overall_converted = overall_stats["total_converted"] or 0

        overall_conversion_rate = (
            round((overall_converted / overall_total) * 100, 2)
            if overall_total > 0 else 0
        )

        # -------------------------
        # RESPONSE
        # -------------------------
        return Response({
            "overall": {
                "total_leads": overall_total,
                "converted": overall_converted,
                "conversion_rate": overall_conversion_rate,
            },
            "source_performance": source_list
        })
    


from hr_section.models import Enquiry
from django.db.models.functions import TruncMonth

class EnquiryReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        enquiries = Enquiry.objects.all()

        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        status = request.GET.get("status")
        search = request.GET.get("search")

        # ✅ SAFE DATETIME RANGE FILTER
        if from_date:
            parsed_from = parse_date(from_date)
            if parsed_from:
                start_datetime = make_aware(
                    datetime.combine(parsed_from, time.min)
                )
                enquiries = enquiries.filter(created_at__gte=start_datetime)

        if to_date:
            parsed_to = parse_date(to_date)
            if parsed_to:
                end_datetime = make_aware(
                    datetime.combine(parsed_to, time.max)
                )
                enquiries = enquiries.filter(created_at__lte=end_datetime)

        if status:
            enquiries = enquiries.filter(status=status)

        if search:
            enquiries = enquiries.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(message__icontains=search)
            )

        enquiries = enquiries.order_by("-created_at")

        enquiry_list = [
            {
                "enquiry_id": enquiry.id,
                "date": enquiry.created_at.date(),
                "client_name": f"{enquiry.first_name} {enquiry.last_name or ''}".strip(),
                "email": enquiry.email,
                "phone": enquiry.phone,
                "message": enquiry.message,
                "status": enquiry.status,
            }
            for enquiry in enquiries
        ]

        return Response({
            "total_records": enquiries.count(),
            "enquiries": enquiry_list
        })


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, F, Value
from django.db.models.functions import Concat
from django.utils.dateparse import parse_date

class FollowUpReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        followups = FollowUp.objects.select_related(
            "lead",
            "lead__salesperson"
        )

        # 🔒 Restrict non-admin users
        if not request.user.is_staff:
            followups = followups.filter(lead__CustomUser=request.user)

        # -------------------------
        # FILTER PARAMETERS
        # -------------------------
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        status = request.GET.get("status")
        salesperson = request.GET.get("salesperson")
        lead = request.GET.get("lead")
        search = request.GET.get("search")

        # -------------------------
        # DATE FILTER
        # -------------------------
        if from_date:
            followups = followups.filter(date__gte=parse_date(from_date))

        if to_date:
            followups = followups.filter(date__lte=parse_date(to_date))

        # -------------------------
        # FIELD FILTERS
        # -------------------------
        if status:
            followups = followups.filter(status=status)

        if salesperson:
            followups = followups.filter(lead__salesperson_id=salesperson)

        if lead:
            followups = followups.filter(lead_id=lead)

        # -------------------------
        # GLOBAL SEARCH
        # -------------------------
        if search:
            followups = followups.filter(
                Q(lead__name__icontains=search) |
                Q(lead__lead_number__icontains=search) |
                Q(notes__icontains=search) |
                Q(title__icontains=search)
            )

        # -------------------------
        # RESPONSE DATA FORMAT
        # -------------------------
        data = followups.annotate(
            lead_display=Concat(
                F("lead__lead_number"),
                Value(" - "),
                F("lead__name")
            ),
            salesperson_name=Concat(
                F("lead__salesperson__first_name"),
                Value(" "),
                F("lead__salesperson__last_name")
            )
        ).values(
            "id",
            "lead_display",
            "title",
            "date",
            "time",
            "status",
            "notes",
            "salesperson_name"
        ).order_by("-date", "-time")

        return Response({
            "total_followups": followups.count(),
            "completed": followups.filter(status="completed").count(),
            "pending": followups.filter(status="new").count(),
            "results": data
        })



class SalespersonLeadReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        leads = Lead.objects.select_related("salesperson")

        # -----------------------------------
        # RESTRICT NON-ADMIN USERS
        # -----------------------------------
        if not request.user.is_staff:
            leads = leads.filter(CustomUser=request.user)

        # -----------------------------------
        # FILTER PARAMETERS
        # -----------------------------------
        salesperson_id = request.GET.get("salesperson_id")
        salesperson_name = request.GET.get("salesperson_name")
        lead_status = request.GET.get("lead_status")
        lead_source = request.GET.get("lead_source")
        location = request.GET.get("location")
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        # -----------------------------------
        # APPLY FILTERS
        # -----------------------------------

        if salesperson_id:
            leads = leads.filter(salesperson_id=salesperson_id)

        if salesperson_name:
            leads = leads.filter(
                Q(salesperson__first_name__icontains=salesperson_name) |
                Q(salesperson__last_name__icontains=salesperson_name)
            )

        if lead_status:
            leads = leads.filter(lead_status=lead_status)

        if lead_source:
            leads = leads.filter(lead_source_id=lead_source)

        if location:
            leads = leads.filter(location_id=location)

        if from_date:
            leads = leads.filter(created_at__date__gte=parse_date(from_date))

        if to_date:
            leads = leads.filter(created_at__date__lte=parse_date(to_date))

        # -----------------------------------
        # GROUP BY SALESPERSON
        # -----------------------------------
        report = leads.filter(
            salesperson__isnull=False
        ).annotate(
            full_name=Concat(
                F("salesperson__first_name"),
                Value(" "),
                F("salesperson__last_name")
            )
        ).values(
            "salesperson_id",
            "full_name"
        ).annotate(
            total_leads=Count("id"),
            new=Count("id", filter=Q(lead_status="new")),
            contacted=Count("id", filter=Q(lead_status="contacted")),
            follow_up=Count("id", filter=Q(lead_status="follow_up")),
            in_progress=Count("id", filter=Q(lead_status="in_progress")),
            converted=Count("id", filter=Q(lead_status="converted")),
            lost=Count("id", filter=Q(lead_status="lost")),
        ).order_by("-total_leads")

        result = []

        for row in report:
            result.append({
                "salesperson_id": row["salesperson_id"],
                "salesperson": row["full_name"].strip(),
                "total_leads": row["total_leads"],
                "new": row["new"],
                "contacted": row["contacted"],
                "follow_up": row["follow_up"],
                "in_progress": row["in_progress"],
                "converted": row["converted"],
                "lost": row["lost"],
            })

        return Response(result)