from datetime import timedelta
from datetime import datetime
from django.utils.timezone import now, make_aware
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Count, Q, F, Sum

from accounts.models import StaffProfile
from accounts.permissions import HasModulePermission
from internship.models import Center, Task, TaskSubmission, AssignedStaffCourse, TaskAssignment, CoursePayment
from internship.serializers.report_serializers import CenterDetailReportSerializer, CenterReportsSerializer, TaskReportSerializer, InternTaskPerformanceReportSerializer, \
    TaskSubmissionReportSerializer, InternPaymentSummaryReportSerializer, InternSummaryReportSerializer, \
    EnrollmentReportSerializer
from internship.utils import get_installment_due_date_for_staff, get_next_unpaid_installment_item


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

        # filter with intern_id
        intern_id = self.request.query_params.get("intern_id")
        if intern_id and intern_id.strip().lower() != "all":
            queryset = queryset.filter(staff_id=int(intern_id))

        # Assigned Date filter
        assigned_date = self.request.query_params.get("assigned_date")
        if assigned_date and assigned_date.strip().lower() != "all":
            start = make_aware(
                datetime.strptime(assigned_date.strip(), "%Y-%m-%d")
            )
            end = start + timedelta(days=1)
            queryset = queryset.filter(
                assigned_at__gte=start,
                assigned_at__lt=end
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
        # filter by intern_id
        intern_id = self.request.query_params.get("intern_id")

        if intern_id and intern_id.strip().lower() not in ["", "all"]:
            queryset = queryset.filter(
                staff_id=int(intern_id)
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

        # filter with intern_id
        intern_id = self.request.query_params.get("intern_id")
        if intern_id and intern_id.strip().lower() not in ["", "all"]:
            queryset = queryset.filter(
                assignment__staff_id=int(intern_id)
            )

        # filter with submission date
        submission_date = self.request.query_params.get("submission_date")
        if submission_date:
            start = make_aware(
                datetime.strptime(submission_date, "%Y-%m-%d")
            )
            end = start + timedelta(days=1)
            queryset = queryset.filter(
                submitted_at__gte=start,
                submitted_at__lt=end
            )

        # filter with status
        status = self.request.query_params.get("status")
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
        # filter by intern_id
        intern_id = self.request.query_params.get("intern_id")
        if intern_id and intern_id.strip().lower() not in ["", "all"]:

            queryset = queryset.filter(
                staff_id=int(intern_id)
            )

        # Filter by course
        course = self.request.query_params.get("course")
        if course and course.strip().lower() != "all":
            queryset = queryset.filter(course_id=int(course))
        # Filter by payment status
        payment_status = self.request.query_params.get("payment_status")
        if payment_status and payment_status.strip().lower() != "all":
            filtered_ids = []
            today = now().date()
            for obj in queryset:
                total_fee = obj.course.total_fee
                paid = CoursePayment.objects.filter(
                    student__profile=obj.staff,
                    installments__plan__course=obj.course
                ).aggregate(total=Sum("amount_paid"))["total"] or 0
                pending = total_fee - paid
                next_installment = get_next_unpaid_installment_item(
                    obj.staff,
                    obj.course,
                )
                next_due_date = get_installment_due_date_for_staff(
                    obj.staff,
                    next_installment,
                )
                is_overdue = bool(next_due_date and next_due_date < today)
                if payment_status.lower() == "fully paid" and pending <= 0:
                    filtered_ids.append(obj.id)
                elif payment_status.lower() == "pending" and pending > 0 and not is_overdue:
                    filtered_ids.append(obj.id)
                elif payment_status.lower() == "overdue" and pending > 0 and is_overdue:
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

        # filter by intern id
        intern_id = self.request.query_params.get("intern_id")
        if intern_id and intern_id.strip().lower() != "all":
            if intern_id.isdigit():
                queryset = queryset.filter(
                    staff_id=int(intern_id)
                )

        # filter by intern name
        intern_name = self.request.query_params.get("intern_name")
        if intern_name and intern_name.strip().lower() != "all":
            intern_clean = intern_name.strip()
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=intern_clean) |
                Q(staff__user__last_name__icontains=intern_clean)
            )

        # filter by course
        course = self.request.query_params.get("course")
        if course and course.strip().lower() != "all":
            course_clean = course.strip()
            if course_clean.isdigit():
                queryset = queryset.filter(
                    course_id=int(course_clean)
                )
            else:
                queryset = queryset.filter(
                    course__title__icontains=course_clean
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

        # filter with intern_id
        intern_id = self.request.query_params.get("intern_id")
        if intern_id and intern_id.strip().lower() != "all":
            if intern_id.isdigit():
                queryset = queryset.filter(
                    staff_id=int(intern_id)
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

        # filter with intern_name
        intern_name = self.request.query_params.get("intern_name")
        if intern_name and intern_name.strip().lower() != "all":
            name_clean = intern_name.strip()
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=name_clean) |
                Q(staff__user__last_name__icontains=name_clean)
            )
        return queryset.order_by("-assigned_date")




class CenterReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CenterReportsSerializer

    def get_queryset(self):
        return Center.objects.annotate(
            total_students=Count("students"),
            active_students=Count("students", filter=Q(students__is_active=True)),
            inactive_students=Count("students", filter=Q(students__is_active=False)),
            total_courses=Count("students__course", distinct=True),
            faculties=Count("students__batch__faculties", distinct=True),  # count annotate
        )
    


class CenterDetailReportView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CenterDetailReportSerializer
    queryset = Center.objects.all()


from ..models import Batch, Course
from ..serializers.report_serializers import BatchDetailReportSerializer, BatchReportSerializer, CourseDetailReportSerializer, CourseReportSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q


class BatchReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Batch.objects.select_related("course").annotate(
            student_count=Count(
                "enrollments__student",
                filter=Q(enrollments__student__is_active=True),
                distinct=True
            )
        )

        course_id = request.query_params.get("course_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        completed = request.query_params.get("completed")

        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        if completed is not None:
            if completed.lower() == "true":
                queryset = queryset.filter(end_date__lt=now().date())
        else:
            queryset = queryset.filter(end_date__gte=now().date())

        queryset = queryset.order_by("-created_at")

        serializer = BatchReportSerializer(queryset, many=True)
        return Response(serializer.data)


class BatchDetailReportAPIView(generics.RetrieveAPIView):
    serializer_class = BatchDetailReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = Batch.objects.select_related("course").all()



class CourseReportAPIView(generics.ListAPIView):
    serializer_class = CourseReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Course.objects.select_related(
            "department"
        ).annotate(
            total_students=Count("enrollments__student", distinct=True),
            active_students=Count(
                "enrollments__student",
                filter=Q(enrollments__student__is_active=True),
                distinct=True
            ),
            inactive_students=Count(
                "enrollments__student",
                filter=Q(enrollments__student__is_active=False),
                distinct=True
            ),
            total_batches=Count("batches", distinct=True),
            active_batches=Count(
                "batches",
                filter=Q(batches__is_active=True),
                distinct=True
            ),
            total_faculties=Count("faculties", distinct=True),
        )

        # Filters
        is_active = self.request.query_params.get("is_active")
        department_id = self.request.query_params.get("department_id")
        search = self.request.query_params.get("search")

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset.order_by("-created_at")


class CourseDetailReportAPIView(generics.RetrieveAPIView):
    serializer_class = CourseDetailReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = Course.objects.select_related("department").prefetch_related(
        "batches", "faculties__user__user", "faculties__department"
    ).all()