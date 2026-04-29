from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Prefetch, Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from datetime import datetime
from django.db.models.functions import TruncMonth
from ..models import Section, Class, Student, Course, Faculty, StudentCourseEnrollment, CoursePayment
from ..serializers.internship_admin import SectionSerializer, ClassListCreateSerializer, StudentPaymentDetailSerializer, StudentPaymentSerializer

from accounts.models import CustomUser
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
        students_count=Count('students', distinct=True)
    ).order_by('-created_at')

    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]

    filterset_fields = {
        "department": ["exact"],
        "is_active": ["exact"],
        "students": ["exact"],
        "batches__faculties": ["exact"],
    }

    search_fields = ['title', 'description', 'department__name']

class CourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.select_related(
        "department",
        "tax_settings",
    ).prefetch_related(
        "batches__faculties__user__user",
        "installment_plans__items"
    ).annotate(
        students_count=Count('students', distinct=True)
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
        "user__user",
        "department",
    ).annotate(
        course_count=Count("batches__course", distinct=True),
        students_count=Count("batches__students", distinct=True),
    ).order_by("id")


#Faculty
class FacultyListCreateAPIView(FacultyQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = {
        "department": ["exact"],
        "batches__course": ["exact"],
        "batches": ["exact"],
        "is_active": ["exact"],
    }
    search_fields = [
        "user__user__first_name",
        "user__user__last_name",
        "department__name",
    ]


class FacultyRetrieveUpdateDestroyAPIView(
    FacultyQuerysetMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]

#Batch
class BatchNumberPreviewAPIView(APIView):
    def get(self, request):
        course_id = request.query_params.get("course")

        if not course_id:
            return Response({"error": "course required"}, status=400)

        course = get_object_or_404(Course, id=course_id)

        prefix = get_clean_prefix(course.title)

        batch_number = generate_batch_number(
            model=Batch,
            field_name="batch_number",
            prefix=prefix,
            length=3,
            course=course
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
        "is_active": ["exact"],
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

class StudentCourseEnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudentCourseEnrollment.objects.select_related("student", "batch", "installment_plan").all()
    serializer_class = StudentCourseEnrollmentSerializer
    permission_classes = [IsAuthenticated]

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
        "installments__plan",
        "installments__plan__course"
    )
    serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    


class StudentPaymentListAPIView(generics.ListAPIView):
    serializer_class = StudentPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Student.objects.select_related(
            "profile__user"
        ).prefetch_related(
            Prefetch(
                "enrollments",
                queryset=StudentCourseEnrollment.objects.select_related(
                    "course",
                    "batch",
                    "installment_plan",
                )
            ),
            "course_payments__installments__plan",
        ).filter(
            enrollments__isnull=False
        ).distinct()


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
                "student__course_payments__installments",
            ),
            student_id=pk,
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
        "installments__plan",
        "installments__plan__course"
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
    serializer_class   = ClassListCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Class.objects.select_related("center").prefetch_related(
            "sections__days", "sections__batch"
        )

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
        active_students = Student.objects.filter(is_active=True).count()
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
                "status": "Active" if s.is_active else "Inactive"
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