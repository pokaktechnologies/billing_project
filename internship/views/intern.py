from rest_framework.views import APIView
from rest_framework import generics, status, serializers
from rest_framework.response import Response

from accounts.models import StaffProfile
from ..models import (
    Course, AssignedStaffCourse, CoursePayment, StudyMaterial, Task, 
    TaskSubmission, TaskAssignment, TaskSubmissionAttachment
)
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated
from ..serializers.intern import *
from rest_framework import viewsets
from ..serializers.instructor import TaskSerializer, StudyMaterialSerializer, CourseSerializer
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import OuterRef, Subquery
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now

# === Course Views ===

class MyCourseView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "intern"

    def get(self, request):
        staff_profile = getattr(request.user, "staff_profile", None)
        if not staff_profile:
            return Response(
                {"detail": "User has no staff profile"},
                status=status.HTTP_400_BAD_REQUEST
            )

        assigned = AssignedStaffCourse.objects.filter(
            staff=staff_profile
        ).select_related("course")

        courses = [a.course for a in assigned]
        # get the count of the study meterials for each course
        study_material_counts = {
            course.id: StudyMaterial.objects.filter(course=course).count()
            for course in courses
        }
        data = []
        for course in courses:
            course_data = CourseSerializer(course).data
            course_data["study_material_count"] = study_material_counts.get(course.id, 0)
            data.append(course_data)

        return Response(data)


class MyCourseDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "intern"
    serializer_class = CourseSerializer
    queryset = Course.objects.all()



class MyCourseStudyMaterialListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "intern"
    serializer_class = StudyMaterialSerializer

    def get_queryset(self):
        staff_profile = getattr(self.request.user, "staff_profile", None)
        if not staff_profile:
            return StudyMaterial.objects.none()

        assigned_course_ids = (
            AssignedStaffCourse.objects
            .filter(staff=staff_profile)
            .values_list("course_id", flat=True)
        )

        queryset = StudyMaterial.objects.filter(
            course_id__in=assigned_course_ids,
            is_public=True,
        )

        # search by title
        title = self.request.query_params.get("title")
        if title:
            queryset = queryset.filter(title__icontains=title)

        # filter by type
        material_type = self.request.query_params.get("type")
        if material_type:
            queryset = queryset.filter(material_type=material_type)

        return queryset.order_by("-created_at")

    
# path('study-material/<int:pk>/', intern.MyStudyMaterialDetailView.as_view(), name='intern-study-material-detail'),
class MyStudyMaterialDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "intern"
    serializer_class = StudyMaterialSerializer
    queryset = StudyMaterial.objects.filter(is_public=True)


    
# === Task Views ===

class MyTaskViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InternTaskSerializer

    def get_queryset(self):
        user = self.request.user
        staff_profile = getattr(user, "staff_profile", None)
        
        if not staff_profile:
            return Task.objects.none()

        # Subquery → latest assignment per task
        latest_assignment_sub = (
            TaskAssignment.objects
            .filter(task=OuterRef("pk"), staff=staff_profile)
            .order_by("-assigned_at")
        )

        queryset = (
            Task.objects
            .filter(assignments__staff=staff_profile)
            .distinct()
            .annotate(
                latest_status=Subquery(
                    latest_assignment_sub.values("status")[:1]
                )
            )
        )

        # GET query params
        title = self.request.query_params.get("title")
        status_filter = self.request.query_params.get("status")

        # Search by task title
        if title:
            queryset = queryset.filter(title__icontains=title)

        # Filter by latest assignment status
        if status_filter:
            queryset = queryset.filter(latest_status=status_filter)

        return queryset




class MyTaskStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        staff_profile = getattr(user, "staff_profile", None)

        if not staff_profile:
            return Response({"detail": "Staff profile not found."}, status=400)

        # Subquery: get latest assignment for each task
        latest_assignment_subquery = (
            TaskAssignment.objects
            .filter(staff=staff_profile, task=OuterRef("pk"))
            .order_by("-assigned_at")
        )

        # Annotate each task with its latest status
        tasks = (
            Task.objects
            .filter(assignments__staff=staff_profile)
            .distinct()
            .annotate(
                latest_status=Subquery(
                    latest_assignment_subquery.values("status")[:1]
                )
            )
        )

        # Database-level counts (clean, fast, correct)
        data = {
            "all_tasks": tasks.count(),
            "pending": tasks.filter(latest_status="pending").count(),
            "submitted": tasks.filter(latest_status="submitted").count(),
            "approved": tasks.filter(latest_status="completed").count(),
            "revision": tasks.filter(latest_status="revision_required").count(),
        }

        return Response(data)





# === Task Submission Views ===

class TaskSubmissionListCreateAPI(generics.ListCreateAPIView):
    serializer_class = TaskSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # only my submissions
        return TaskSubmission.objects.filter(
            assignment__staff__user=self.request.user
        )

    def perform_create(self, serializer):
        assignment_id = self.request.data.get("assignment")

        try:
            assignment = TaskAssignment.objects.get(
                id=assignment_id,
                staff__user=self.request.user
            )
        except TaskAssignment.DoesNotExist:
            raise ValueError("You are not assigned to this task")

        serializer.save(assignment=assignment)


class TaskSubmissionDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskSubmission.objects.filter(
            assignment__staff__user=self.request.user
        )



class DeleteTaskSubmissionAttachmentAPI(generics.DestroyAPIView):
    serializer_class = TaskSubmissionAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskSubmissionAttachment.objects.filter(
            submission__assignment__staff__user=self.request.user
        )
    
class MyCoursePaymentListAPIView(generics.ListAPIView):
    # serializer_class = CoursePaymentSerializer
    permission_classes = [IsAuthenticated]
    queryset = CoursePayment.objects.all()

    def get(self, request,):

        # Get staff
        staff = get_object_or_404(StaffProfile, id=request.user.staff_profile.id)

        # Get latest payment (to identify course)
        payment = (
            CoursePayment.objects
            .filter(staff=staff)
            .select_related(
                "staff",
                "installment",
                "installment__course"
            )
            .order_by("-payment_date")
            .first()
        )

        if not payment:
            return Response(
                {"detail": "No payments found for this staff"},
                status=404
            )

        serializer = CoursePaymentDetailSerializer(payment)
        return Response(serializer.data, status=200)
