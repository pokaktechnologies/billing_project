from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import DailyAttendance
from .serializers import DailyAttendanceSerializer
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import DailyAttendance
from .serializers import DailyAttendanceSerializer, DailyAttendanceEmployeeViewSerializer,DailyAttendanceSessionDetailSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg

class DailyAttendanceListView(generics.ListAPIView):
    queryset = DailyAttendance.objects.all()
    serializer_class = DailyAttendanceSerializer
    permission_classes = [IsAuthenticated]

    # Enable filtering and ordering
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]

    # Filters by exact match fields
    filterset_fields = {
        'staff': ['exact'],       # filter by staff ID
        'status': ['exact'],      # leave, half_day, full_day
        'date': ['exact', 'gte', 'lte'],  # specific date or date range
    }

    # Ordering fields
    ordering_fields = ['date', 'status', 'staff']
    ordering = ['-date']  # default ordering



# 2. Get today's attendance records
class DailyAttendanceTodayView(generics.ListAPIView):
    serializer_class = DailyAttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        today = timezone.localdate()
        return DailyAttendance.objects.filter(date=today).order_by('-date')


# 3. Get attendance details by ID
class DailyAttendanceDetailView(generics.RetrieveAPIView):
    queryset = DailyAttendance.objects.all()
    serializer_class = DailyAttendanceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


class DailyAttendanceEmployeeView(generics.ListAPIView):
    serializer_class = DailyAttendanceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get(self, request, id):
        # Filter records by employee_id
        queryset = DailyAttendance.objects.filter(staff__id=id)
        print(queryset.prefetch_related('sessions').query) 
        # serializer_session = DailyAttendanceSessionDetailSerializer(queryset, many=True)
        serializer = DailyAttendanceEmployeeViewSerializer(queryset, many=True)
        return Response(serializer.data, status=200)

class DailyAttendanceDaysCountView(generics.ListAPIView):
    def get(self, request, id):
        queryset = DailyAttendance.objects.filter(staff__id=id)
        serializer = DailyAttendanceEmployeeViewSerializer(queryset, many=True)

        # 👇 status field in model is `leave`, `half_day`, `full_day`
        present_days = queryset.filter(status='full_day').count()
        absent_days = queryset.filter(status='leave').count()
        half_days = queryset.filter(status='half_day').count()

        data = {
            "id": id,
                "employee_id": serializer.data[0]['employee_id'] if serializer.data else "",
                "present_days": present_days,
                "half_days": half_days,
                "absent_days": absent_days,
        }

        return Response(data, status=200)
class DailyAttendanceSessionView(generics.ListAPIView):
    def get(self, request, id):
        queryset = DailyAttendance.objects.filter(staff__id=id)
        serializer = DailyAttendanceSessionDetailSerializer(queryset, many=True)
        return Response(serializer.data, status=200)

class StaffAttendanceTodayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_view = DailyAttendanceTodayView()
        queryset = today_view.get_queryset()  # 🔁 Reuse directly

        total_logged_in = queryset.filter(sessions__login_time__isnull=False).distinct().count()
        present_count = queryset.filter(status='full_day').count()
        half_day_count = queryset.filter(status='half_day').count()
        leave_count = queryset.filter(status='leave').count()

        # ✅ Calculate weekly average working hours
        today = timezone.localdate()
        week_start = today - timezone.timedelta(days=6)
        week_queryset = DailyAttendance.objects.filter(date__range=[week_start, today])

        avg_working_hours = week_queryset.aggregate(avg_hours=Avg('total_working_hours'))['avg_hours'] or 0

        data = {
            "date": str(today),
            "total_staff_logged_today": total_logged_in,
            "present_count": present_count,
            "half_day_count": half_day_count,
            "leave_count": leave_count,
            "average_working_hours_this_week": round(avg_working_hours, 2),
        }

        return Response(data)