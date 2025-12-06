from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from internship.models import Course,AssignedStaffCourse,StudyMaterial
from internship.serializers.instructor import CourseSerializer
from accounts.permissions import HasModulePermission
from rest_framework.permissions import IsAuthenticated

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



