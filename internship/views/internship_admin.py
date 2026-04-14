from rest_framework import generics,filters
from ..models import *
from ..serializers.internship_admin import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from decimal import Decimal




# ===== Course Views ======
class CourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = Course.objects.select_related(
        "department"
    ).prefetch_related(
        "installment_plans__items"
    ).order_by('-created_at')

    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = {
        "department": ["exact"],
        "is_active": ["exact"],
        "students": ["exact"],
        "batches__faculty": ["exact"],
    }
                        
    search_fields = ['title', 'description', 'department__name']


class CourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.select_related(
        "department"
    ).prefetch_related(
        "installment_plans__items"
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

#Faculty
class FacultyListCreateAPIView(generics.ListCreateAPIView):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]

class CourseFacultyListCreateAPIView(generics.ListCreateAPIView):
    queryset = CourseFaculty.objects.select_related(
        "faculty", "department"
    ).annotate(
        course_count=Count("faculty__course_faculties", distinct=True),
        students_count=Count("batches__students", distinct=True)
    )

    serializer_class = CourseFacultySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = {
            "department": ["exact"],
            "batches__course": ["exact"],
            "batches": ["exact"],
        }
    search_fields = [
    "faculty__user__user__first_name",
    "faculty__user__user__last_name",
    "department__name"
        ]
class CourseFacultyRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CourseFaculty.objects.select_related(
        "faculty", "department"
    ).annotate(
        course_count=Count("faculty__course_faculties", distinct=True),
        students_count=Count("batches__students", distinct=True)
    )
    serializer_class = CourseFacultySerializer
    permission_classes = [IsAuthenticated]

#Batch
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime
from django.shortcuts import get_object_or_404

from ..models import Batch, Course
from ..utils import generate_batch_number, get_clean_prefix


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
    queryset = Batch.objects.select_related("course", "faculty").all()
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['course', 'faculty']
    search_fields = [
        'batch_number',
        'course__title',
        'faculty__faculty__user__user__first_name',
        'faculty__faculty__user__user__last_name'
    ]

class BatchRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Batch.objects.select_related("course", "faculty").all()
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]


class StudentListCreateAPIView(generics.ListCreateAPIView):
    queryset = Student.objects.select_related(
        "profile__user",
        "course",
        "batch",
        "payment_type",
        "councellor"
    ).all()

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
        "course": ["exact"],
        "batch": ["exact"],
        "center": ["exact"],
        "is_active": ["exact"],
        "batch__faculty": ["exact"],
    }


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
        "course",
        "batch",
        "payment_type",
        "councellor"
    ).all()

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
    queryset = Center.objects.select_related("country", "state").all()
    serializer_class = CenterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name", "address", "country__name", "state__name"]


class CenterRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Center.objects.select_related("country", "state").all()
    serializer_class = CenterSerializer
    permission_classes = [IsAuthenticated]


class CoursePaymentListCreateAPIView(generics.ListCreateAPIView):
    queryset = CoursePayment.objects.select_related(
        "student",
        "student__profile",
        "student__profile__user",
        "installment",
        "installment__plan",
        "installment__plan__course"
    )
    serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    
class CoursePaymentListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    

    def get(self, request):

        queryset = (
            Student.objects
            .select_related("profile", "profile__user", "course")
            .prefetch_related(
                "course_payments__installment__plan__course"
            )
        )

        data = []

        for student in queryset:
            payments = list(student.course_payments.all())
            if not payments:
                continue

            plan = payments[0].installment.plan
            course = plan.course

            total_fee = course.total_fee

            paid_amount = sum(
                (p.amount_paid for p in payments),
                Decimal("0.00")
            )

            pending_amount = total_fee - paid_amount

            resolved_plan = get_staff_installment_plan(
                student,
                course,
                preferred_plan=plan,
            ) or plan
            next_installment = get_next_unpaid_installment_item(
                student,
                course,
                preferred_plan=resolved_plan,
            )
            next_due_date = get_installment_due_date_for_staff(
                student,
                next_installment,
            )

            user = student.profile.user
            data.append({
                "id": student.id,
                "student_name": f"{user.first_name} {user.last_name}",
                "student_id": student.student_id,
                "course_title": course.title,
                "total_fee": total_fee,
                "paid_amount": paid_amount,
                "pending_amount": pending_amount,
                "next_due_date": next_due_date,
            })

        return Response(data, status=200)

class CoursePaymentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    

    def get(self, request, pk):

        student = get_object_or_404(
            Student.objects.select_related("profile", "profile__user"),
            id=pk,
        )

        payment = (
            CoursePayment.objects
            .filter(student=student)
            .select_related(
                "student",
                "student__profile",
                "student__profile__user",
                "installment",
                "installment__plan",
                "installment__plan__course"
            )
            .order_by("-payment_date")
            .first()
        )

        if not payment:
            return Response(
                {"detail": "No payments found for this student"},
                status=404
            )

        serializer = CoursePaymentDetailSerializer(payment)
        return Response(serializer.data, status=200)


class CoursePaymentDestroyAPIView(generics.DestroyAPIView):
    queryset = CoursePayment.objects.all()
    serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    

class CoursePaymentRetrieveAPIView(generics.RetrieveAPIView):
    queryset = CoursePayment.objects.select_related(
        "student",
        "student__profile",
        "student__profile__user",
        "installment",
        "installment__plan",
        "installment__plan__course"
    )
    serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    


