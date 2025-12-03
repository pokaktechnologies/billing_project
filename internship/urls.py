from django.urls import path, include
from .views import instructor, intern

instructor_patterns = [
    path('course/', instructor.InstructorCourseListCreateAPIView.as_view(), name='instructor-course-list'),
    path('course/<int:pk>/', instructor.InstructorCourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-course-detail'),
]

# intern_patterns = [
#     path('course/', intern.InternCourseListCreateAPIView.as_view(), name='intern-course-list'),
#     path('course/<int:pk>/', intern.InternCourseRetrieveUpdateDestroyAPIView.as_view(), name='intern-course-detail'),
# ]

urlpatterns = [
    path('instructor/', include((instructor_patterns))),
    # path('intern/', include((intern_patterns))),
]
