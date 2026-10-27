import os
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination

from ..models import RecordedClass, StudentCourseEnrollment
from ..serializers.recorded_class import (
    RecordedClassSerializer,
    StudentRecordedClassSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class RecordedClassListCreateAPIView(APIView):
    """
    API for Admins and Faculties to:
    - List recorded classes (with filtering by course, batch, and search by title)
    - Upload a new recorded video / session
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        queryset = RecordedClass.objects.select_related("course", "batch", "faculty__user__user").all()

        course_id = request.query_params.get("course")
        batch_id = request.query_params.get("batch")
        search = request.query_params.get("search")
        is_published = request.query_params.get("is_published")

        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
        if is_published is not None:
            queryset = queryset.filter(is_published=is_published.lower() in ['true', '1'])

        paginator = StandardResultsSetPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request)
        serializer = RecordedClassSerializer(paginated_qs, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = RecordedClassSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # Automatically assign faculty if the logged-in user is a faculty member and not explicitly provided
            faculty = None
            if hasattr(request.user, "staffprofile") and hasattr(request.user.staffprofile, "faculty_profile"):
                faculty = request.user.staffprofile.faculty_profile

            if "faculty" in serializer.validated_data and serializer.validated_data["faculty"]:
                faculty = serializer.validated_data["faculty"]

            serializer.save(faculty=faculty)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecordedClassDetailAPIView(APIView):
    """
    API for Admins and Faculties to:
    - Retrieve details of a recorded class
    - Update metadata, order, or files
    - Delete a recorded class (and clean up file from VPS media disk)
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, pk):
        return get_object_or_404(
            RecordedClass.objects.select_related("course", "batch", "faculty__user__user"),
            pk=pk
        )

    def get(self, request, pk):
        instance = self.get_object(pk)
        serializer = RecordedClassSerializer(instance, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk):
        instance = self.get_object(pk)
        serializer = RecordedClassSerializer(instance, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        instance = self.get_object(pk)
        serializer = RecordedClassSerializer(instance, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        instance = self.get_object(pk)
        # Clean up video file on disk
        if instance.video_file and os.path.isfile(instance.video_file.path):
            try:
                os.remove(instance.video_file.path)
            except OSError:
                pass
        # Clean up thumbnail on disk
        if instance.thumbnail and os.path.isfile(instance.thumbnail.path):
            try:
                os.remove(instance.thumbnail.path)
            except OSError:
                pass

        instance.delete()
        return Response(
            {"message": "Recorded class and associated media deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


class StudentRecordedClassListAPIView(APIView):
    """
    API for Enrolled Students to list and stream recorded classes.
    Restricts access strictly to videos belonging to courses & batches the student is enrolled in.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        student_profile = getattr(user.staffprofile, "student_profile", None) if hasattr(user, "staffprofile") else None

        if not student_profile:
            return Response(
                {"error": "You do not have an active student profile."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get active course enrollments for this student
        enrollments = StudentCourseEnrollment.objects.filter(student=student_profile)
        course_ids = [e.course_id for e in enrollments if e.course_id]
        batch_ids = [e.batch_id for e in enrollments if e.batch_id]

        if not course_ids:
            return Response([], status=status.HTTP_200_OK)

        # Filter videos:
        # 1. Belonging to the student's courses
        # 2. Must be published
        # 3. Either belongs to student's specific batch OR batch is NULL (common course video)
        videos_qs = RecordedClass.objects.filter(
            is_published=True,
            course_id__in=course_ids
        ).filter(
            Q(batch_id__in=batch_ids) | Q(batch__isnull=True)
        ).select_related("course", "batch", "faculty__user__user").order_by("order", "-created_at")

        # Optional filter by course
        filter_course = request.query_params.get("course")
        if filter_course:
            videos_qs = videos_qs.filter(course_id=filter_course)

        serializer = StudentRecordedClassSerializer(videos_qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
