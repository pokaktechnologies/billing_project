from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import DailyAttendance
from .serializers import DailyAttendanceSerializer
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import DailyAttendance
from .serializers import DailyAttendanceSerializer

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
