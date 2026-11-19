from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import StaffProfile
from ..models import DailyAttendance
from ..serializers import DailyAttendanceSerializer, DailyAttendanceSessionDetailSerializer
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from rest_framework.response import Response
from django.db.models import Count, Q, Sum
from rest_framework.views import APIView
from rest_framework import status

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
class DailyAttendanceDetailView(generics.RetrieveUpdateAPIView):
    queryset = DailyAttendance.objects.all()
    serializer_class = DailyAttendanceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"


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


class StaffWiseAttendanceDetailReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # ----------------------------------
        # GET FILTERS
        # ----------------------------------

        staff_id = request.query_params.get("staff_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        department = request.query_params.get("department")

        # ----------------------------------
        # VALIDATE STAFF
        # ----------------------------------

        if not staff_id:
            return Response({
                "Status": "0",
                "Message": "staff_id is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not staff_id.isdigit():
            return Response({
                "Status": "0",
                "Message": "Invalid staff_id."
            }, status=status.HTTP_400_BAD_REQUEST)

        staff = (
            StaffProfile.objects
            .select_related(
                "user",
                "job_detail",
                "job_detail__department"
            )
            .filter(id=staff_id)
            .first()
        )

        if not staff:
            return Response({
                "Status": "0",
                "Message": "Staff not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # ----------------------------------
        # VALIDATE DATE RANGE
        # ----------------------------------

        parsed_start = None
        parsed_end = None

        if start_date:
            parsed_start = parse_date(start_date)

            if not parsed_start:
                return Response({
                    "Status": "0",
                    "Message": "Invalid start_date. Use YYYY-MM-DD."
                }, status=status.HTTP_400_BAD_REQUEST)

        if end_date:
            parsed_end = parse_date(end_date)

            if not parsed_end:
                return Response({
                    "Status": "0",
                    "Message": "Invalid end_date. Use YYYY-MM-DD."
                }, status=status.HTTP_400_BAD_REQUEST)

        if parsed_start and parsed_end and parsed_start > parsed_end:
            return Response({
                "Status": "0",
                "Message": "start_date cannot be greater than end_date."
            }, status=status.HTTP_400_BAD_REQUEST)

        # ----------------------------------
        # BASE ATTENDANCE QUERYSET
        # ----------------------------------

        attendances = (
            DailyAttendance.objects
            .filter(
                staff_id=staff.id,
                staff__job_detail__isnull=False
            )
            .select_related(
                "staff__user",
                "staff__job_detail__department"
            )
            .prefetch_related("sessions")
            .order_by("-date", "-id")
        )

        # ----------------------------------
        # DEPARTMENT FILTER
        # ----------------------------------

        if department:
            attendances = attendances.filter(
                staff__job_detail__department_id=department
            )

        # ----------------------------------
        # DATE FILTER
        # ----------------------------------

        if parsed_start:
            attendances = attendances.filter(
                date__gte=parsed_start
            )

        if parsed_end:
            attendances = attendances.filter(
                date__lte=parsed_end
            )

        # Default: Today's attendance
        if not parsed_start and not parsed_end:
            today = timezone.localdate()

            attendances = attendances.filter(
                date=today
            )

        # ----------------------------------
        # ATTENDANCE SUMMARY
        # ----------------------------------

        summary = attendances.aggregate(
            total_records=Count("id"),

            present_count=Count(
                "id",
                filter=Q(status="full_day")
            ),

            absent_count=Count(
                "id",
                filter=Q(status="absent")
            ),

            half_day_count=Count(
                "id",
                filter=Q(status="half_day")
            ),

            leave_count=Count(
                "id",
                filter=Q(status="leave")
            ),

            total_working_hours=Sum(
                "total_working_hours"
            )
        )

        total_records = summary["total_records"] or 0

        total_working_hours = (
            summary["total_working_hours"] or 0
        )

        # ----------------------------------
        # STAFF DETAILS
        # ----------------------------------

        job_detail = getattr(staff, "job_detail", None)

        department_name = (
            job_detail.department.name
            if job_detail and job_detail.department
            else None
        )

        # ----------------------------------
        # SERIALIZE DAILY ATTENDANCE
        # ----------------------------------

        attendance_serializer = DailyAttendanceSerializer(
            attendances,
            many=True
        )

        # ----------------------------------
        # FINAL RESPONSE
        # ----------------------------------

        return Response({

            "Status": "1",
            "Message": "Success",

            "staff_summary": {
                "staff_id": staff.id,

                "name": (
                    f"{staff.user.first_name} "
                    f"{staff.user.last_name}"
                ).strip(),

                "email": staff.user.email,

                "employee_id": (
                    job_detail.employee_id
                    if job_detail else None
                ),

                "department": department_name,

                "start_date": (
                    str(parsed_start) if parsed_start else None
                ),

                "end_date": (
                    str(parsed_end) if parsed_end else None
                ),

                "total_records": total_records,

                "present_count": summary["present_count"],

                "absent_count": summary["absent_count"],

                "half_day_count": summary["half_day_count"],

                "leave_count": summary["leave_count"],

                "total_working_hours": round(
                    float(total_working_hours), 2
                ),

                "total_hours": total_records * 9,
            },

            "attendance_details": attendance_serializer.data,

            "total_records": total_records,

        })
