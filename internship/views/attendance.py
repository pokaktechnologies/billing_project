from datetime import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    ClassAttendanceSession,
    Faculty,
    Section,
    Student,
    StudentAttendanceRecord,
    StudentCourseEnrollment,
)
from ..serializers.attendance import (
    BulkAttendanceSubmitSerializer,
    ClassAttendanceSessionHistorySerializer,
    SectionAttendanceRosterSerializer,
    StudentAttendanceDetailItemSerializer,
)
from ..utils import get_authenticated_student


def _get_faculty_for_user(user):
    """Returns the active Faculty object for a given user, or None."""
    if not user or not user.is_authenticated:
        return None
    try:
        return Faculty.objects.select_related("user__user").get(
            user__user=user,
            is_active=True
        )
    except Faculty.DoesNotExist:
        return None


def _check_faculty_section_permission(user, section):
    """
    Checks if the user has permission to manage attendance for this section.
    Allowed if user is a superuser, staff, or an assigned faculty to section's batch.
    """
    if user.is_superuser or user.is_staff:
        return True, _get_faculty_for_user(user)

    faculty = _get_faculty_for_user(user)
    if not faculty:
        return False, None

    # Check if faculty is assigned to the section's batch
    is_assigned = section.batch.faculties.filter(id=faculty.id).exists()
    return is_assigned, faculty


