from datetime import timedelta, datetime, time
from django.utils.timezone import now, make_aware
from django.utils.dateparse import parse_date
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Count, Q, F, Sum
from django.shortcuts import get_object_or_404
from accounts.models import StaffProfile, SalesPerson
from internship.models import Center, Task, TaskSubmission, AssignedStaffCourse, TaskAssignment, CoursePayment, Student, CounsellorHRSubmission, InternshipApplication
from internship.serializers.report_serializers import (
    SalesPersonSerializer,
    RegistrationReportSerializer,
    CounsellorConversionStudentSerializer,
    CounsellorRegistrationApplicationSerializer,
    CounsellorHRSubmissionSerializer,
    CounsellorProceedToHRSerializer,
    AdmissionsBreakdownSerializer,
    RegistrationsBreakdownSerializer,
    PaymentsBreakdownSerializer,
)
from internship.serializers.report_serializers import CenterDetailReportSerializer, CenterReportsSerializer, TaskReportSerializer, InternTaskPerformanceReportSerializer, \
    TaskSubmissionReportSerializer, InternPaymentSummaryReportSerializer, InternSummaryReportSerializer, \
    EnrollmentReportSerializer, StudentInSerializer
from internship.utils import get_installment_due_date_for_staff, get_next_unpaid_installment_item, parse_flexible_date


# report based on tasks
class TaskReportAPIView(generics.ListAPIView):
    serializer_class = TaskReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TaskAssignment.objects.select_related(
            "task",
            "student",
            "student__profile__user"
        ).prefetch_related(
            "student__enrollments__course",
            "student__enrollments__batch"
        ).order_by("-assigned_at")

        # filter with student_id
        student_id = self.request.query_params.get("student")
        if student_id and student_id.strip().lower() != "all":
            queryset = queryset.filter(student_id=int(student_id))

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
                student__enrollments__course_id=course
            )

        # batch filter
        batch = self.request.query_params.get("batch")

        if batch and batch.lower() != "all":
            queryset = queryset.filter(
                student__enrollments__batch_id=batch
            )

        return queryset.distinct()


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

        queryset = (
            TaskSubmission.objects
            .select_related(
                "assignment",
                "assignment__student",
                "assignment__student__profile__user",
                "assignment__task",
            )
            .prefetch_related(
                "assignment__student__enrollments__course",
                "assignment__student__enrollments__batch",
            )
        )

        # Student Filter
        student_id = self.request.query_params.get("student")

        if student_id and student_id.strip().lower() not in ["", "all"]:
            queryset = queryset.filter(
                assignment__student_id=int(student_id)
            )

        # Submission Date Filter
        submission_date = self.request.query_params.get(
            "submission_date"
        )

        if submission_date:

            start = make_aware(
                datetime.strptime(
                    submission_date,
                    "%Y-%m-%d"
                )
            )

            end = start + timedelta(days=1)

            queryset = queryset.filter(
                submitted_at__gte=start,
                submitted_at__lt=end
            )

        # Status Filter
        status = self.request.query_params.get("status")

        if status:

            status = status.strip().lower()

            if status == "approved":
                queryset = queryset.filter(
                    assignment__status="completed"
                )

            elif status == "revision":
                queryset = queryset.filter(
                    assignment__status="revision_required"
                )

            elif status == "submitted":
                queryset = queryset.filter(
                    assignment__status="submitted"
                )

            elif status == "pending":
                queryset = queryset.filter(
                    assignment__status="pending"
                )

        # Course Filter
        course = self.request.query_params.get("course")

        if course and course.lower() not in ["", "all"]:
            queryset = queryset.filter(
                assignment__student__enrollments__course_id=course
            )

        # Batch Filter
        batch = self.request.query_params.get("batch")

        if batch and batch.lower() not in ["", "all"]:
            queryset = queryset.filter(
                assignment__student__enrollments__batch_id=batch
            )

        return queryset.distinct().order_by("-submitted_at")


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
                    installments__enrollment__course=obj.course
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
            active_students=Count("students", filter=Q(students__status='active')),
            completed_students=Count("students", filter=Q(students__status='completed')),
            inactive_students=Count("students", filter=Q(students__status='inactive')),
            total_courses=Count("students__enrollments__course", distinct=True),
            faculties=Count("students__enrollments__batch__faculties", distinct=True),
        )
    


class CenterDetailReportView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CenterDetailReportSerializer
    queryset = Center.objects.all()


from ..models import Batch, Course, Faculty
from ..serializers.report_serializers import BatchDetailReportSerializer, BatchReportSerializer, CourseDetailReportSerializer, CourseReportSerializer, FacultyDetailReportSerializer, FacultyReportSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q


class BatchReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Batch.objects.select_related("course").annotate(
            student_count=Count(
                "enrollments__student",
                filter=Q(enrollments__student__status='active'),
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
                filter=Q(enrollments__student__status='active'),
                distinct=True
            ),
            inactive_students=Count(
                "enrollments__student",
                filter=Q(enrollments__student__status='inactive'),
                distinct=True
            ),
            completed_students=Count(
                "enrollments__student",
                filter=Q(enrollments__student__status='completed'),
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
        "batches", "faculties__user__user", "faculties__departments"
    ).all()


#councellor list view
class CounsellorListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        counsellors = SalesPerson.objects.annotate(
            total_students=Count("counselled_students")
        )

        serializer = SalesPersonSerializer(counsellors, many=True)
        return Response(serializer.data)


# students under counsellr
class CounsellorStudentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, counsellor_id):
        counsellor = get_object_or_404(SalesPerson, id=counsellor_id)

        students = Student.objects.select_related(
            "profile__user"
        ).prefetch_related(
            "enrollments__course",
            "enrollments__batch"
        ).filter(
            councellor=counsellor
        )

        serializer = StudentInSerializer(students, many=True)
        return Response({
            "counsellor": counsellor.get_full_name(),
            "total_students": students.count(),
            "students": serializer.data
        })


