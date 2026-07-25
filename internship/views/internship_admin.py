from decimal import Decimal
from django.db.migrations import serializer
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Prefetch, Sum, DecimalField, Value, ExpressionWrapper
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from datetime import datetime
from django.db.models.functions import TruncMonth

from accounts.services.receipt_service import StudentReceiptService
from internship.serializers.instructor import StudentReportSerializer
from ..models import Section, Class, Student, Course, Faculty, StudentCourseEnrollment, CoursePayment, StudentReport
from ..serializers.internship_admin import AvailableFacultySerializer, AvailableStudentSerializer, BatchInformationSerializer, ClassDetailSerializer, SectionSerializer, ClassListCreateSerializer, StudentPaymentDetailSerializer, StudentPaymentSerializer, StudentProfileDetailSerializer

from accounts.models import CustomUser, StaffProfile
from internship.utils import (
    get_installment_due_date_for_staff,
    get_next_unpaid_installment_item,
    get_staff_installment_plan,
)
from ..models import (
    Batch,
    Center,
    Course,
    CoursePayment,
    Faculty,
    InstallmentPlan,
    Student,
    StudentCourseEnrollment,
)
from ..serializers.internship_admin import (
    BatchSerializer,
    CenterSerializer,
    CoursePaymentSerializer,
    CourseSerializer,
    FacultySerializer,
    InstallmentPlanSerializer,
    InstallmentPlanUpdateSerializer,
    StudentCourseEnrollmentSerializer,
    StudentSerializer,
)
from ..utils import generate_batch_number, get_clean_prefix


# ===== Course Views ======
class CourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = Course.objects.select_related(
        "department",
        "tax_settings",
    ).prefetch_related(
        "batches__faculties__user__user",
        "installment_plans__items",
    ).annotate(
        students_count=Count("enrollments__student", distinct=True)
    ).order_by('-created_at')

    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]

    filterset_fields = {
        "department": ["exact"],
        "is_active": ["exact"],
        "enrollments__student": ["exact"],
        "batches__faculties": ["exact"],
    }

    search_fields = ['title', 'description', 'department__name']

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        student_id = self.request.query_params.get("students")
        if student_id:
            queryset = queryset.filter(enrollments__student_id=student_id)
        return queryset.distinct()

class CourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.select_related(
        "department",
        "tax_settings",
    ).prefetch_related(
        "batches__faculties__user__user",
        "installment_plans__items"
    ).annotate(
        students_count=Count("enrollments__student", distinct=True)
    )

    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    
class InstallmentPlanUpdateAPIView(generics.UpdateAPIView):
    queryset = InstallmentPlan.objects.prefetch_related("items")
    serializer_class = InstallmentPlanUpdateSerializer
    permission_classes = [IsAuthenticated]

class InstallmentListAPIView(generics.ListAPIView):
    queryset = InstallmentPlan.objects.prefetch_related("items").all()
    serializer_class = InstallmentPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["course"]


class InstallmentSelectionListAPIView(generics.ListAPIView):
    serializer_class = InstallmentPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        return InstallmentPlan.objects.filter(
            course_id=course_id,
            is_active=True
        ).prefetch_related("items").order_by("total_installments")

class FacultyQuerysetMixin:
    queryset = Faculty.objects.select_related(
        "user__user"
    ).prefetch_related(
        "departments",
    ).annotate(
        course_count=Count("batches__course", distinct=True),
        students_count=Count("batches__enrollments__student", distinct=True),
    ).order_by("id")


#Faculty
class FacultyListCreateAPIView(FacultyQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = {
        "departments": ["exact"],
        "batches__course": ["exact"],
        "batches": ["exact"],
        "is_active": ["exact"],
    }
    search_fields = [
        "user__user__first_name",
        "user__user__last_name",
        "departments__name",
    ]

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).distinct()


class FacultyRetrieveUpdateDestroyAPIView(
    FacultyQuerysetMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]

#Batch
# Preview view
class BatchNumberPreviewAPIView(APIView):
    def get(self, request):


        batch_number = generate_batch_number(
            model=Batch,
            field_name="batch_number",
            prefix="BAT",
            length=4,
            use_lock=False
        )

        return Response({"batch_number": batch_number})
    
