from rest_framework import generics
from rest_framework.response import Response
from internship.models import Course
from internship.serializers.instructor import CourseSerializer
from internship.models import AssignedStaffCourse
from internship.serializers.instructor import *
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class InstructorCourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

class InstructorCourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"


class InstructorAssignedStaffCourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = AssignedStaffCourse.objects.select_related("staff", "course")
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

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
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"


#list staff inter by course id (Enrolled Students(count))
class CourseEnrolledStudentsListAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=404)
        
        assigned_staff_courses = AssignedStaffCourse.objects.filter(course=course).select_related("staff__user")
        serializer = AssignedStaffCourseSerializer(assigned_staff_courses, many=True)
        return Response(
            {
                 "enrolled_students_count": assigned_staff_courses.count(),
                "enrolled_students": serializer.data,
            }
        )



# ====== Study Material ViewSet ======

class StudyMaterialAPIView(generics.ListCreateAPIView):
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

class StudyMaterialDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"


# list study materials by course
class CourseStudyMaterialListAPIView(generics.ListAPIView):
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "instructor"

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")

        title = self.request.query_params.get("title")
        material_type = self.request.query_params.get("type") 

        queryset = StudyMaterial.objects.filter(course=course_id).order_by("-created_at")

        if title:
            queryset = queryset.filter(title__icontains=title)

        if material_type:
            queryset = queryset.filter(material_type=material_type)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "results": serializer.data
        })




class TaskListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all().order_by('-id')

    def perform_create(self, serializer):
        return serializer.save()

class TaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

class TaskDetailAPIView(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = InstructorTaskDetailSerializer
    permission_classes = [IsAuthenticated]


class TaskAttachmentDeleteAPIView(generics.DestroyAPIView):
    queryset = TaskAttachment.objects.all()
    permission_classes = [IsAuthenticated]


# list of submissions for instructor to review
class InstructorSubmissionListAPIView(generics.ListAPIView):
    serializer_class = InstructorSubmissionSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        return TaskSubmission.objects.all()


# detail view to review a submission
class InstructorSubmissionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = InstructorSubmissionSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        return TaskSubmission.objects.all()

class InstructorSubmissionReviewAPI(generics.UpdateAPIView):
    serializer_class = InstructorSubmissionReviewSerializer
    permission_classes = [IsAuthenticated]   # add your instructor permission

    def get_queryset(self):
        return TaskSubmission.objects.all()