# counsellor conversion report
class CounsellorConversionReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, counsellor_id):
        counsellor = get_object_or_404(SalesPerson, id=counsellor_id)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        course_id = request.query_params.get("course") or request.query_params.get("course_id")
        record_type_filter = request.query_params.get("type", "all").lower().strip()

        # Parse date bounds safely
        d_start = None
        if start_date:
            try:
                d_start = parse_date(start_date)
                if not d_start:
                    return Response({"detail": f"Invalid start_date format '{start_date}'. Use YYYY-MM-DD."}, status=400)
            except ValueError as e:
                return Response({"detail": f"Invalid start_date '{start_date}': {str(e)}."}, status=400)

        d_end = None
        if end_date:
            try:
                d_end = parse_date(end_date)
                if not d_end:
                    return Response({"detail": f"Invalid end_date format '{end_date}'. Use YYYY-MM-DD."}, status=400)
            except ValueError as e:
                return Response({"detail": f"Invalid end_date '{end_date}': {str(e)}."}, status=400)

        if d_start and d_end and d_start > d_end:
            return Response({"detail": "end_date must be greater than or equal to start_date."}, status=400)

        dt_start = make_aware(datetime.combine(d_start, time.min)) if d_start else None
        dt_end = make_aware(datetime.combine(d_end, time.max)) if d_end else None

        # ── 1. New Admissions (Students) ──
        all_students = Student.objects.filter(councellor=counsellor)
        total_students_all_time = all_students.count()

        admissions_data = []
        if record_type_filter in ["all", "admission"]:
            students = all_students.select_related(
                "profile__user",
            ).prefetch_related(
                "enrollments__course",
                "course_payments",
            )
            if dt_start:
                students = students.filter(created_at__gte=dt_start)
            if dt_end:
                students = students.filter(created_at__lte=dt_end)
            if course_id:
                students = students.filter(enrollments__course_id=course_id)

            students = students.distinct().order_by("-created_at")
            admissions_data = CounsellorConversionStudentSerializer(students, many=True).data

        # ── 2. New Registrations (Unconverted Applications) ──
        registrations_data = []
        if record_type_filter in ["all", "registration"]:
            applications = InternshipApplication.objects.filter(
                councellor=counsellor,
                is_converted=False,
            ).select_related("course")

            if dt_start:
                applications = applications.filter(created_at__gte=dt_start)
            if dt_end:
                applications = applications.filter(created_at__lte=dt_end)
            if course_id:
                applications = applications.filter(course_id=course_id)

            applications = applications.distinct().order_by("-created_at")
            registrations_data = CounsellorRegistrationApplicationSerializer(applications, many=True).data

        # ── 3. Combined Records ──
        if record_type_filter == "admission":
            combined_records = admissions_data
        elif record_type_filter == "registration":
            combined_records = registrations_data
        else:
            combined_records = sorted(
                admissions_data + registrations_data,
                key=lambda r: r.get("created_at") or "",
                reverse=True,
            )

        # ── 4. Payment Totals ──
        total_payments = Decimal("0.00")
        for rec in combined_records:
            p = rec.get("payment")
            if p and p.get("amount"):
                try:
                    total_payments += Decimal(str(p["amount"]))
                except Exception:
                    pass

        # ── 5. Submission Status ──
        submission_status = None
        if start_date and end_date:
            submission = CounsellorHRSubmission.objects.filter(
                counsellor=counsellor,
                start_date=start_date,
                end_date=end_date,
            ).first()
            if submission:
                submission_status = CounsellorHRSubmissionSerializer(submission).data

        # ── 6. Team Leader Info ──
        team_leader_info = None
        # Check if designation contains Team Leader or if assigned_staff has a team lead
        if hasattr(counsellor, "team_leader") and counsellor.team_leader:
            tl = counsellor.team_leader
            team_leader_info = {
                "id": tl.id,
                "name": tl.get_full_name(),
                "email": getattr(tl, "email", None),
                "phone": getattr(tl, "phone", None),
            }

        return Response({
            "counsellor": {
                "id": counsellor.id,
                "name": counsellor.get_full_name(),
                "email": counsellor.email,
                "phone": counsellor.phone,
                "designation": counsellor.designation,
                "team_leader": team_leader_info,
            },
            "summary": {
                "total_records": len(combined_records),
                "new_admissions_count": len(admissions_data),
                "new_registrations_count": len(registrations_data),
                "total_students": len(admissions_data),  # Backwards compatibility
                "total_students_all_time": total_students_all_time,
                "total_payment_collected": f"{total_payments:.2f}",
            },
            "submission_status": submission_status,
            "records": combined_records,
            "students": combined_records,  # Backwards compatibility alias
        })


class FacultyReportAPIView(generics.ListAPIView):
    serializer_class = FacultyReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        today = now().date()

        queryset = Faculty.objects.select_related(
            "user__user"
        ).prefetch_related(
            "departments"
        ).annotate(
            total_students=Count(
                "batches__enrollments__student",
                distinct=True
            ),
            active_students=Count(
                "batches__enrollments__student",
                filter=Q(batches__end_date__gte=today) & Q(batches__enrollments__student__status='active'),
                distinct=True
            ),
            completed_students=Count(
                "batches__enrollments__student",
                filter=Q(batches__end_date__lt=today) & Q(batches__enrollments__student__status='completed'),
                distinct=True
            ),
            total_batches=Count("batches", distinct=True),
            total_courses=Count("courses", distinct=True),
        )

        is_active = self.request.query_params.get("is_active")
        department_id = self.request.query_params.get("department_id")
        search = self.request.query_params.get("search")

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        if department_id:
            queryset = queryset.filter(departments__id=department_id)
        if search:
            queryset = queryset.filter(
                Q(user__user__first_name__icontains=search) |
                Q(user__user__last_name__icontains=search)
            )

        return queryset.order_by("-id").distinct()


