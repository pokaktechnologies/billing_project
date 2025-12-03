from rest_framework import generics
from internship.models import Course
from internship.serializers.instructor import CourseSerializer


class InstructorCourseListCreateAPIView(generics.ListCreateAPIView):
	queryset = Course.objects.all()
	serializer_class = CourseSerializer


class InstructorCourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
	queryset = Course.objects.all()
	serializer_class = CourseSerializer

