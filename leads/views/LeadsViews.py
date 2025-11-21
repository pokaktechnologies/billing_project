from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics

from django.utils.timezone import make_aware
from django.utils.dateparse import parse_date
from datetime import datetime, date
from django.db.models import Q

from accounts.permissions import HasModulePermission

from ..models import *
from ..serializers.LeadsSerializers import *


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
            serializer.save(CustomUser=user, salesperson=salesperson , lead_type="my_lead")
            return Response({"status": "1", "message": "Lead created successfully"}, status=201)

        return Response(
            {"status": "0", "message": "Lead creation failed", "errors": serializer.errors},
            status=400
        )




class StaffLeadDetailView(APIView):
    permission_classes = [IsAuthenticated,HasModulePermission]
    required_module = 'marketing'

    def get_object(self, pk, user):
        try:
            staff_profile = StaffProfile.objects.get(user=user)
            salesperson = SalesPerson.objects.get(assigned_staff=staff_profile)
            return Lead.objects.get(pk=pk, salesperson=salesperson)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist, Lead.DoesNotExist):
            return None

    def get(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found or unauthorized"}, status=404)
        serializer = LeadSerializerDetailDisplay(lead)
        return Response({"status": "1", "message": "success", "data": serializer.data})

    def patch(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found or unauthorized"}, status=404)
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Lead updated successfully"})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=400)

    def delete(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found or unauthorized"}, status=404)
        lead.delete()
        return Response({"status": "1", "message": "Lead deleted successfully"}, status=200)



# -----------------------
# FOLLOW-UPS
# -----------------------

class StaffFollowUpView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get_salesperson(self, user):
        """Return salesperson or None"""
        try:
            staff = StaffProfile.objects.get(user=user)
            return SalesPerson.objects.get(assigned_staff=staff)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist):
            return None

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

        if title:
            followups = followups.filter(title__icontains=title)

        if followup_type:
            followups = followups.filter(types__contains=[followup_type])

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
            serializer.save()
            return Response(
                {"status": "1", "message": "Follow-up created successfully"},
                status=201
            )

        return Response(
            {"status": "0", "message": "Creation failed", "errors": serializer.errors},
            status=400
        )



class StaffFollowUpDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get_salesperson(self, user):
        try:
            staff = StaffProfile.objects.get(user=user)
            return SalesPerson.objects.get(assigned_staff=staff)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist):
            return None

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

    # -----------------------
    # UPDATE FOLLOW-UP
    # -----------------------
    def patch(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        followup = self.get_object(pk, salesperson)
        if not followup:
            return Response({"status": "0", "message": "Follow-up not found"}, status=404)

        serializer = FollowUpSerializer(followup, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Follow-up updated"})

        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=400)

    # -----------------------
    # DELETE FOLLOW-UP
    # -----------------------
    def delete(self, request, pk):
        salesperson = self.get_salesperson(request.user)
        if not salesperson:
            return Response({"status": "0", "message": "Unauthorized"}, status=400)

        followup = self.get_object(pk, salesperson)
        if not followup:
            return Response({"status": "0", "message": "Follow-up not found"}, status=404)

        followup.delete()
        return Response({"status": "1", "message": "Follow-up deleted"})

# list all followups for a lead
class LeadFollowUpView(APIView):
    def get_salesperson(self, user):
        try:
            staff = StaffProfile.objects.get(user=user)
            return SalesPerson.objects.get(assigned_staff=staff)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist):
            return None
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


class StaffFollowUpSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get_salesperson(self, user):
        try:
            staff = StaffProfile.objects.get(user=user)
            return SalesPerson.objects.get(assigned_staff=staff)
        except (StaffProfile.DoesNotExist, SalesPerson.DoesNotExist):
            return None

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

class MeetingsView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'


    def get(self, request):
        meetings = Meeting.objects.all().order_by('-created_at')
        serializer = MeetingSerializerDisplay(meetings, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MeetingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "1",
                "message": "Meeting created successfully"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "0",
            "message": "Meeting creation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class MeetingDetailView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get_object(self, pk, user):
        try:
            return Meeting.objects.get(pk=pk, lead__CustomUser=user)
        except Meeting.DoesNotExist:
            return None
        
    def get(self, request, pk):
        meeting = self.get_object(pk, request.user)
        if not meeting:
            return Response({"status": "0", "message": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = MeetingSerializerDisplay(meeting)
        return Response({"status": "1", "message": "success", "data": [serializer.data]})
    
    def patch(self, request, pk):
        meeting = self.get_object(pk, request.user)
        if not meeting:
            return Response({"status": "0", "message": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = MeetingSerializer(meeting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Meeting updated successfully"})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        meeting = self.get_object(pk, request.user)
        if not meeting:
            return Response({"status": "0", "message": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            meeting.delete()
        except Exception as e:
            return Response({"status": "0", "message": "Meeting deletion failed", "errors": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # If deletion is successful, return a success message
        return Response({"status": "1", "message": "Meeting deleted successfully"}, status=status.HTTP_200_OK)


class MeetingSearchView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = 'marketing'

    def get(self, request):
        lead_name = request.query_params.get('lead_name', '').strip()
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')
        status_filter = request.query_params.get('status', '').strip()


        # Validate missing dates
        if (from_date_str and not to_date_str) or (to_date_str and not from_date_str):
            return Response(
                {"status": "0", "message": "Both 'from_date' and 'to_date' must be provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not lead_name and not (from_date_str and to_date_str) and not status_filter:
            return Response(
                {"status": "0", "message": "Provide at least 'lead_name' or both 'from_date' and 'to_date or 'status'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        


        meetings = Meeting.objects.filter(lead__CustomUser=request.user).order_by('-created_at')

        if from_date_str and to_date_str:
            try:
                from_parsed = parse_date(from_date_str)
                to_parsed = parse_date(to_date_str)

                if not from_parsed or not to_parsed:
                    raise ValueError

                # Check if from_date is greater than to_date
                if from_parsed > to_parsed:
                    return Response(
                        {"status": "0", "message": "'from_date' cannot be greater than 'to_date'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Convert to aware datetime
                if from_parsed == to_parsed:
                    # Same day filter
                    day_start = make_aware(datetime.combine(from_parsed, datetime.min.time()))
                    day_end = make_aware(datetime.combine(from_parsed, datetime.max.time()))
                    meetings = meetings.filter(date__range=(day_start, day_end))
                else:
                    from_date = make_aware(datetime.combine(from_parsed, datetime.min.time()))
                    to_date = make_aware(datetime.combine(to_parsed, datetime.max.time()))
                    meetings = meetings.filter(date__range=(from_date, to_date))

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format. Use 'YYYY-MM-DD'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if lead_name:
            search_terms = lead_name.split()
            query = Q()
            for term in search_terms:
                query &= Q(lead__name__icontains=term)
            meetings = meetings.filter(query)
        
        if status_filter:
            if status_filter not in ['scheduled', 'completed', 'canceled']:
                return Response(
                    {"status": "0", "message": "Invalid status value. Choose from 'scheduled', 'completed', or 'canceled'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            meetings = meetings.filter(status=status_filter)


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