class BatchListCreateAPIView(generics.ListCreateAPIView):
    queryset         = Batch.objects.select_related("course").prefetch_related("faculties__user__user")
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends  = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['course', 'faculties']
    search_fields    = [
        'batch_number',
        'course__title',
        'faculties__user__user__first_name',
        'faculties__user__user__last_name',
    ]

class BatchRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset         = Batch.objects.select_related("course").prefetch_related("faculties__user__user")
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]

class StudentListCreateAPIView(generics.ListCreateAPIView):

    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    filter_backends = [SearchFilter, DjangoFilterBackend]

    search_fields = [
        "student_id",
        "profile__user__first_name",
        "profile__user__last_name",
        "profile__user__email"
    ]

    filterset_fields = {
        "center": ["exact"],
        "status": ["exact"],
    }

    def get_queryset(self):

        qs = Student.objects.select_related(
            "profile__user",
            "center",
            "councellor"
        ).prefetch_related(
            Prefetch(
                "enrollments",
                queryset=StudentCourseEnrollment.objects.select_related(
                    "course",
                    "batch",
                    "installment_plan"
                )
            )
        ).distinct()

        course = self.request.query_params.get("course")
        batch = self.request.query_params.get("batch")

        if course:
            qs = qs.filter(
                enrollments__course_id=course
            )

        if batch:
            qs = qs.filter(
                enrollments__batch_id=batch
            )

        return qs.distinct()

class StudentCredentialsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            student = Student.objects.select_related("profile__user").get(pk=pk)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        user = student.profile.user

        return Response({
            "student_id": student.id,
            "email": user.email,
            "password": "********"  # Do not return the actual password
        }, status=200)

    def patch(self, request, pk):
        try:
            student = Student.objects.select_related("profile__user").get(pk=pk)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        user = student.profile.user

        email = request.data.get("email")
        password = request.data.get("password")
        confirm_password = request.data.get("confirm_password")

        updated_fields = []

        with transaction.atomic():

            # Email Update
            if email:
                if CustomUser.objects.filter(email=email).exclude(id=user.id).exists():
                    return Response(
                        {"error": "Email already exists"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.email = email
                updated_fields.append("email")

            # Password Update
            if password:
                if password != confirm_password:
                    return Response(
                        {"error": "Passwords do not match"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.set_password(password)
                updated_fields.append("password")

            user.save()

        return Response({
            "message": "Student credentials updated successfully",
            "updated_fields": updated_fields
        }, status=200)

class StudentRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.select_related(
        "profile__user",
        "center",
        "councellor"
    ).prefetch_related(
        Prefetch(
            "enrollments",
            queryset=StudentCourseEnrollment.objects.select_related(
                "course",
                "batch",
                "installment_plan"
            )
        )
    )
    def perform_destroy(self, instance):

        # Do not allow deletion if any payment exists
        if instance.course_payments.exists():
            raise ValidationError({
                "detail": "Cannot delete this student because payment records exist."
            })

        with transaction.atomic():
            # Delete all enrollments (this also deletes StudentInstallmentItem
            # because StudentInstallmentItem.enrollment uses CASCADE)
            instance.enrollments.all().delete()

            # Finally delete the student
            instance.delete()    

    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "id"


class StudentCourseEnrollmentView(generics.ListCreateAPIView):
    queryset = StudentCourseEnrollment.objects.select_related("student", "batch", "installment_plan").all()
    serializer_class = StudentCourseEnrollmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["course", "batch"]

    def perform_create(self, serializer):
        enrollment = serializer.save()

        receipt_data = serializer.validated_data.pop("receipt", None)

        if receipt_data:

            advance_payment = CoursePayment.objects.filter(
                enrollment=enrollment,
                payment_type="advance"
            ).first()

            if advance_payment:
                StudentReceiptService.create_receipt(
                    enrollment=enrollment,
                    payment=advance_payment,
                    receipt_data=receipt_data,
                    user=self.request.user,
                )



class StudentCourseEnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudentCourseEnrollment.objects.select_related("student", "batch", "installment_plan").all()
    serializer_class = StudentCourseEnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):

        # Advance payments
        has_advance_payments = instance.payments.exists()

        # Installment payments
        has_installment_payments = CoursePayment.objects.filter(
            installments__enrollment=instance
        ).exists()

        if has_advance_payments or has_installment_payments:
            raise ValidationError({
                "detail": "Cannot delete this enrollment because payment records exist."
            })

        with transaction.atomic():
            instance.delete()

class CenterListCreateAPIView(generics.ListCreateAPIView):
    queryset = Center.objects.all()
    serializer_class = CenterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name", "address", "state_name", "country_name"]


class CenterRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Center.objects.all()
    serializer_class = CenterSerializer
    permission_classes = [IsAuthenticated]


class CoursePaymentListCreateAPIView(generics.ListCreateAPIView):
    queryset = CoursePayment.objects.select_related(
        "student",
        "student__profile",
        "student__profile__user",
        "installments",
        "installments__enrollment",
        "installments__enrollment__course"
    )
    serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    

# aadyam student nn aayirunnu one student one course validastion maattiyappo ee api erro vaann appo student course enrollment nn edduth data 
class StudentPaymentListAPIView(generics.ListAPIView):
    serializer_class = StudentPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            StudentCourseEnrollment.objects.select_related(
                "student__profile__user",
                "course",
                "installment_plan",
            )
            .prefetch_related(
                "student_installment_items",
                "payments",
            )
            .order_by("-id")
        )


class StudentPaymentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        enrollment = get_object_or_404(
            StudentCourseEnrollment.objects.select_related(
                "student__profile__user",
                "course",
                "installment_plan",
            ).prefetch_related(
                "installment_plan__items",
                "student_installment_items",
                "student__course_payments__installments",
            ),
            pk=pk,
        )
        serializer = StudentPaymentDetailSerializer(enrollment)
        return Response(serializer.data)

class CoursePaymentDestroyAPIView(generics.DestroyAPIView):
    queryset = CoursePayment.objects.all()
    serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    

class CoursePaymentRetrieveAPIView(generics.RetrieveAPIView):
    queryset = CoursePayment.objects.select_related(
        "student",
        "student__profile",
        "student__profile__user",
        "installments",
        "installments__enrollment",
        "installments__enrollment__course"
    )
    serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    



class ClassListCreateAPIView(generics.ListCreateAPIView):
    serializer_class   = ClassListCreateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter]
    filterset_fields   = ["center", "is_active"]
    search_fields      = ["name"]

    def get_queryset(self):
        return Class.objects.select_related("center").prefetch_related(
            "sections__days", "sections__batch"
        ).filter(is_active=True)

class ClassRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = ClassDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Class.objects.select_related("center").prefetch_related(
            "sections__days", "sections__batch__course"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # request serializer-ലേക്ക് pass ചെയ്യുന്നു
        return context
    
class SectionListCreateAPIView(generics.ListCreateAPIView):
    serializer_class   = SectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ["class_obj", "batch", "batch__course"]

    def get_queryset(self):
        today = timezone.now().date()
        qs = Section.objects.select_related(
            "class_obj", "batch", "batch__course"
        ).prefetch_related("days").filter(
            batch__is_active=True,        # active batch only
            batch__end_date__gte=today,   # non-expired only
        )
        day = self.request.query_params.get("day")
        if day:
            qs = qs.filter(days__day=day)
        return qs

class SectionRetrieveUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = SectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Section.objects.select_related(
            "class_obj", "batch", "batch__course"
        ).prefetch_related("days")


class AcademicDashboardAPIView(APIView):

    def get(self, request):
        year = int(request.GET.get("year", datetime.now().year))

        # status
        active_students = Student.objects.filter(status='active').count()
        active_courses = Course.objects.filter(is_active=True).count()
        faculty_count = Faculty.objects.filter(is_active=True).count()

        # Pending payments
        paid_students = CoursePayment.objects.values("student").distinct().count()
        total_students = Student.objects.count()
        pending_payments = total_students - paid_students

        stats = {
            "active_students": active_students,
            "active_courses": active_courses,
            "faculty_count": faculty_count,
            "pending_payments": pending_payments,
        }

        # revenue chart
        revenue_data = (
            CoursePayment.objects
            .filter(payment_date__year=year)
            .annotate(month=TruncMonth("payment_date"))
            .values("month")
            .annotate(total=Sum("amount_paid"))
            .order_by("month")
        )

        revenue_chart = [
            {
                "month": item["month"].strftime("%b"),
                "amount": item["total"]
            }
            for item in revenue_data
        ]

        # enrollmetn chart
        enrollment_data = (
            StudentCourseEnrollment.objects
            .values("course__title")
            .annotate(count=Count("id"))
            .order_by("-count")[:6]
        )

        enrollment_chart = [
            {
                "course": item["course__title"],
                "students": item["count"]
            }
            for item in enrollment_data
        ]

        # recent intern
        recent_students = Student.objects.select_related(
            "profile__user"
        ).prefetch_related(
            "enrollments__course"
        ).order_by("-created_at")[:5]

        recent_interns = []

        for s in recent_students:
            enrollment = s.enrollments.select_related("course").first()

            recent_interns.append({
                "name": s.get_full_name(),
                "course": enrollment.course.title if enrollment and enrollment.course else None,
                "status": s.get_status_display()
            })

        # top faculty
        faculty_data = (
            Faculty.objects.annotate(
                student_count=Count(
                    "batches__enrollments__student",
                    distinct=True
                )
            )
            .order_by("-student_count")[:5]
        )

        top_faculty = [
            {
                "name": f.get_full_name(),
                "students": f.student_count
            }
            for f in faculty_data
        ]

        return Response({
            "stats": stats,
            "charts": {
                "revenue": revenue_chart,
                "enrollments": enrollment_chart
            },
            "recent_interns": recent_interns,
            "top_faculty": top_faculty
        })
    



class AvailableStudentsView(APIView):

    def get(self, request):
        center_id = request.query_params.get('center_id')

        already_enrolled_ids = StudentCourseEnrollment.objects.values_list(
            'student_id', flat=True
        ).distinct()

        qs = Student.objects.filter(
            status='active'
        ).exclude(
            id__in=already_enrolled_ids
        ).select_related(
            'profile__user',
            'center'
        ).order_by('profile__user__first_name')

        if center_id:
            qs = qs.filter(center_id=center_id)

        serializer = AvailableStudentSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# admin side report view , 
class AdminStudentReportListAPIView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]

    serializer_class = StudentReportSerializer

    def get_queryset(self):

        qs = (
            StudentReport.objects
            .select_related(
                'student',
                'batch',
                'template',
                'faculty'
            )
            .prefetch_related(
                'field_values__field'
            )
            .order_by('-submitted_at')
        )

        student = self.request.query_params.get('student')
        batch = self.request.query_params.get('batch')
        faculty = self.request.query_params.get('faculty')

        if student:
            qs = qs.filter(student_id=student)

        if batch:
            qs = qs.filter(batch_id=batch)

        if faculty:
            qs = qs.filter(faculty_id=faculty)

        return qs
    
class AdminStudentReportDetailAPIView(generics.RetrieveAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = StudentReportSerializer

    queryset = (
        StudentReport.objects
        .select_related(
            'student',
            'batch',
            'template',
            'faculty'
        )
        .prefetch_related(
            'field_values__field'
        )
    )

#get count of total students, active and inaactive for admin view
class StudentCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_students = Student.objects.count()
        active_students = Student.objects.filter(status='active').count()
        inactive_students = Student.objects.filter(status='inactive').count()

        return Response({
            'total_students': total_students,
            'active_students': active_students,
            'inactive_students': inactive_students
        })


class AvailableFacultyListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AvailableFacultySerializer

    def get_queryset(self):

        queryset = (
            StaffProfile.objects
            .select_related("user", "job_detail")
            .filter(
                faculty_profile__isnull=True,
                job_detail__job_type="full_day", # staff prifile e ulla  job type full day aayittulla users ne maathram drop down cheyyaan
                job_detail__status__in=["active", "probation"] 
            )
        )

        search = self.request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(staff_email__icontains=search)
            )

        return queryset

# student detail profile viewfor admin
class StudentProfileDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        student = get_object_or_404(
            Student.objects.select_related(
                "profile__user",
                "center",
                "councellor",
            ).prefetch_related(
                "enrollments__course",
                "enrollments__batch__faculties__user__user",
                "enrollments__payments",
            ),
            pk=pk,
        )

        serializer = StudentProfileDetailSerializer(student)

        return Response(serializer.data)


class BatchInformationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        batch_id = request.query_params.get("batch")

        if not batch_id:
            return Response(
                {
                    "detail": "batch query parameter is required."
                },
                status=400,
            )

        batch = get_object_or_404(
            Batch.objects.select_related("course"),
            pk=batch_id,
        )

        serializer = BatchInformationSerializer(batch)

        return Response(serializer.data)


from datetime import timedelta

from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter

from internship.models import StudentCourseEnrollment
from internship.serializers.internship_admin import PaymentReportSerializer


class PaymentReportListAPIView(generics.ListAPIView):
    serializer_class = PaymentReportSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "student__profile__user__first_name",
        "student__profile__user__last_name",
        "student__student_id",
        "student__profile__phone_number",
        "student__profile__user__email",
        "course__title",
    ]

    ordering_fields = [
        "enrollment_date",
        "course__title",
        "student__student_id",
        "course__total_fee",
    ]

    ordering = [
        "-enrollment_date"
    ]

    def get_queryset(self):

        queryset = (
            StudentCourseEnrollment.objects
            .select_related(
                "student",
                "student__profile",
                "student__profile__user",
                "course",
                "batch",
                "installment_plan",
            )
            .prefetch_related(
                "payments",
                "student_installment_items",
            )
            .annotate(
                total_paid=Coalesce(
                    Sum("payments__amount_paid"),
                    Value(0),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ),
                discounted_fee=ExpressionWrapper(
                    F("course__total_fee") - F("discount_amount"),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
        )

        params = self.request.query_params

        # Student
        student = params.get("student")

        if student:
            queryset = queryset.filter(
                student_id=student
            )

        # Course
        course = params.get("course")

        if course:
            queryset = queryset.filter(
                course_id=course
            )

        # Batch
        batch = params.get("batch")

        if batch:
            queryset = queryset.filter(
                batch_id=batch
            )

        # Default / Custom
        payment_plan_type = params.get(
            "payment_plan_type"
        )

        if payment_plan_type:

            queryset = queryset.filter(
                payment_plan_type=payment_plan_type
            )

        # Installment Count
        installments = params.get(
            "installments"
        )

        if installments:

            queryset = queryset.filter(

                Q(
                    payment_plan_type="default_installment",
                    installment_plan__total_installments=installments,
                )

                |

                Q(
                    payment_plan_type="custom_installment",
                    custom_installments=installments,
                )

            )

        # Advance

        advance = params.get("advance")

        if advance == "yes":

            queryset = queryset.filter(
                advance_amount__gt=0
            )

        elif advance == "no":

            queryset = queryset.filter(
                advance_amount=0
            )

        # Payment Method
        payment_method = params.get(
            "payment_method"
        )

        if payment_method:

            queryset = queryset.filter(
                payments__payment_method=payment_method
            ).distinct()

        # Enrollment Date
        enrolled_from = params.get(
            "enrolled_from"
        )

        if enrolled_from:

            queryset = queryset.filter(
                enrollment_date__gte=enrolled_from
            )

        enrolled_to = params.get(
            "enrolled_to"
        )

        if enrolled_to:

            queryset = queryset.filter(
                enrollment_date__lte=enrolled_to
            )

        # Payment Status
        status = params.get("status")

        if status == "pending":

            queryset = queryset.filter(
                total_paid=0
            )

        elif status == "partial":

            queryset = queryset.filter(
                total_paid__gt=0,
                total_paid__lt=F("discounted_fee")
            )

        elif status == "paid":

            queryset = queryset.filter(
                total_paid__gte=F("discounted_fee")
            )

        # Due Filter
        due = params.get("due")

        today = timezone.now().date()

        if due == "today":

            queryset = queryset.filter(
                enrollment_date=today
            )

        elif due == "this_week":

            queryset = queryset.filter(
                enrollment_date__range=[
                    today,
                    today + timedelta(days=7)
                ]
            )

        elif due == "this_month":

            queryset = queryset.filter(
                enrollment_date__month=today.month,
                enrollment_date__year=today.year,
            )

        return queryset.distinct()