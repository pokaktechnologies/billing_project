from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.utils.timezone import make_aware
from django.utils.dateparse import parse_date
from datetime import datetime
from django.db.models import Q

from .models import *
from .serializers import *



class LeadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leads = Lead.objects.filter(CustomUser=request.user).order_by('-created_at')
        serializer = LeadSerializer(leads, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(CustomUser=request.user)
            return Response({
                "status": "1",
                "message": "Lead created successfully"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "0",
            "message": "Lead creation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LeadDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Lead.objects.get(pk=pk, CustomUser=user)
        except Lead.DoesNotExist:
            return None

    def get(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeadSerializer(lead)
        return Response({"status": "1", "message": "success", "data": [serializer.data]})

    def patch(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "1", "message": "Lead updated successfully"})
        return Response({"status": "0", "message": "Update failed", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        lead = self.get_object(pk, request.user)
        if not lead:
            return Response({"status": "0", "message": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            lead.delete()
        except Exception as e:
            return Response({"status": "0", "message": "Lead deletion failed", "errors": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # If deletion is successful, return a success message
        return Response({"status": "1", "message": "Lead deleted successfully"}, status=status.HTTP_200_OK)





class LeadSearchView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        name = request.query_params.get('name', '').strip()
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')

        # Validate missing dates
        if (from_date_str and not to_date_str) or (to_date_str and not from_date_str):
            return Response(
                {"status": "0", "message": "Both 'from_date' and 'to_date' must be provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not name and not (from_date_str and to_date_str):
            return Response(
                {"status": "0", "message": "Provide at least 'name' or both 'from_date' and 'to_date'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        leads = Lead.objects.filter(CustomUser=request.user).order_by('-created_at')

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
                    leads = leads.filter(created_at__range=(day_start, day_end))
                else:
                    from_date = make_aware(datetime.combine(from_parsed, datetime.min.time()))
                    to_date = make_aware(datetime.combine(to_parsed, datetime.max.time()))
                    leads = leads.filter(created_at__range=(from_date, to_date))

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format. Use 'YYYY-MM-DD'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if name:
            # leads = leads.filter(name__icontains=name)
            search_terms = name.strip().split()
            query = Q()
            for term in search_terms:
                query &= Q(name__icontains=term)
            leads = leads.filter(query)

        serializer = LeadSerializer(leads, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)




class MeetingsView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request):
        meetings = Meeting.objects.filter(lead__CustomUser=request.user).order_by('-created_at')
        serializer = MeetingSerializerDisplay(meetings, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MeetingSerializer(data=request.data)
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
    permission_classes = [IsAuthenticated]


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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lead_name = request.query_params.get('lead_name', '').strip()
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')

        # Validate missing dates
        if (from_date_str and not to_date_str) or (to_date_str and not from_date_str):
            return Response(
                {"status": "0", "message": "Both 'from_date' and 'to_date' must be provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not lead_name and not (from_date_str and to_date_str):
            return Response(
                {"status": "0", "message": "Provide at least 'lead_name' or both 'from_date' and 'to_date'."},
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

        serializer = MeetingSerializerDisplay(meetings, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "data": serializer.data
        }, status=status.HTTP_200_OK)