class FacultyDetailReportAPIView(generics.RetrieveAPIView):
    serializer_class = FacultyDetailReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = Faculty.objects.select_related(
        "user__user"
    ).prefetch_related(
        "departments", "courses", "batches__course"
    ).all()


from decimal import Decimal


class RegistrationReportAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Student.objects.select_related(
            "profile__user",
            "center",
            "councellor",
        ).prefetch_related(
            "enrollments__course",
            "enrollments__batch",
            "enrollments__batch__faculties__user__user",
            "enrollments__student_installment_items__course_payments",
            "course_payments",
        )

        # filters same...
        center_id = request.query_params.get("center_id")
        counsellor_id = request.query_params.get("counsellor_id")
        course_id = request.query_params.get("course_id")
        status = request.query_params.get("status")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        faculty_id = request.query_params.get("faculty_id")
        search = request.query_params.get("search")

        if center_id:
            queryset = queryset.filter(center_id=center_id)
        if counsellor_id:
            queryset = queryset.filter(councellor_id=counsellor_id)
        if course_id:
            queryset = queryset.filter(enrollments__course_id=course_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        if start_date:
            queryset = queryset.filter(
                enrollments__enrollment_date__gte=start_date
            )

        if end_date:
            queryset = queryset.filter(
                enrollments__enrollment_date__lte=end_date
            )
        if faculty_id:
            queryset = queryset.filter(enrollments__batch__faculties__id=faculty_id)
        if search:
            queryset = queryset.filter(
                Q(profile__user__first_name__icontains=search) |
                Q(profile__user__last_name__icontains=search) |
                Q(profile__user__email__icontains=search)
            )

        queryset = queryset.distinct().order_by("start_date")

        students_list = list(queryset)
 
        student_profile_ids = [student.profile_id for student in students_list]
        from certificates.models import CertificateRecord
        certified_profile_ids = set(
            CertificateRecord.objects.filter(user_id__in=student_profile_ids)
            .values_list('user_id', flat=True)
        )

        students_data = RegistrationReportSerializer(
            students_list,
            many=True,
            context={"certified_profile_ids": certified_profile_ids}
        ).data

        total_paid = sum(
            Decimal(str(s["paid_amount"] or 0)) for s in students_data
        )

        total_course_fee = sum(
            Decimal(str(s["discounted_fee"] or 0))
            for s in students_data
        )
        total_balance = total_course_fee - total_paid

        return Response({
            "total_students": queryset.count(),
            "total_balance": f"{total_balance:.2f}",
            "total_course_fee": f"{total_course_fee:.2f}",
            "total_paid": f"{total_paid:.2f}",
            "students": students_data,
        })


class CounsellorProceedToHRAPIView(APIView):
    """
    POST: Proceed a counsellor's verified conversions for a specific date range to HR.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, counsellor_id):
        counsellor = get_object_or_404(SalesPerson, id=counsellor_id)
        serializer = CounsellorProceedToHRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]
        period_label = serializer.validated_data.get("period_label")
        remarks = serializer.validated_data.get("remarks")

        # Check if already submitted for this exact date range
        existing = CounsellorHRSubmission.objects.filter(
            counsellor=counsellor,
            start_date=start_date,
            end_date=end_date,
        ).first()

        if existing:
            if existing.status == "submitted":
                return Response(
                    {"detail": "A submission for this counsellor and date range is already pending with HR."},
                    status=400,
                )
            elif existing.status == "approved":
                return Response(
                    {"detail": "Conversions for this counsellor and date range have already been approved by HR."},
                    status=400,
                )
            # If previously rejected, allow re-submission
            existing.status = "submitted"
            existing.period_label = period_label or existing.period_label
            existing.remarks = remarks or existing.remarks
            existing.submitted_by = request.user
            existing.reviewed_by = None
            existing.reviewed_at = None
            existing.save()
            submission = existing
        else:
            submission = CounsellorHRSubmission.objects.create(
                counsellor=counsellor,
                start_date=start_date,
                end_date=end_date,
                period_label=period_label,
                remarks=remarks,
                submitted_by=request.user,
                status="submitted",
            )

        # Count admissions and registrations in this range for quick response feedback
        dt_start = make_aware(datetime.combine(start_date, time.min))
        dt_end = make_aware(datetime.combine(end_date, time.max))

        admissions_qs = Student.objects.filter(
            councellor=counsellor,
            created_at__gte=dt_start,
            created_at__lte=dt_end,
        ).prefetch_related("course_payments")
        admissions_count = admissions_qs.count()

        registrations_qs = InternshipApplication.objects.filter(
            councellor=counsellor,
            is_converted=False,
            created_at__gte=dt_start,
            created_at__lte=dt_end,
        )
        registrations_count = registrations_qs.count()

        total_payment = Decimal("0.00")
        for st in admissions_qs:
            payments = list(st.course_payments.all())
            if payments:
                sorted_payments = sorted(
                    payments,
                    key=lambda p: (p.payment_date or (p.created_at.date() if p.created_at else date.min))
                )
                first_pay = sorted_payments[0]
                pay_amt = getattr(first_pay, "amount_paid", None)
                if pay_amt is None:
                    pay_amt = getattr(first_pay, "amount", None)
                if pay_amt:
                    total_payment += Decimal(str(pay_amt))

        for app in registrations_qs:
            if app.slot_amount:
                total_payment += Decimal(str(app.slot_amount))

        summary = {
            "total_records": admissions_count + registrations_count,
            "new_admissions_count": admissions_count,
            "new_registrations_count": registrations_count,
            "total_students": admissions_count,
            "total_payment_collected": f"{total_payment:.2f}",
        }

        return Response({
            "message": "Conversions successfully submitted to HR.",
            "submission": CounsellorHRSubmissionSerializer(submission).data,
            "summary": summary,
            "total_records": summary["total_records"],
            "total_students": admissions_count,
        }, status=201)


class HRSubmissionsListAPIView(APIView):
    """
    GET: List all counsellor HR submissions. Supports filtering by status, counsellor_id, month, year, search, and date range.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = CounsellorHRSubmission.objects.select_related("counsellor", "submitted_by", "reviewed_by").all().order_by("-submitted_at")

        counsellor_id = request.query_params.get("counsellor_id")
        status_filter = request.query_params.get("status")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        search = request.query_params.get("search")

        if counsellor_id:
            queryset = queryset.filter(counsellor_id=counsellor_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if year:
            try:
                queryset = queryset.filter(start_date__year=int(year))
            except (ValueError, TypeError):
                pass
        if month:
            try:
                queryset = queryset.filter(start_date__month=int(month))
            except (ValueError, TypeError):
                pass

        if start_date:
            try:
                d = parse_date(start_date)
                if d:
                    queryset = queryset.filter(start_date__gte=d)
            except ValueError:
                return Response({"error": "Invalid start_date format."}, status=400)

        if end_date:
            try:
                d = parse_date(end_date)
                if d:
                    queryset = queryset.filter(end_date__lte=d)
            except ValueError:
                return Response({"error": "Invalid end_date format."}, status=400)

        if search:
            queryset = queryset.filter(
                Q(counsellor__first_name__icontains=search) |
                Q(counsellor__last_name__icontains=search) |
                Q(period_label__icontains=search) |
                Q(remarks__icontains=search)
            )

        serializer = CounsellorHRSubmissionSerializer(queryset, many=True)
        return Response(serializer.data)


class HRSubmissionDetailAPIView(APIView):
    """
    GET: Retrieve details of a specific submission, dynamically fetching the admissions and registrations in that date range.
    Supports filtering by ?type=all|admission|registration and ?course=<id>.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        submission = get_object_or_404(
            CounsellorHRSubmission.objects.select_related("counsellor", "submitted_by", "reviewed_by"),
            pk=pk
        )

        dt_start = make_aware(datetime.combine(submission.start_date, time.min))
        dt_end = make_aware(datetime.combine(submission.end_date, time.max))

        record_type = request.query_params.get("type", "all").lower()
        course_id = request.query_params.get("course") or request.query_params.get("course_id")

        # Admissions Query
        admissions_data = []
        if record_type in ["all", "admission"]:
            students = Student.objects.filter(
                councellor=submission.counsellor,
                created_at__gte=dt_start,
                created_at__lte=dt_end,
            ).select_related(
                "profile__user"
            ).prefetch_related(
                "enrollments__course",
                "course_payments"
            ).distinct().order_by("-created_at")

            if course_id:
                students = students.filter(enrollments__course_id=course_id)

            admissions_data = CounsellorConversionStudentSerializer(students, many=True).data

        # Registrations Query
        registrations_data = []
        if record_type in ["all", "registration"]:
            applications = InternshipApplication.objects.filter(
                councellor=submission.counsellor,
                is_converted=False,
                created_at__gte=dt_start,
                created_at__lte=dt_end,
            ).select_related("course").distinct().order_by("-created_at")

            if course_id:
                applications = applications.filter(course_id=course_id)

            registrations_data = CounsellorRegistrationApplicationSerializer(applications, many=True).data

        combined_records = sorted(
            admissions_data + registrations_data,
            key=lambda r: r.get("created_at") or "",
            reverse=True,
        )

        total_payments = Decimal("0.00")
        for rec in combined_records:
            p = rec.get("payment")
            if p and p.get("amount"):
                try:
                    total_payments += Decimal(str(p["amount"]))
                except Exception:
                    pass

        # Build counsellor & team leader info
        counsellor = submission.counsellor
        team_leader_data = None
        if hasattr(counsellor, "team_leader") and counsellor.team_leader:
            tl = counsellor.team_leader
            team_leader_data = {
                "id": tl.id,
                "name": tl.get_full_name(),
                "email": getattr(tl, "email", None),
                "phone": getattr(tl, "phone", None),
                "designation": getattr(tl, "designation", None),
            }

        counsellor_data = {
            "id": counsellor.id,
            "name": counsellor.get_full_name(),
            "email": getattr(counsellor, "email", None),
            "phone": getattr(counsellor, "phone", None),
            "designation": getattr(counsellor, "designation", None),
            "team_leader": team_leader_data,
        }

        return Response({
            "submission": CounsellorHRSubmissionSerializer(submission).data,
            "counsellor": counsellor_data,
            "summary": {
                "total_records": len(combined_records),
                "new_admissions_count": len(admissions_data),
                "new_registrations_count": len(registrations_data),
                "total_students": len(admissions_data),
                "total_payment_collected": f"{total_payments:.2f}",
            },
            "records": combined_records,
            "students": combined_records,
        })


class HRSubmissionActionAPIView(APIView):
    """
    POST: Approve or reject an HR submission.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        submission = get_object_or_404(CounsellorHRSubmission, pk=pk)
        action = request.data.get("action")
        remarks = request.data.get("remarks")

        if action not in ["approved", "rejected"]:
            return Response(
                {"detail": "Invalid action. Must be 'approved' or 'rejected'."},
                status=400,
            )

        if action == "rejected" and not remarks:
            return Response(
                {"detail": "Remarks are required when rejecting a submission so the counsellor knows what needs correction."},
                status=400,
            )

        submission.status = action
        submission.reviewed_by = request.user
        submission.reviewed_at = now()
        if remarks:
            submission.remarks = remarks
        submission.save()

        return Response({
            "message": f"Submission successfully {action}.",
            "submission": CounsellorHRSubmissionSerializer(submission).data,
        })


# ── Breakdown Standalone Report Views (Pure Lists, No Summary) ─

class AdmissionsReportListAPIView(APIView):
    """
    GET: List all New Admissions (Students).
    Returns a pure list [] by default.
    Activates pagination ({count, next, previous, results}) only if ?page= or ?page_size= is provided.
    Filters:
      - counsellor / counselor: Counsellor ID or 'all'
      - course: Course ID or 'all'
      - start_date / end_date: DD-MM-YYYY or YYYY-MM-DD
      - search: Search in student name, email, phone, or student_id
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Student.objects.select_related(
            "profile__user",
            "councellor",
        ).prefetch_related(
            "enrollments__course",
            "course_payments",
        )

        # Counsellor filter
        counsellor_param = request.query_params.get("counsellor") or request.query_params.get("counselor")
        if counsellor_param and counsellor_param.strip().lower() not in ["", "all"]:
            try:
                queryset = queryset.filter(councellor_id=int(counsellor_param))
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid counsellor filter '{counsellor_param}'."}, status=400)

        # Course filter
        course_param = request.query_params.get("course") or request.query_params.get("course_id")
        if course_param and course_param.strip().lower() not in ["", "all"]:
            try:
                queryset = queryset.filter(enrollments__course_id=int(course_param))
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid course filter '{course_param}'."}, status=400)

        # Date filters
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        d_start, d_end = None, None

        if start_date_str:
            try:
                d_start = parse_flexible_date(start_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if end_date_str:
            try:
                d_end = parse_flexible_date(end_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if d_start and d_end and d_start > d_end:
            return Response({"detail": "end_date must be greater than or equal to start_date."}, status=400)

        if d_start:
            dt_start = make_aware(datetime.combine(d_start, time.min))
            queryset = queryset.filter(created_at__gte=dt_start)
        if d_end:
            dt_end = make_aware(datetime.combine(d_end, time.max))
            queryset = queryset.filter(created_at__lte=dt_end)

        # Search filter
        search = request.query_params.get("search")
        if search and search.strip():
            s = search.strip()
            queryset = queryset.filter(
                Q(profile__user__first_name__icontains=s) |
                Q(profile__user__last_name__icontains=s) |
                Q(profile__user__email__icontains=s) |
                Q(profile__phone_number__icontains=s) |
                Q(student_id__icontains=s)
            )

        queryset = queryset.distinct().order_by("-created_at")

        # Conditional Pagination: activate ONLY if page or page_size is in query params
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        if page is not None or page_size is not None:
            from rest_framework.pagination import PageNumberPagination
            paginator = PageNumberPagination()
            if page_size:
                try:
                    paginator.page_size = int(page_size)
                except (ValueError, TypeError):
                    pass
            page_qs = paginator.paginate_queryset(queryset, request)
            serializer = AdmissionsBreakdownSerializer(page_qs, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Pure list by default
        serializer = AdmissionsBreakdownSerializer(queryset, many=True)
        return Response(serializer.data)


class RegistrationsReportListAPIView(APIView):
    """
    GET: List all New Registrations (Unconverted Applications).
    Returns a pure list [] by default.
    Activates pagination ({count, next, previous, results}) only if ?page= or ?page_size= is provided.
    Filters:
      - counsellor / counselor: Counsellor ID or 'all'
      - course: Course ID or 'all'
      - start_date / end_date: DD-MM-YYYY or YYYY-MM-DD
      - search: Search in first_name, last_name, email, primary_phone, secondary_phone
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = InternshipApplication.objects.filter(
            is_converted=False
        ).select_related(
            "course",
            "councellor",
        )

        # Counsellor filter
        counsellor_param = request.query_params.get("counsellor") or request.query_params.get("counselor")
        if counsellor_param and counsellor_param.strip().lower() not in ["", "all"]:
            try:
                queryset = queryset.filter(councellor_id=int(counsellor_param))
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid counsellor filter '{counsellor_param}'."}, status=400)

        # Course filter
        course_param = request.query_params.get("course") or request.query_params.get("course_id")
        if course_param and course_param.strip().lower() not in ["", "all"]:
            try:
                queryset = queryset.filter(course_id=int(course_param))
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid course filter '{course_param}'."}, status=400)

        # Date filters
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        d_start, d_end = None, None

        if start_date_str:
            try:
                d_start = parse_flexible_date(start_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if end_date_str:
            try:
                d_end = parse_flexible_date(end_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if d_start and d_end and d_start > d_end:
            return Response({"detail": "end_date must be greater than or equal to start_date."}, status=400)

        if d_start:
            dt_start = make_aware(datetime.combine(d_start, time.min))
            queryset = queryset.filter(created_at__gte=dt_start)
        if d_end:
            dt_end = make_aware(datetime.combine(d_end, time.max))
            queryset = queryset.filter(created_at__lte=dt_end)

        # Search filter
        search = request.query_params.get("search")
        if search and search.strip():
            s = search.strip()
            queryset = queryset.filter(
                Q(first_name__icontains=s) |
                Q(last_name__icontains=s) |
                Q(email__icontains=s) |
                Q(primary_phone__icontains=s) |
                Q(secondary_phone__icontains=s)
            )

        queryset = queryset.distinct().order_by("-created_at")

        # Conditional Pagination: activate ONLY if page or page_size is in query params
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        if page is not None or page_size is not None:
            from rest_framework.pagination import PageNumberPagination
            paginator = PageNumberPagination()
            if page_size:
                try:
                    paginator.page_size = int(page_size)
                except (ValueError, TypeError):
                    pass
            page_qs = paginator.paginate_queryset(queryset, request)
            serializer = RegistrationsBreakdownSerializer(page_qs, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Pure list by default
        serializer = RegistrationsBreakdownSerializer(queryset, many=True)
        return Response(serializer.data)


class PaymentsReportListAPIView(APIView):
    """
    GET: List all Payments (Course payments + Application slot payments).
    Returns a pure list [] by default.
    Activates pagination ({count, next, previous, results}) only if ?page= or ?page_size= is provided.
    Filters:
      - counsellor / counselor: Counsellor ID or 'all'
      - course: Course ID or 'all'
      - start_date / end_date: DD-MM-YYYY or YYYY-MM-DD
      - payment_type: 'slot', 'installment', 'advance', 'all'
      - search: Search in payer name, student_id, transaction_id, or email
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        counsellor_param = request.query_params.get("counsellor") or request.query_params.get("counselor")
        counsellor_id = None
        if counsellor_param and counsellor_param.strip().lower() not in ["", "all"]:
            try:
                counsellor_id = int(counsellor_param)
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid counsellor filter '{counsellor_param}'."}, status=400)

        course_param = request.query_params.get("course") or request.query_params.get("course_id")
        course_id = None
        if course_param and course_param.strip().lower() not in ["", "all"]:
            try:
                course_id = int(course_param)
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid course filter '{course_param}'."}, status=400)

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        d_start, d_end = None, None

        if start_date_str:
            try:
                d_start = parse_flexible_date(start_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if end_date_str:
            try:
                d_end = parse_flexible_date(end_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if d_start and d_end and d_start > d_end:
            return Response({"detail": "end_date must be greater than or equal to start_date."}, status=400)

        payment_type_filter = request.query_params.get("payment_type", "all").strip().lower()
        search = (request.query_params.get("search") or "").strip()

        combined_payments = []

        # ── 1. Course Payments (Admissions / Installments / Advances) ──
        if payment_type_filter in ["all", "installment", "advance", "admission"]:
            cp_qs = CoursePayment.objects.select_related(
                "student__profile__user",
                "student__councellor",
                "enrollment__course",
                "installments__enrollment__course",
            )

            if counsellor_id:
                cp_qs = cp_qs.filter(student__councellor_id=counsellor_id)

            if course_id:
                cp_qs = cp_qs.filter(
                    Q(enrollment__course_id=course_id) |
                    Q(installments__enrollment__course_id=course_id) |
                    Q(student__enrollments__course_id=course_id)
                )

            if d_start:
                cp_qs = cp_qs.filter(payment_date__gte=d_start)
            if d_end:
                cp_qs = cp_qs.filter(payment_date__lte=d_end)

            if payment_type_filter in ["installment", "advance"]:
                cp_qs = cp_qs.filter(payment_type=payment_type_filter)

            if search:
                cp_qs = cp_qs.filter(
                    Q(student__profile__user__first_name__icontains=search) |
                    Q(student__profile__user__last_name__icontains=search) |
                    Q(student__profile__user__email__icontains=search) |
                    Q(student__student_id__icontains=search) |
                    Q(transaction_id__icontains=search)
                )

            cp_qs = cp_qs.distinct()

            for cp in cp_qs:
                student = cp.student
                user = student.profile.user if student and student.profile else None
                counsellor = student.councellor if student else None

                # Resolve course title and id
                crs_title, crs_id = None, None
                if cp.enrollment and cp.enrollment.course:
                    crs_title = cp.enrollment.course.title
                    crs_id = cp.enrollment.course.id
                elif cp.installments and cp.installments.enrollment and cp.installments.enrollment.course:
                    crs_title = cp.installments.enrollment.course.title
                    crs_id = cp.installments.enrollment.course.id
                elif student:
                    enr = student.enrollments.first()
                    if enr and enr.course:
                        crs_title = enr.course.title
                        crs_id = enr.course.id

                # Identify if this was the first payment for the student
                category = "installment"
                if cp.payment_type == "advance":
                    category = "advance"
                else:
                    if student:
                        first_pay = min(
                            list(student.course_payments.all()),
                            key=lambda p: (p.payment_date or (p.created_at.date() if hasattr(p, "created_at") and p.created_at else date.min)),
                            default=None
                        )
                        if first_pay and first_pay.id == cp.id:
                            category = "admission_first_payment"

                combined_payments.append({
                    "id": f"CP-{cp.id}",
                    "payment_category": category,
                    "student_id": student.student_id if student else None,
                    "payer_name": student.get_full_name() if student else "",
                    "email": user.email if user else None,
                    "phone": student.profile.phone_number if student and student.profile else None,
                    "course": {"id": crs_id, "title": crs_title} if crs_title else None,
                    "counsellor": {"id": counsellor.id, "name": counsellor.get_full_name()} if counsellor else None,
                    "amount": f"{cp.amount_paid:.2f}",
                    "payment_method": cp.payment_method,
                    "transaction_id": cp.transaction_id,
                    "payment_date": str(cp.payment_date) if cp.payment_date else None,
                    "payment_type": cp.payment_type,
                })

        # ── 2. Application Slot Payments ──
        if payment_type_filter in ["all", "slot", "slot_amount"]:
            app_qs = InternshipApplication.objects.filter(
                slot_amount__isnull=False,
                slot_amount__gt=0,
            ).select_related("course", "councellor")

            if counsellor_id:
                app_qs = app_qs.filter(councellor_id=counsellor_id)

            if course_id:
                app_qs = app_qs.filter(course_id=course_id)

            if d_start:
                app_qs = app_qs.filter(
                    Q(slot_payment_date__gte=d_start) |
                    Q(slot_payment_date__isnull=True, created_at__date__gte=d_start)
                )
            if d_end:
                app_qs = app_qs.filter(
                    Q(slot_payment_date__lte=d_end) |
                    Q(slot_payment_date__isnull=True, created_at__date__lte=d_end)
                )

            if search:
                app_qs = app_qs.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(primary_phone__icontains=search) |
                    Q(slot_transaction_id__icontains=search)
                )

            app_qs = app_qs.distinct()

            for app in app_qs:
                p_date = app.slot_payment_date or (app.created_at.date() if app.created_at else None)
                crs_title = app.course.title if app.course else (app.course_name or None)
                crs_id = app.course.id if app.course else None

                combined_payments.append({
                    "id": f"SLOT-{app.id}",
                    "payment_category": "slot_amount",
                    "student_id": None,
                    "payer_name": f"{app.first_name} {app.last_name}".strip(),
                    "email": app.email,
                    "phone": app.primary_phone,
                    "course": {"id": crs_id, "title": crs_title} if crs_title else None,
                    "counsellor": {"id": app.councellor.id, "name": app.councellor.get_full_name()} if app.councellor else None,
                    "amount": f"{app.slot_amount:.2f}",
                    "payment_method": app.slot_payment_method,
                    "transaction_id": app.slot_transaction_id,
                    "payment_date": str(p_date) if p_date else None,
                    "payment_type": "slot_amount",
                })

        # Sort payments newest first
        combined_payments.sort(
            key=lambda p: p.get("payment_date") or "",
            reverse=True,
        )

        # Conditional Pagination: activate ONLY if page or page_size is in query params
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")
        if page is not None or page_size is not None:
            from rest_framework.pagination import PageNumberPagination
            paginator = PageNumberPagination()
            if page_size:
                try:
                    paginator.page_size = int(page_size)
                except (ValueError, TypeError):
                    pass
            page_items = paginator.paginate_queryset(combined_payments, request)
            serializer = PaymentsBreakdownSerializer(page_items, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Pure list by default
        serializer = PaymentsBreakdownSerializer(combined_payments, many=True)
        return Response(serializer.data)


# ── Admissions & Conversions Dashboard Summary API ────────────

class AdmissionsSummaryReportAPIView(APIView):
    """
    GET /internship/report/admissions/summary/
    Returns comprehensive KPI overview statistics for the Admissions/Conversions dashboard:
      - Total Registrations (with % change from previous month)
      - Total Admissions (with % intake conversion vs registrations)
      - Total Payments (successful transaction count)
      - Pending Payments (number of enrolled students with pending balance)
      - Total Amount Collected (advance + course fees + slot booking amounts)
      - Conversion Rate (% of registrations converted or admitted)
      - Today's Registrations (entries created today)
      - Today's Admissions (students admitted today)
    Supports filters:
      - counsellor / counselor
      - course
      - start_date / end_date (supports DD-MM-YYYY or YYYY-MM-DD)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now().date()
        dt_today_start = make_aware(datetime.combine(today, time.min))
        dt_today_end = make_aware(datetime.combine(today, time.max))

        # Filter parameters
        counsellor_param = request.query_params.get("counsellor") or request.query_params.get("counselor")
        counsellor_id = None
        if counsellor_param and counsellor_param.strip().lower() not in ["", "all"]:
            try:
                counsellor_id = int(counsellor_param)
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid counsellor filter '{counsellor_param}'."}, status=400)

        course_param = request.query_params.get("course") or request.query_params.get("course_id")
        course_id = None
        if course_param and course_param.strip().lower() not in ["", "all"]:
            try:
                course_id = int(course_param)
            except (ValueError, TypeError):
                return Response({"detail": f"Invalid course filter '{course_param}'."}, status=400)

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        d_start, d_end = None, None

        if start_date_str:
            try:
                d_start = parse_flexible_date(start_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if end_date_str:
            try:
                d_end = parse_flexible_date(end_date_str)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)

        if d_start and d_end and d_start > d_end:
            return Response({"detail": "end_date must be greater than or equal to start_date."}, status=400)

        dt_start = make_aware(datetime.combine(d_start, time.min)) if d_start else None
        dt_end = make_aware(datetime.combine(d_end, time.max)) if d_end else None

        # Base querysets
        admissions_qs = Student.objects.all()
        registrations_qs = InternshipApplication.objects.all()
        course_payments_qs = CoursePayment.objects.all()
        slot_payments_qs = InternshipApplication.objects.filter(slot_amount__isnull=False, slot_amount__gt=0)

        # Apply counsellor filter
        if counsellor_id:
            admissions_qs = admissions_qs.filter(councellor_id=counsellor_id)
            registrations_qs = registrations_qs.filter(councellor_id=counsellor_id)
            course_payments_qs = course_payments_qs.filter(student__councellor_id=counsellor_id)
            slot_payments_qs = slot_payments_qs.filter(councellor_id=counsellor_id)

        # Apply course filter
        if course_id:
            admissions_qs = admissions_qs.filter(enrollments__course_id=course_id)
            registrations_qs = registrations_qs.filter(course_id=course_id)
            course_payments_qs = course_payments_qs.filter(
                Q(enrollment__course_id=course_id) |
                Q(installments__enrollment__course_id=course_id) |
                Q(student__enrollments__course_id=course_id)
            )
            slot_payments_qs = slot_payments_qs.filter(course_id=course_id)

        # Range-filtered querysets
        admissions_filtered = admissions_qs
        registrations_filtered = registrations_qs
        course_payments_filtered = course_payments_qs
        slot_payments_filtered = slot_payments_qs

        if dt_start:
            admissions_filtered = admissions_filtered.filter(created_at__gte=dt_start)
            registrations_filtered = registrations_filtered.filter(created_at__gte=dt_start)
            course_payments_filtered = course_payments_filtered.filter(payment_date__gte=d_start)
            slot_payments_filtered = slot_payments_filtered.filter(
                Q(slot_payment_date__gte=d_start) |
                Q(slot_payment_date__isnull=True, created_at__date__gte=d_start)
            )

        if dt_end:
            admissions_filtered = admissions_filtered.filter(created_at__lte=dt_end)
            registrations_filtered = registrations_filtered.filter(created_at__lte=dt_end)
            course_payments_filtered = course_payments_filtered.filter(payment_date__lte=d_end)
            slot_payments_filtered = slot_payments_filtered.filter(
                Q(slot_payment_date__lte=d_end) |
                Q(slot_payment_date__isnull=True, created_at__date__lte=d_end)
            )

        # Distinct counts
        total_admissions = admissions_filtered.distinct().count()
        total_registrations = registrations_filtered.distinct().count()

        # Payments calculations
        course_pay_count = course_payments_filtered.distinct().count()
        slot_pay_count = slot_payments_filtered.distinct().count()
        total_payments = course_pay_count + slot_pay_count

        course_amount_sum = course_payments_filtered.distinct().aggregate(t=Sum("amount_paid"))["t"] or Decimal("0.00")
        slot_amount_sum = slot_payments_filtered.distinct().aggregate(t=Sum("slot_amount"))["t"] or Decimal("0.00")
        total_amount_collected = Decimal(str(course_amount_sum)) + Decimal(str(slot_amount_sum))

        # Today's counts
        today_registrations = registrations_qs.filter(
            created_at__gte=dt_today_start,
            created_at__lte=dt_today_end,
        ).distinct().count()

        today_admissions = admissions_qs.filter(
            created_at__gte=dt_today_start,
            created_at__lte=dt_today_end,
        ).distinct().count()

        # Month-over-month calculation for Registrations
        # Current month: 1st of this month to today
        curr_month_start = make_aware(datetime(today.year, today.month, 1, 0, 0))
        # Previous month: 1st of last month to same relative days
        if today.month == 1:
            prev_month_start = make_aware(datetime(today.year - 1, 12, 1, 0, 0))
            prev_month_end = make_aware(datetime(today.year - 1, 12, min(today.day, 31), 23, 59, 59))
        else:
            prev_month_start = make_aware(datetime(today.year, today.month - 1, 1, 0, 0))
            # Handle shorter month length (e.g. Feb)
            import calendar
            max_days_prev = calendar.monthrange(today.year, today.month - 1)[1]
            prev_month_end = make_aware(datetime(today.year, today.month - 1, min(today.day, max_days_prev), 23, 59, 59))

        curr_month_reg = registrations_qs.filter(created_at__gte=curr_month_start, created_at__lte=dt_today_end).distinct().count()
        prev_month_reg = registrations_qs.filter(created_at__gte=prev_month_start, created_at__lte=prev_month_end).distinct().count()

        if prev_month_reg > 0:
            reg_pct_change = round(((curr_month_reg - prev_month_reg) / prev_month_reg) * 100, 1)
            reg_growth_str = f"{'+' if reg_pct_change >= 0 else ''}{reg_pct_change}% from last month"
        elif curr_month_reg > 0:
            reg_growth_str = "+100% from last month"
        else:
            reg_growth_str = "0% from last month"

        # Conversion Rate
        if total_registrations > 0:
            conversion_rate_val = round((total_admissions / total_registrations) * 100, 1)
        else:
            conversion_rate_val = 0.0

        intake_conversion_str = f"{conversion_rate_val}% intake conversion"

        # Pending Payments count: Students in this scope who still have pending course fees
        pending_payments_count = 0
        students_in_scope = admissions_filtered.prefetch_related(
            "enrollments__course",
            "enrollments__student_installment_items",
            "course_payments",
        ).distinct()

        for student in students_in_scope:
            enrollment = student.enrollments.first()
            if enrollment:
                if enrollment.pending_balance > Decimal("0.00"):
                    pending_payments_count += 1
            else:
                # Student with no enrollment record or fee not fully paid
                payments_sum = sum((p.amount_paid for p in student.course_payments.all()), Decimal("0.00"))
                if payments_sum == Decimal("0.00"):
                    pending_payments_count += 1

        return Response({
            "total_registrations": {
                "value": total_registrations,
                "label": "Total Registrations",
                "subtext": reg_growth_str,
            },
            "total_admissions": {
                "value": total_admissions,
                "label": "Total Admissions",
                "subtext": intake_conversion_str,
            },
            "total_payments": {
                "value": total_payments,
                "label": "Total Payments",
                "subtext": "Successful transactions",
            },
            "pending_payments": {
                "value": pending_payments_count,
                "label": "Pending Payments",
                "subtext": "Pending fee clearance",
            },
            "total_amount_collected": {
                "value": f"{total_amount_collected:.2f}",
                "formatted": f"₹{total_amount_collected:,.2f}",
                "label": "Total Amount Collected",
                "subtext": "Advance & course fees",
            },
            "conversion_rate": {
                "value": conversion_rate_val,
                "formatted": f"{conversion_rate_val}%",
                "label": "Conversion Rate",
                "subtext": "Target ratio achieved" if conversion_rate_val >= 50 else "In progress",
            },
            "today_registrations": {
                "value": today_registrations,
                "label": "Today's Registrations",
                "subtext": "New lead entries",
            },
            "today_admissions": {
                "value": today_admissions,
                "label": "Today's Admissions",
                "subtext": "Enrolled students",
            },
            # Raw summary object for direct programmatic access
            "summary": {
                "total_registrations": total_registrations,
                "registrations_growth": reg_growth_str,
                "total_admissions": total_admissions,
                "admissions_intake_conversion": intake_conversion_str,
                "total_payments": total_payments,
                "pending_payments": pending_payments_count,
                "total_amount_collected": f"{total_amount_collected:.2f}",
                "conversion_rate": conversion_rate_val,
                "today_registrations": today_registrations,
                "today_admissions": today_admissions,
            }
        })



