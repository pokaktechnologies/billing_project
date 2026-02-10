from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime
from django.db.models import Avg, Count, Q
from ..models import DailyAttendance
from accounts.models import StaffProfile
from .attendance import DailyAttendanceTodayView

class StaffAttendanceTodayView(APIView):
    permission_classes = [IsAuthenticated]

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
        job_type = request.query_params.get("job_type")
        staff_ids = [sid for sid in request.query_params.getlist("staff") if sid.isdigit()]  # supports ?staff=1&staff=2

        # -----------------------------
        # BASE STAFF QUERY
        # -----------------------------
        staff_qs = StaffProfile.objects.select_related("user", "job_detail", "job_detail__department")

        # --- FILTER BY DEPARTMENT ---
        if department:
            staff_qs = staff_qs.filter(job_detail__department_id=department)

        # --- FILTER BY JOB TYPE ---
        if job_type:
            staff_qs = staff_qs.filter(job_detail__job_type=job_type)

        # --- FILTER BY STAFF IDS ---
        if staff_ids:
            staff_qs = staff_qs.filter(id__in=staff_ids)

        # -----------------------------
        # ATTENDANCE QUERY (CONSISTENT WITH STAFF FILTERS)
        # -----------------------------
        attendance_qs = DailyAttendance.objects.filter(staff__in=staff_qs)

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
            job_detail = getattr(staff, "job_detail", None)
            department = getattr(job_detail, "department", None) if job_detail else None

            results.append({
                "staff_id": staff.id,
                "name": f"{staff.user.first_name} {staff.user.last_name}",
                "email": staff.user.email,
                "department": department.name if department else None,

                "total_records": s.get("total_records", 0),
                "present_count": s.get("present_count", 0),
                "half_day_count": s.get("half_day_count", 0),
                "leave_count": s.get("leave_count", 0),
            })

        return Response(results)

class AllStaffWiseAttendanceStats(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        department = request.query_params.get("department")
        job_type = request.query_params.get("job_type")
        staff_ids = [sid for sid in request.query_params.getlist("staff") if sid.isdigit()]

        # -----------------------------
        # BASE STAFF QUERY
        # -----------------------------
        staff_qs = StaffProfile.objects.select_related("user", "job_detail", "job_detail__department")

        # --- FILTER BY DEPARTMENT ---
        if department:
            staff_qs = staff_qs.filter(job_detail__department_id=department)

        # --- FILTER BY JOB TYPE ---
        if job_type:
            staff_qs = staff_qs.filter(job_detail__job_type=job_type)

        # --- FILTER BY STAFF IDS ---
        if staff_ids:
            staff_qs = staff_qs.filter(id__in=staff_ids)

        # -----------------------------
        # ATTENDANCE QUERY (CONSISTENT WITH STAFF FILTERS)
        # -----------------------------
        attendance_qs = DailyAttendance.objects.filter(staff__in=staff_qs)

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

            job_detail = getattr(staff, "job_detail", None)
            department = getattr(job_detail, "department", None) if job_detail else None

            results.append({
                "staff_id": staff.id,
                "name": f"{staff.user.first_name} {staff.user.last_name}",
                "email": staff.user.email,
                "department": department.name if department else None,

                "total_records": s.get("total_records", 0),
                "present_count": s.get("present_count", 0),
                "half_day_count": s.get("half_day_count", 0),
                "leave_count": s.get("leave_count", 0),
            })

        return Response(results)
