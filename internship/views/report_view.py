from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Count, Q, F, Sum

from accounts.models import StaffProfile
from accounts.permissions import HasModulePermission
from internship.models import Task, TaskSubmission, AssignedStaffCourse, TaskAssignment, CoursePayment
from internship.serializers.report_serializers import TaskReportSerializer, InternTaskPerformanceReportSerializer, \
    TaskSubmissionReportSerializer, InternPaymentSummaryReportSerializer, InternSummaryReportSerializer, \
    EnrollmentReportSerializer


# report based on tasks
class TaskReportAPIView(generics.ListAPIView):
    serializer_class = TaskReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TaskAssignment.objects.select_related(
            "task",
            "task__course",
            "staff",
            "staff__user"
        ).order_by("-assigned_at")

        # Assigned Date filter
        assigned_date = self.request.query_params.get("assigned_date")
        if assigned_date:
            queryset = queryset.filter(
                assigned_at__date=assigned_date
            )

        # Status filter
        status = self.request.query_params.get("status")
        if status and status.lower() != "all":
            status_mapping = {
                "Pending": "pending",
                "Submitted": "submitted",
                "Approved": "completed",
                "Revision": "revision_required"
            }
            queryset = queryset.filter(
                status=status_mapping.get(status, status)
            )

        # Course filter
        course = self.request.query_params.get("course")
        if course and course.lower() != "all":
            queryset = queryset.filter(
                task__course_id=course
            )
        return queryset


# report based on per intern task performance
class InternTaskPerformanceReportView(generics.ListAPIView):
    serializer_class = InternTaskPerformanceReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = AssignedStaffCourse.objects.select_related(
            "staff",
            "staff__user",
            "course"
        )
        # Search by intern name
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=search) |
                Q(staff__user__last_name__icontains=search)
            )

        # Filter by course id
        course = self.request.query_params.get("course")
        if course and course not in ["", "all", "All"]:
            queryset = queryset.filter(course_id=int(course))
        return queryset.order_by("-assigned_date")


# reports based on task submission
class TaskSubmissionReportAPIView(generics.ListAPIView):
    serializer_class = TaskSubmissionReportSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        queryset = TaskSubmission.objects.select_related(
            "assignment",
            "assignment__staff",
            "assignment__staff__user",
            "assignment__task",
            "assignment__task__course"
        )
        submission_date = self.request.query_params.get("submission_date")
        status = self.request.query_params.get("status")

        if submission_date:
            queryset = queryset.filter(
                submitted_at__date=submission_date
            )
        if status:
            status = status.strip().lower()
            if status == "approved":
                queryset = queryset.filter(assignment__status="completed")
            elif status == "revision":
                queryset = queryset.filter(assignment__status="revision_required")
            elif status == "submitted":
                queryset = queryset.filter(assignment__status="submitted")
            elif status == "pending":
                queryset = queryset.filter(assignment__status="pending")
        print(self.request.query_params)
        return queryset.order_by("-submitted_at")


# report based on intern payment details
class InternPaymentSummaryReportAPIView(generics.ListAPIView):
    serializer_class = InternPaymentSummaryReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = AssignedStaffCourse.objects.select_related(
            "staff",
            "staff__user",
            "course"
        )

        # Filter by course
        course = self.request.query_params.get("course")
        if course and course.strip().lower() != "all":
            queryset = queryset.filter(course_id=int(course))

        # Filter by payment status
        payment_status = self.request.query_params.get("payment_status")
        if payment_status and payment_status.strip().lower() != "all":
            filtered_ids = []
            for obj in queryset:
                total_fee = obj.course.total_fee
                paid = CoursePayment.objects.filter(
                    staff=obj.staff,
                    installment__course=obj.course
                ).aggregate(total=Sum("amount_paid"))["total"] or 0
                pending = total_fee - paid
                if payment_status.lower() == "fully paid" and pending <= 0:
                    filtered_ids.append(obj.id)
                elif payment_status.lower() == "pending" and pending > 0:
                    filtered_ids.append(obj.id)
                elif payment_status.lower() == "overdue" and pending > 0:
                    filtered_ids.append(obj.id)
            queryset = queryset.filter(id__in=filtered_ids)
        return queryset.order_by("-assigned_date")


# report based on intern summary
class InternSummaryReportAPIView(generics.ListAPIView):
    serializer_class = InternSummaryReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = AssignedStaffCourse.objects.select_related(
            "staff",
            "staff__user",
            "course"
        )

        # Filter by course
        course = self.request.query_params.get("course")
        if course and course.strip().lower() != "all":
            # support both ID and course name
            if course.isdigit():
                queryset = queryset.filter(course_id=int(course))
            else:
                queryset = queryset.filter(course__title__icontains=course)

        # Filter by intern name
        intern_name = self.request.query_params.get("intern_name")
        if intern_name and intern_name.strip().lower() != "all":
            queryset = queryset.filter(
                staff__user__first_name__icontains=intern_name
            ) | queryset.filter(
                staff__user__last_name__icontains=intern_name
            )
        return queryset.order_by("-assigned_date")


# report based on enrollment
class EnrollmentReportAPIView(generics.ListAPIView):
    serializer_class = EnrollmentReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = AssignedStaffCourse.objects.select_related(
            "staff",
            "staff__user",
            "staff__job_detail",
            "course"
        )

        # Enrollment Date Filter
        enrollment_date = self.request.query_params.get("enrollment_date")
        if enrollment_date and enrollment_date.strip().lower() != "all":
            queryset = queryset.filter(
                assigned_date=enrollment_date
            )

        # Status Filter (Active / Completed)
        status = self.request.query_params.get("status")
        if status and status.strip().lower() != "all":
            queryset = queryset.filter(
                staff__job_detail__status__iexact=status
            )

        return queryset.order_by("-assigned_date")
