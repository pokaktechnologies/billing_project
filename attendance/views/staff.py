from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import DailyAttendance
from accounts.models import JobDetail
from ..serializers import DailyAttendanceEmployeeViewSerializer

class DailyAttendanceEmployeeView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get(self, request, id):
        staff_detail = JobDetail.objects.get(staff__id=id)
        serializer = DailyAttendanceEmployeeViewSerializer(staff_detail)
        return Response(serializer.data, status=200)

class DailyAttendanceDaysCountView(generics.ListAPIView):
    def get(self, request, id):
        queryset = DailyAttendance.objects.filter(staff__id=id)
        # serializer = DailyAttendanceEmployeeViewSerializer(queryset, many=True) # Not used in original logic

        # 👇 status field in model is `leave`, `half_day`, `full_day`
        present_days = queryset.filter(status='full_day').count()
        absent_days = queryset.filter(status='leave').count()
        half_days = queryset.filter(status='half_day').count()

        data = {
            "id": id,
                "present_days": present_days,
                "half_days": half_days,
                "absent_days": absent_days,
        }

        return Response(data, status=200)
