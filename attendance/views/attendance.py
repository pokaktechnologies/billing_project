from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from ..models import DailyAttendance
from ..serializers import DailyAttendanceSerializer, DailyAttendanceSessionDetailSerializer
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from rest_framework.response import Response

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


class DailyAttendanceSessionView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = DailyAttendance.objects.filter(staff__id=id)

        if start_date and end_date:
            start = parse_date(start_date)
            end = parse_date(end_date)
            if start > end:
                raise ValidationError("Start date cannot be after end date.")

        if start_date:
            queryset = queryset.filter(date__gte=start)
        if end_date:
            queryset = queryset.filter(date__lte=end)

        # ✅ total hours with date filter
        hurs = queryset.aggregate(
            total_hours=Sum('total_working_hours')
        )['total_hours'] or 0

        queryset = queryset.order_by('-date')
        serializer = DailyAttendanceSessionDetailSerializer(queryset, many=True)

        return Response({
            "total_working_hours": hurs,
            "data": serializer.data
        }, status=200)


