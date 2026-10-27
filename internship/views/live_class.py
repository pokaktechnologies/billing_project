import json
import logging
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ..models import LiveClass, LiveClassAttendance, StudentCourseEnrollment, Faculty
from ..serializers.live_class import (
    LiveClassSerializer,
    StudentLiveClassSerializer,
    LiveClassAttendanceSerializer,
)
from ..services.livekit_service import LiveKitService

logger = logging.getLogger(__name__)


def get_staff_profile(user):
    return getattr(user, "staff_profile", None) or getattr(user, "staffprofile", None)


def get_student_profile(user):
    staff = get_staff_profile(user)
    return getattr(staff, "student_profile", None) if staff else None


def get_faculty_profile(user):
    staff = get_staff_profile(user)
    return getattr(staff, "faculty_profile", None) if staff else None


class StandardLiveClassPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class LiveClassListCreateAPIView(APIView):
    """
    API for Admins and Faculty:
    - GET: List live classes with filters (course, batch, status, search)
    - POST: Schedule a new live class
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = LiveClass.objects.select_related('course', 'batch', 'faculty__user__user').all()

        course_id = request.query_params.get('course')
        batch_id = request.query_params.get('batch')
        status_param = request.query_params.get('status')
        search = request.query_params.get('search')

        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

        # If logged-in user is a faculty member and not admin, prioritize their assigned classes
        faculty = get_faculty_profile(request.user)
        if faculty:
            # If user explicitly wants just their classes or accesses via instructor endpoint
            if request.path.startswith('/internship/instructor/') or request.query_params.get('my_classes') == 'true':
                queryset = queryset.filter(faculty=faculty)

        paginator = StandardLiveClassPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request)
        serializer = LiveClassSerializer(paginated_qs, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = LiveClassSerializer(data=request.data)
        if serializer.is_valid():
            # If faculty is not provided, auto-assign if current user is faculty
            faculty = serializer.validated_data.get('faculty')
            if not faculty:
                user_faculty = get_faculty_profile(request.user)
                if user_faculty:
                    serializer.validated_data['faculty'] = user_faculty

            live_class = serializer.save()
            return Response(LiveClassSerializer(live_class).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LiveClassDetailAPIView(APIView):
    """
    API for Admins and Faculty to retrieve, update, or cancel a live class
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            LiveClass.objects.select_related('course', 'batch', 'faculty__user__user'),
            pk=pk
        )

    def get(self, request, pk):
        live_class = self.get_object(pk)
        serializer = LiveClassSerializer(live_class)
        return Response(serializer.data)

    def patch(self, request, pk):
        live_class = self.get_object(pk)
        serializer = LiveClassSerializer(live_class, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        live_class = self.get_object(pk)
        live_class.status = 'cancelled'
        live_class.save()
        return Response({"message": "Live class cancelled successfully."}, status=status.HTTP_200_OK)


class LiveClassStartAPIView(APIView):
    """
    API for Faculty / Admin to start the class (moves status to 'live')
    and returns the Host Access Token for LiveKit.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        live_class = get_object_or_404(LiveClass, pk=pk)

        if live_class.status == 'completed':
            return Response({"error": "Class has already been completed."}, status=status.HTTP_400_BAD_REQUEST)

        # Update status
        if live_class.status != 'live':
            live_class.status = 'live'
            live_class.actual_start_time = timezone.now()
            live_class.save()

        user = request.user
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        identity = f"faculty_{user.id}"

        livekit_url, _, _ = LiveKitService.get_credentials()
        try:
            token = LiveKitService.generate_token(
                room_name=live_class.room_name,
                identity=identity,
                name=full_name,
                is_host=True
            )
        except Exception as e:
            logger.error(f"Failed to generate LiveKit token: {str(e)}")
            return Response({"error": f"Failed to generate LiveKit token: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Live class started successfully.",
            "live_class_id": live_class.id,
            "room_name": live_class.room_name,
            "token": token,
            "livekit_url": livekit_url,
            "role": "host",
            "status": live_class.status
        })


class LiveClassEndAPIView(APIView):
    """
    API for Faculty / Admin to end the class (moves status to 'completed').
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        live_class = get_object_or_404(LiveClass, pk=pk)

        live_class.status = 'completed'
        live_class.actual_end_time = timezone.now()
        live_class.save()

        return Response({
            "message": "Live class completed.",
            "live_class_id": live_class.id,
            "status": live_class.status,
            "actual_end_time": live_class.actual_end_time
        })


class StudentLiveClassListAPIView(APIView):
    """
    API for Enrolled Students to list their upcoming and ongoing live classes.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        student = get_student_profile(request.user)
        if not student:
            return Response({"error": "User does not have an active student profile."}, status=status.HTTP_403_FORBIDDEN)

        # Get course enrollments for this student
        enrollments = StudentCourseEnrollment.objects.filter(
            student=student
        ).values("course_id", "batch_id")

        if not enrollments:
            return Response([], status=status.HTTP_200_OK)

        course_ids = {e["course_id"] for e in enrollments if e["course_id"]}
        batch_ids = {e["batch_id"] for e in enrollments if e["batch_id"]}

        # Match classes where student is enrolled in course and either batch matches or batch is null (all batches)
        queryset = LiveClass.objects.filter(
            course_id__in=course_ids,
            status__in=['scheduled', 'live']
        ).filter(
            Q(batch_id__in=batch_ids) | Q(batch__isnull=True)
        ).select_related('course', 'batch', 'faculty__user__user').order_by('scheduled_start_time')

        serializer = StudentLiveClassSerializer(queryset, many=True)
        return Response(serializer.data)


class StudentLiveClassJoinAPIView(APIView):
    """
    API for Enrolled Students to request a Viewer LiveKit Token to join a live class.
    Also logs/updates attendance.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        live_class = get_object_or_404(LiveClass, pk=pk)

        if live_class.status not in ['live', 'scheduled']:
            return Response({"error": f"Cannot join a class that is {live_class.get_status_display().lower()}."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        student = get_student_profile(user)
        if not student:
            return Response({"error": "User does not have an active student profile."}, status=status.HTTP_403_FORBIDDEN)

        # Verify enrollment
        has_enrollment = StudentCourseEnrollment.objects.filter(
            student=student,
            course=live_class.course
        )
        if live_class.batch:
            has_enrollment = has_enrollment.filter(Q(batch=live_class.batch) | Q(batch__isnull=True))

        if not has_enrollment.exists():
            return Response({"error": "You are not enrolled in this class's course/batch."}, status=status.HTTP_403_FORBIDDEN)

        # Record attendance
        LiveClassAttendance.objects.get_or_create(
            live_class=live_class,
            student=student
        )

        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        identity = f"student_{student.student_id}"

        livekit_url, _, _ = LiveKitService.get_credentials()
        try:
            token = LiveKitService.generate_token(
                room_name=live_class.room_name,
                identity=identity,
                name=full_name,
                is_host=False
            )
        except Exception as e:
            logger.error(f"Failed to generate student LiveKit token: {str(e)}")
            return Response({"error": f"Failed to generate LiveKit token: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Token generated successfully.",
            "live_class_id": live_class.id,
            "title": live_class.title,
            "room_name": live_class.room_name,
            "token": token,
            "livekit_url": livekit_url,
            "role": "viewer",
            "status": live_class.status
        })


class LiveClassWebhookAPIView(APIView):
    """
    Receives LiveKit Webhook events (e.g. room_finished, participant_joined).
    No authentication required as it is validated using LiveKit webhook signature or header.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            from livekit import api
            _, api_key, api_secret = LiveKitService.get_credentials()

            auth_header = request.headers.get("Authorization", "")
            body = request.body.decode("utf-8")

            if api_key and api_secret and auth_header:
                receiver = api.WebhookReceiver(api_key, api_secret)
                event = receiver.receive(body, auth_header)
                event_type = event.event
                room = event.room
            else:
                # Fallback to json parsing if direct or local testing
                data = json.loads(body)
                event_type = data.get("event")
                room = data.get("room", {})

            room_name = getattr(room, "name", None) or (room.get("name") if isinstance(room, dict) else None)

            if room_name:
                live_class = LiveClass.objects.filter(room_name=room_name).first()
                if live_class:
                    if event_type == "room_finished" and live_class.status == "live":
                        live_class.status = "completed"
                        live_class.actual_end_time = timezone.now()
                        live_class.save()
                        logger.info(f"LiveClass {live_class.id} marked as completed via webhook.")

            return Response({"status": "received"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"LiveKit webhook error: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
