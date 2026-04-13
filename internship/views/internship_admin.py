from rest_framework import generics,filters
from ..models import *
from ..serializers.internship_admin import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count



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