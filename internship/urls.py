from django.urls import path, include
from .views import instructor, intern, report_view

instructor_patterns = [
    path('course/', instructor.InstructorCourseListCreateAPIView.as_view(), name='instructor-course-list'),
    path('course/<int:pk>/', instructor.InstructorCourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-course-detail'),
    path('assigned-staff-course/', instructor.InstructorAssignedStaffCourseListCreateAPIView.as_view(), name='instructor-assignedstaffcourse-list'),
    path('assigned-staff-course/<int:pk>/', instructor.InstructorAssignedStaffCourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-assignedstaffcourse-detail'),
    path('course/<int:course_id>/enrolled-students/', instructor.CourseEnrolledStudentsListAPIView.as_view(), name='instructor-course-enrolled-students'),
    path('interns/', instructor.InternListAPIView.as_view()),
    path('interns/<int:pk>/', instructor.InternProfileInfoAPIView.as_view()),
    path('interns/stats/', instructor.InternsStatsAPIView.as_view()),

    path('study-material/', instructor.StudyMaterialAPIView.as_view(), name='instructor-study-material-list'),
    path('study-material/<int:pk>/', instructor.StudyMaterialDetailAPIView.as_view(), name='instructor-study-material-detail'),

    path('study-material/<int:course_id>/course/', instructor.CourseStudyMaterialListAPIView.as_view(), name='instructor-course-study-material-list'),


    path('tasks/', instructor.TaskListCreateAPIView.as_view()),
    path('tasks/<int:pk>/', instructor.TaskRetrieveUpdateDestroyAPIView.as_view()),
    path('tasks/<int:pk>/detail/', instructor.TaskDetailAPIView.as_view()),
    path('tasks/stats/', instructor.TaskStatsAPIView.as_view()),
    path('tasks/intern/<int:staff_id>/stats/', instructor.InternTaskStatsAPIView.as_view()),
    path('attachments/<int:pk>/', instructor.TaskAttachmentDeleteAPIView.as_view()),

    path('staff/<int:staff_id>/performance/', instructor.StaffPerformanceStatsAPIView.as_view()),


    
    path('submissions/', instructor.InstructorSubmissionListAPIView.as_view()),
    path('submissions/<int:pk>/', instructor.InstructorSubmissionDetailAPIView.as_view()),
    path('submissions/<int:pk>/review/', instructor.InstructorSubmissionReviewAPI.as_view()),
    path('submissions/stats/', instructor.SubmissionStatsAPIView.as_view()),

    path('course/<int:course_id>/installments/', instructor.InstallmentListAPIView.as_view()),

    path("payments/", instructor.CoursePaymentListCreateAPIView.as_view()),
    path("payments-list/", instructor.CoursePaymentListAPIView.as_view()),
    path("payments/<int:pk>/", instructor.CoursePaymentRetrieveAPIView.as_view()),
    path("payments/<int:pk>/delete/", instructor.CoursePaymentDestroyAPIView.as_view()),

    path("payments/<int:pk>/detail/", instructor.CoursePaymentDetailAPIView.as_view()),
]


intern_patterns = [
    path('course/', intern.MyCourseView.as_view(), name='intern-course-list'),
    path('course/<int:pk>/', intern.MyCourseDetailView.as_view(), name='intern-course-detail'),
    path('course/<int:course_id>/study-materials/', intern.MyCourseStudyMaterialListAPIView.as_view(), name='intern-course-study-material-list'),
    path('study-material/<int:pk>/', intern.MyStudyMaterialDetailView.as_view(), name='intern-study-material-detail'),

    path("tasks/", intern.MyTaskViewSet.as_view({'get': 'list'})),
    path("tasks/<int:pk>/", intern.MyTaskViewSet.as_view({'get': 'retrieve'})),
    path('tasks/stats/', intern.MyTaskStatsAPIView.as_view()),

    path('submissions/', intern.TaskSubmissionListCreateAPI.as_view()),
    path('submissions/<int:pk>/', intern.TaskSubmissionDetailAPI.as_view()),
    path('submission-attachments/<int:pk>/', intern.DeleteTaskSubmissionAttachmentAPI.as_view()),

    path('payments/', intern.MyCoursePaymentListAPIView.as_view()),

    #Dashboard
    path('dashaboard/',intern.InternDashboardAPIView.as_view()),
    
   
]

report_patterns = [
    path('reports-task/', report_view.TaskReportAPIView.as_view()),
    path('reports-intern_performance/', report_view.InternTaskPerformanceReportView.as_view()),
    path('report-task-submission/', report_view.TaskSubmissionReportAPIView.as_view()),
    path("reports-intern-payment-summary/", report_view.InternPaymentSummaryReportAPIView.as_view()),
    path("reports-intern-summary/", report_view.InternSummaryReportAPIView.as_view()),
    path("report-enrollment/", report_view.EnrollmentReportAPIView.as_view())

]

urlpatterns = [
    path('instructor/', include((instructor_patterns))),
    path('intern/', include((intern_patterns))),
    path('report/', include(report_patterns)),
]

