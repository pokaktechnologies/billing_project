from django.urls import path, include
from .views import instructor, intern

instructor_patterns = [
    path('course/', instructor.InstructorCourseListCreateAPIView.as_view(), name='instructor-course-list'),
    path('course/<int:pk>/', instructor.InstructorCourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-course-detail'),
    path('assigned-staff-course/', instructor.InstructorAssignedStaffCourseListCreateAPIView.as_view(), name='instructor-assignedstaffcourse-list'),
    path('assigned-staff-course/<int:pk>/', instructor.InstructorAssignedStaffCourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-assignedstaffcourse-detail'),
    path('course/<int:course_id>/enrolled-students/', instructor.CourseEnrolledStudentsListAPIView.as_view(), name='instructor-course-enrolled-students'),

    path('study-material/', instructor.StudyMaterialAPIView.as_view(), name='instructor-study-material-list'),
    path('study-material/<int:pk>/', instructor.StudyMaterialDetailAPIView.as_view(), name='instructor-study-material-detail'),

    path('study-material/<int:course_id>/course/', instructor.CourseStudyMaterialListAPIView.as_view(), name='instructor-course-study-material-list'),
]


intern_patterns = [
    path('course/', intern.MyCourseView.as_view(), name='intern-course-list'),
    path('course/<int:pk>/', intern.MyCourseDetailView.as_view(), name='intern-course-detail'),
]

urlpatterns = [
    path('instructor/', include((instructor_patterns))),
    path('intern/', include((intern_patterns))),
]
