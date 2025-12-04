from rest_framework import generics
from rest_framework.response import Response
from internship.models import Course
from internship.serializers.instructor import CourseSerializer
from internship.models import AssignedStaffCourse
from internship.serializers.instructor import *
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated


class InstructorCourseListCreateAPIView(generics.ListCreateAPIView):
	queryset = Course.objects.all()
	serializer_class = CourseSerializer
	permission_classes = [IsAuthenticated]



class InstructorCourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Course.objects.all()
	serializer_class = CourseSerializer
	permission_classes = [IsAuthenticated]





class InstructorAssignedStaffCourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = AssignedStaffCourse.objects.select_related("staff", "course")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AssignedStaffCourseCreateSerializer
        return AssignedStaffCourseSerializer

    def create(self, request, *args, **kwargs):
        serializer = AssignedStaffCourseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_objects = serializer.save()

        # return full details
        data = AssignedStaffCourseSerializer(created_objects, many=True).data
        return Response(data, status=201)


class InstructorAssignedStaffCourseRetrieveUpdateDestroyAPIView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = AssignedStaffCourse.objects.select_related("staff", "course")
    serializer_class = AssignedStaffCourseDetailSerializer
    permission_classes = [IsAuthenticated]

