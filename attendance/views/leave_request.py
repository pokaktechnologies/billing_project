from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import LeaveRequest
from ..serializers import LeaveRequestSerializer, HrLeaveRequestSerializer
from accounts.models import StaffProfile
from django.utils import timezone

class EmployeeLeaveRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
             staff_profile = request.user.staff_profile
             leave_requests = LeaveRequest.objects.filter(staff=staff_profile).order_by('-requested_at')
             serializer = LeaveRequestSerializer(leave_requests, many=True)
             return Response(serializer.data, status=status.HTTP_200_OK)
        except StaffProfile.DoesNotExist:
             return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            staff_profile = request.user.staff_profile
        except StaffProfile.DoesNotExist:
            return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveRequestSerializer(data=request.data,context={'request': request})
        if serializer.is_valid():
            serializer.save(staff=staff_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmployeeLeaveRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, staff_profile):
        try:
            return LeaveRequest.objects.get(pk=pk, staff=staff_profile)
        except LeaveRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        try:
            staff_profile = request.user.staff_profile
        except StaffProfile.DoesNotExist:
             return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

        leave_request = self.get_object(pk, staff_profile)
        if not leave_request:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveRequestSerializer(leave_request)
        return Response(serializer.data)

    def patch(self, request, pk):
        try:
            staff_profile = request.user.staff_profile
        except StaffProfile.DoesNotExist:
             return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

        leave_request = self.get_object(pk, staff_profile)
        if not leave_request:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = LeaveRequestSerializer(leave_request, data=request.data, partial=True,context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            staff_profile = request.user.staff_profile
        except StaffProfile.DoesNotExist:
             return Response({"detail": "Staff profile not found."}, status=status.HTTP_404_NOT_FOUND)

        leave_request = self.get_object(pk, staff_profile)
        if not leave_request:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if leave_request.status != "PENDING":
             return Response({"detail": "Cannot delete a leave request that is not pending."}, status=status.HTTP_400_BAD_REQUEST)

        leave_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── HR / Admin Leave Report ───────────────────────────────────────────────

class HrLeaveRequestListCreateView(APIView):
    """Admin-side: list all leave requests, create on behalf of any staff."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = LeaveRequest.objects.select_related(
            'staff__user', 'action_by__user'
        ).order_by('-requested_at')

        # Optional filters
        staff_id = request.query_params.get('staff_id')
        status_filter = request.query_params.get('status')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        serializer = HrLeaveRequestSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = HrLeaveRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HrLeaveRequestDetailView(APIView):
    """Admin-side: retrieve, update, or delete any leave request."""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return LeaveRequest.objects.select_related(
                'staff__user', 'action_by__user'
            ).get(pk=pk)
        except LeaveRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        leave_request = self.get_object(pk)
        if not leave_request:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = HrLeaveRequestSerializer(leave_request)
        return Response(serializer.data)

    def put(self, request, pk):
        leave_request = self.get_object(pk)
        if not leave_request:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = HrLeaveRequestSerializer(leave_request, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        leave_request = self.get_object(pk)
        if not leave_request:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = HrLeaveRequestSerializer(leave_request, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        leave_request = self.get_object(pk)
        if not leave_request:
            return Response({"detail": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        leave_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
