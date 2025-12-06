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

from ..models import *
from ..serializers.LeadsSerializers import *
from ..utils import log_activity


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

        serializer = LeadSerializerListDisplay(leads, many=True)
        
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


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
            return Response({"status": "0", "message": "No salesperson assigned"}, status=400)

        reminders = Reminders.objects.filter(lead__salesperson=salesperson)

        # Filters
        title = request.query_params.get('title')
        reminder_type = request.query_params.get('type')
        status_param = request.query_params.get('status')
        filter_by = request.query_params.get('filter_by')  # today, upcoming, overdue, completed

        if title:
            reminders = reminders.filter(title__icontains=title)

        if reminder_type:
            reminders = reminders.filter(type=reminder_type)

        if status_param:
            reminders = reminders.filter(status=status_param)

        today = date.today()
        if filter_by:
            if filter_by == 'today':
                reminders = reminders.filter(date=today)
            elif filter_by == 'upcoming':
                reminders = reminders.filter(date__gt=today)
            elif filter_by == 'overdue':
                reminders = reminders.filter(status='scheduled', date__lt=today)
            elif filter_by == 'completed':
                reminders = reminders.filter(status='completed')
            else:
                return Response({"status": "0", "message": "Invalid filter_by value"}, status=400)

        reminders = reminders.order_by('-date')
        serializer = RemindersGetSerializer(reminders, many=True)
        return Response({"status": "1", "message": "success", "data": serializer.data}, status=200)

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
