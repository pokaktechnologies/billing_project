from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import DailyAttendance
from accounts.models import JobDetail, StaffProfile
from .serializers import DailyAttendanceSerializer
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import DailyAttendanceSerializer, DailyAttendanceEmployeeViewSerializer,DailyAttendanceSessionDetailSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
from django.db.models import Avg
from django.db.models import Count, Q

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
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get(self, request, id):
        staff_detail = JobDetail.objects.get(staff__id=id)
        serializer = DailyAttendanceEmployeeViewSerializer(staff_detail)
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
                "present_days": present_days,
                "half_days": half_days,
                "absent_days": absent_days,
        }

        return Response(data, status=200)

class DailyAttendanceSessionView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # validation check start_date <= end_date
        if start_date and end_date:
            start = parse_date(start_date)
            end = parse_date(end_date)  
            if start > end:
                raise ValidationError("Start date cannot be after end date.")

        queryset = DailyAttendance.objects.filter(staff__id=id).order_by('-date')

        if start_date:
            queryset = queryset.filter(date__gte=start)
        if end_date:
            queryset = queryset.filter(date__lte=end)


        serializer = DailyAttendanceSessionDetailSerializer(queryset, many=True)
        return Response(serializer.data, status=200)


class StaffAttendanceTodayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today_view = DailyAttendanceTodayView()
        queryset = today_view.get_queryset()

    def get(self, request):
        # Base queryset from your existing view
        today_view = DailyAttendanceTodayView()
        queryset = today_view.get_queryset()

        # -----------------------------
        # 📌 DATE RANGE FILTER
        # -----------------------------
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        parsed_start = None
        parsed_end = None

        if start_date and end_date:
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=400
                )

            queryset = queryset.filter(date__range=[parsed_start, parsed_end])

        # -----------------------------
        # 📌 TODAY VALUE (still needed)
        # -----------------------------
        today = timezone.localdate()

        # -----------------------------
        # 📌 COUNTS (affected by range if provided)
        # -----------------------------
        total_logged_in = (
            queryset.filter(sessions__login_time__isnull=False)
            .distinct()
            .count()
        )

        present_count = queryset.filter(status='full_day').count()
        half_day_count = queryset.filter(status='half_day').count()
        leave_count = queryset.filter(status='leave').count()

        # -----------------------------
        # 📌 WEEKLY AVERAGE WORKING HOURS
        # -----------------------------
        week_start = today - timezone.timedelta(days=6)
        week_queryset = DailyAttendance.objects.filter(date__range=[week_start, today])

        avg_working_hours = (
            week_queryset.aggregate(avg_hours=Avg('total_working_hours'))['avg_hours'] or 0
        )

        # -----------------------------
        # 📌 RESPONSE
        # -----------------------------
        data = {
            "today": str(today),
            "start_date": str(parsed_start) if parsed_start else None,
            "end_date": str(parsed_end) if parsed_end else None,

            "total_staff_logged": total_logged_in,
            "present_count": present_count,
            "half_day_count": half_day_count,
            "leave_count": leave_count,

            "average_working_hours_this_week": round(avg_working_hours, 2),
        }

        return Response(data)

class StaffWiseAttendanceStats(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        department = request.query_params.get("department")
        staff_ids = request.query_params.getlist("staff")  # supports ?staff=1&staff=2

        # -----------------------------
        # BASE STAFF QUERY
        # -----------------------------
        staff_qs = StaffProfile.objects.select_related("user", "job_detail", "job_detail__department")

        # --- FILTER BY DEPARTMENT ---
        if department:
            staff_qs = staff_qs.filter(job_detail__department_id=department)

        # --- FILTER BY STAFF IDS ---
        if staff_ids:
            staff_qs = staff_qs.filter(id__in=staff_ids)

        # -----------------------------
        # ATTENDANCE QUERY (FILTERED BY STAFF IDs IF GIVEN)
        # -----------------------------
        attendance_qs = DailyAttendance.objects.all()

        if staff_ids:
            attendance_qs = attendance_qs.filter(staff_id__in=staff_ids)

        # --- DATE RANGE ---
        if start_date:
            attendance_qs = attendance_qs.filter(date__gte=start_date)

        if end_date:
            attendance_qs = attendance_qs.filter(date__lte=end_date)

        # -----------------------------
        # GROUP & AGGREGATE
        # -----------------------------
        stats_map = {
            row["staff_id"]: row
            for row in attendance_qs.values("staff_id").annotate(
                total_records=Count("id"),
                present_count=Count("id", filter=Q(status="full_day")),
                half_day_count=Count("id", filter=Q(status="half_day")),
                leave_count=Count("id", filter=Q(status="leave")),
            )
        }

        # -----------------------------
        # FINAL RESULT
        # -----------------------------
        results = []
        for staff in staff_qs:
            s = stats_map.get(staff.id, {})

            results.append({
                "staff_id": staff.id,
                "name": f"{staff.user.first_name} {staff.user.last_name}",
                "email": staff.user.email,
                "department": staff.job_detail.department.name if staff.job_detail and staff.job_detail.department else None,

                "total_records": s.get("total_records", 0),
                "present_count": s.get("present_count", 0),
                "half_day_count": s.get("half_day_count", 0),
                "leave_count": s.get("leave_count", 0),
            })

        return Response(results)

