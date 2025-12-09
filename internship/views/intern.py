from rest_framework.views import APIView
from rest_framework import generics, status, serializers
from rest_framework.response import Response
from ..models import (
    Course, AssignedStaffCourse, StudyMaterial, Task, 
    TaskSubmission, TaskAssignment, TaskSubmissionAttachment
)
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated
from ..serializers.intern import *
from rest_framework import viewsets
from ..serializers.instructor import TaskSerializer, StudyMaterialSerializer, CourseSerializer
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404


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

        assigned_course_ids = AssignedStaffCourse.objects.filter(
            staff=staff_profile
        ).values_list("course_id", flat=True)

        return StudyMaterial.objects.filter(
            course_id__in=assigned_course_ids,
            is_public=True,
        )

    
# path('study-material/<int:pk>/', intern.MyStudyMaterialDetailView.as_view(), name='intern-study-material-detail'),
class MyStudyMaterialDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "intern"
    serializer_class = StudyMaterialSerializer
    queryset = StudyMaterial.objects.filter(is_public=True)


    



class MyTaskViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InternTaskSerializer

    def get_queryset(self):
        user = self.request.user
        staff_profile = getattr(user, "staff_profile", None)
        if not staff_profile:
            return Task.objects.none()

        return Task.objects.filter(assignments__staff=staff_profile)



# views.py
# from rest_framework import generics, permissions, status
# from rest_framework.response import Response
# from ..models import TaskSubmission, TaskAssignment


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