class SectionAttendanceAPIView(APIView):
    """
    GET  /api/internship/sections/<section_id>/attendance/?date=YYYY-MM-DD
         Returns student roster with attendance statuses for the section on a given date.
    POST /api/internship/sections/<section_id>/attendance/
         Bulk submits or updates student attendance for the section on a given date.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, section_id):
        section = get_object_or_404(
            Section.objects.select_related("class_obj", "class_obj__center", "batch", "batch__course"),
            pk=section_id
        )

        has_permission, faculty = _check_faculty_section_permission(request.user, section)
        if not has_permission:
            return Response(
                {"detail": "You do not have permission to access attendance for this class section."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Parse date query parameter (defaults to today)
        date_str = request.query_params.get("date")
        if date_str:
            try:
                attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"date": "Invalid date format. Expected YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            attendance_date = timezone.now().date()

        # Query active enrolled students in this section's batch
        enrollments = (
            StudentCourseEnrollment.objects
            .filter(batch=section.batch, student__is_active=True)
            .select_related("student", "student__profile", "student__profile__user")
            .order_by("student__profile__user__first_name", "student__student_id")
        )

        # Query if attendance session already exists for this date
        session = (
            ClassAttendanceSession.objects
            .filter(section=section, date=attendance_date)
            .select_related("faculty__user__user")
            .prefetch_related("records")
            .first()
        )

        existing_records_map = {}
        if session:
            existing_records_map = {
                rec.student_id: rec for rec in session.records.all()
            }

        students_data = []
        for enrollment in enrollments:
            student = enrollment.student
            user = student.profile.user if student.profile else None

            existing_record = existing_records_map.get(student.id)
            profile_image_url = None
            if student.profile and student.profile.profile_image:
                try:
                    profile_image_url = student.profile.profile_image.url
                except Exception:
                    profile_image_url = None

            students_data.append({
                "student_id": student.id,
                "student_code": student.student_id,
                "name": student.get_full_name() if user else "Unknown",
                "email": user.email if user else "",
                "phone_number": getattr(student.profile, "phone_number", None),
                "profile_image": profile_image_url,
                "status": existing_record.status if existing_record else "present",
                "remarks": existing_record.remarks if existing_record and existing_record.remarks else "",
            })

        marked_by_name = None
        if session and session.faculty:
            marked_by_name = session.faculty.get_full_name()

        roster_data = {
            "section_id": section.id,
            "class_id": section.class_obj.id,
            "class_name": section.class_obj.name,
            "center_id": section.class_obj.center_id,
            "center_name": section.class_obj.center.name if section.class_obj.center else None,
            "batch_id": section.batch.id,
            "batch_number": section.batch.batch_number,
            "course_id": section.batch.course_id,
            "course_title": section.batch.course.title if section.batch.course else "",
            "start_time": section.start_time,
            "end_time": section.end_time,
            "date": attendance_date,
            "is_marked": session is not None,
            "session_id": session.id if session else None,
            "topic_covered": session.topic_covered if session else None,
            "notes": session.notes if session else None,
            "marked_by": marked_by_name,
            "marked_at": session.updated_at if session else None,
            "total_enrolled": len(students_data),
            "students": students_data,
        }

        serializer = SectionAttendanceRosterSerializer(roster_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, section_id):
        section = get_object_or_404(
            Section.objects.select_related("batch", "batch__course"),
            pk=section_id
        )

        has_permission, faculty = _check_faculty_section_permission(request.user, section)
        if not has_permission:
            return Response(
                {"detail": "You do not have permission to mark attendance for this class section."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BulkAttendanceSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        attendance_date = validated_data["date"]
        topic_covered = validated_data.get("topic_covered", "")
        notes = validated_data.get("notes", "")
        records = validated_data["records"]

        # Validate that all students belong to this section's batch
        valid_student_ids = set(
            StudentCourseEnrollment.objects
            .filter(batch=section.batch)
            .values_list("student_id", flat=True)
        )

        invalid_ids = [
            item["student_id"] for item in records if item["student_id"] not in valid_student_ids
        ]
        if invalid_ids:
            return Response(
                {
                    "records": f"The following student IDs are not enrolled in this section's batch: {invalid_ids}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Atomic transaction to create or update the session and student records
        with transaction.atomic():
            session, _created = ClassAttendanceSession.objects.update_or_create(
                section=section,
                date=attendance_date,
                defaults={
                    "faculty": faculty,
                    "topic_covered": topic_covered,
                    "notes": notes,
                }
            )

            # Upsert student attendance records
            present_count = 0
            absent_count = 0
            leave_count = 0
            late_count = 0

            for item in records:
                st = item["status"]
                if st == "present":
                    present_count += 1
                elif st == "absent":
                    absent_count += 1
                elif st == "leave":
                    leave_count += 1
                elif st == "late":
                    late_count += 1

                StudentAttendanceRecord.objects.update_or_create(
                    session=session,
                    student_id=item["student_id"],
                    defaults={
                        "status": st,
                        "remarks": item.get("remarks", ""),
                    }
                )

        return Response(
            {
                "detail": "Attendance recorded successfully.",
                "session_id": session.id,
                "date": attendance_date,
                "summary": {
                    "total": len(records),
                    "present": present_count,
                    "absent": absent_count,
                    "leave": leave_count,
                    "late": late_count,
                }
            },
            status=status.HTTP_200_OK
        )


SectionAttendanceRosterAPIView = SectionAttendanceAPIView
SectionAttendanceSubmitAPIView = SectionAttendanceAPIView


class SectionAttendanceHistoryAPIView(APIView):
    """
    GET /api/internship/sections/<section_id>/attendance-history/
    Lists past attendance sessions for a section with summary statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, section_id):
        section = get_object_or_404(
            Section.objects.select_related("batch"),
            pk=section_id
        )

        has_permission, _ = _check_faculty_section_permission(request.user, section)
        if not has_permission:
            return Response(
                {"detail": "You do not have permission to view attendance history for this section."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = (
            ClassAttendanceSession.objects
            .filter(section=section)
            .select_related("faculty__user__user")
            .prefetch_related("records")
            .order_by("-date", "-created_at")
        )

        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")

        if from_date:
            try:
                queryset = queryset.filter(date__gte=datetime.strptime(from_date, "%Y-%m-%d").date())
            except ValueError:
                return Response({"from_date": "Invalid format. Expected YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if to_date:
            try:
                queryset = queryset.filter(date__lte=datetime.strptime(to_date, "%Y-%m-%d").date())
            except ValueError:
                return Response({"to_date": "Invalid format. Expected YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ClassAttendanceSessionHistorySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentMyAttendanceAPIView(APIView):
    """
    GET /api/internship/my-attendance/
    Allows an authenticated intern/student to view their attendance summary and records.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = get_authenticated_student(request.user)
        if not student:
            return Response(
                {"detail": "User has no student profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = (
            StudentAttendanceRecord.objects
            .filter(student=student)
            .select_related(
                "session",
                "session__section",
                "session__section__class_obj",
                "session__section__batch",
                "session__section__batch__course",
            )
            .order_by("-session__date", "-created_at")
        )

        # Optional filters
        course_id = request.query_params.get("course_id")
        if course_id:
            queryset = queryset.filter(session__section__batch__course_id=course_id)

        batch_id = request.query_params.get("batch_id")
        if batch_id:
            queryset = queryset.filter(session__section__batch_id=batch_id)

        from_date = request.query_params.get("from_date")
        if from_date:
            try:
                queryset = queryset.filter(session__date__gte=datetime.strptime(from_date, "%Y-%m-%d").date())
            except ValueError:
                return Response({"from_date": "Invalid format. Expected YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        to_date = request.query_params.get("to_date")
        if to_date:
            try:
                queryset = queryset.filter(session__date__lte=datetime.strptime(to_date, "%Y-%m-%d").date())
            except ValueError:
                return Response({"to_date": "Invalid format. Expected YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        total_sessions = queryset.count()
        present_count = queryset.filter(status="present").count()
        absent_count = queryset.filter(status="absent").count()
        leave_count = queryset.filter(status="leave").count()
        late_count = queryset.filter(status="late").count()

        # Late is considered attending class
        effective_attended = present_count + late_count
        attendance_percentage = (
            round((effective_attended / total_sessions) * 100, 1)
            if total_sessions > 0
            else 0.0
        )

        records_serializer = StudentAttendanceDetailItemSerializer(queryset, many=True)

        return Response(
            {
                "summary": {
                    "total_sessions": total_sessions,
                    "present": present_count,
                    "absent": absent_count,
                    "leave": leave_count,
                    "late": late_count,
                    "attendance_percentage": attendance_percentage,
                },
                "records": records_serializer.data,
            },
            status=status.HTTP_200_OK
        )
