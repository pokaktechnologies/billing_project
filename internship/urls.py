from django.urls import path, include
from .views import application, instructor, intern, report_view, internship_admin

instructor_patterns = [
    path('course/', instructor.InstructorCourseListCreateAPIView.as_view(), name='instructor-course-list'),
    path('course/<int:pk>/', instructor.InstructorCourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-course-detail'),
    path('assigned-staff-course/', instructor.InstructorAssignedStaffCourseListCreateAPIView.as_view(), name='instructor-assignedstaffcourse-list'),
    path('assigned-staff-course/<int:pk>/', instructor.InstructorAssignedStaffCourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-assignedstaffcourse-detail'),
    path('course/<int:course_id>/enrolled-students/', instructor.CourseEnrolledStudentsListAPIView.as_view(), name='instructor-course-enrolled-students'),
    path('students/', instructor.StudentListAPIView.as_view()),
    path('students/<int:pk>/', instructor.StudentProfileInfoAPIView.as_view()),
    path('students/stats/', instructor.StudentsStatsAPIView.as_view()),

    path('study-material/', instructor.StudyMaterialAPIView.as_view(), name='instructor-study-material-list'),
    path('study-material/<int:pk>/', instructor.StudyMaterialDetailAPIView.as_view(), name='instructor-study-material-detail'),

    path('study-material/<int:course_id>/course/', instructor.CourseStudyMaterialListAPIView.as_view(), name='instructor-course-study-material-list'),


    path('tasks/', instructor.TaskListCreateAPIView.as_view()),
    path('tasks/<int:pk>/', instructor.TaskRetrieveUpdateDestroyAPIView.as_view()),
    path('tasks/<int:pk>/detail/', instructor.TaskDetailAPIView.as_view()),
    path('tasks/stats/', instructor.TaskStatsAPIView.as_view()),
    path('tasks/intern/<int:student_id>/stats/', instructor.InternTaskStatsAPIView.as_view()),
    # path('tasks/intern/<int:staff_id>/stats/', instructor.InternTaskStatsAPIView.as_view()),
    path('batch/<int:batch_id>/tasks/', instructor.BatchTaskListAPIView.as_view(), name='instructor-batch-task-list'),
    path('attachments/<int:pk>/', instructor.TaskAttachmentDeleteAPIView.as_view()),

    path('students/<int:student_id>/performance/', instructor.StudentPerformanceStatsAPIView.as_view()),



    path('submissions/', instructor.InstructorSubmissionListAPIView.as_view()),
    path('submissions/<int:pk>/', instructor.InstructorSubmissionDetailAPIView.as_view()),
    path('submissions/<int:pk>/review/', instructor.InstructorSubmissionReviewAPI.as_view()),
    path('submissions/stats/', instructor.SubmissionStatsAPIView.as_view()),

    path('faculty/my-courses/', instructor.FacultyCourseListAPIView.as_view()),
    path('faculty/my-students/', instructor.FacultyStudentsAPIView.as_view()),
    # path('course/<int:course_id>/installments/', instructor.InstallmentListAPIView.as_view()),

    # path("payments/", instructor.CoursePaymentListCreateAPIView.as_view()),
    # path("payments-list/", instructor.CoursePaymentListAPIView.as_view()),
    # path("payments/<int:pk>/", instructor.CoursePaymentRetrieveAPIView.as_view()),
    # path("payments/<int:pk>/delete/", instructor.CoursePaymentDestroyAPIView.as_view()),

    # path("payments/<int:pk>/detail/", instructor.CoursePaymentDetailAPIView.as_view()),
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

internship_admin_patterns = [
    path('course/', internship_admin.CourseListCreateAPIView.as_view(), name='instructor-course-list'),
    path('course/<int:pk>/', internship_admin.CourseRetrieveUpdateDestroyAPIView.as_view(), name='instructor-course-detail'),
    path("installment-plan/", internship_admin.InstallmentListAPIView.as_view()),
    path("installment-plan/<int:pk>/", internship_admin.InstallmentPlanUpdateAPIView.as_view()),

    path('course/<int:course_id>/installments/', internship_admin.InstallmentSelectionListAPIView.as_view()),

    #Faculty
    path('faculty/', internship_admin.FacultyListCreateAPIView.as_view(), name='faculty-list'),
    path('faculty/<int:pk>/', internship_admin.FacultyRetrieveUpdateDestroyAPIView.as_view(), name='faculty-detail'),
    # path('course-faculty/', internship_admin.FacultyListCreateAPIView.as_view(), name='course-faculty-list'),
    # path('course-faculty/<int:pk>/', internship_admin.FacultyRetrieveUpdateDestroyAPIView.as_view(), name='course-faculty-detail'),

    #Batch
    path('batch/preview/', internship_admin.BatchNumberPreviewAPIView.as_view(), name='batch-number-preview'),
    path('batch/', internship_admin.BatchListCreateAPIView.as_view(), name='batch-list'),
    path('batch/<int:pk>/', internship_admin.BatchRetrieveUpdateDestroyAPIView.as_view(), name='batch-detail'),

    path("students/", internship_admin.StudentListCreateAPIView.as_view(), name="student-list-create"),
    path("students/<int:id>/", internship_admin.StudentRetrieveUpdateDestroyAPIView.as_view(), name="student-detail"),
    path("students/<int:pk>/credentials/", internship_admin.StudentCredentialsAPIView.as_view(), name="student-credentials"),

    path("enrollments/", internship_admin.StudentCourseEnrollmentView.as_view(), name="student-course-enrollment-list-create"),
    path("enrollments/<int:pk>/", internship_admin.StudentCourseEnrollmentDetailView.as_view(), name="student-course-enrollment-detail"),

    path("centers/", internship_admin.CenterListCreateAPIView.as_view(), name="center-list-create"),
    path("centers/<int:pk>/", internship_admin.CenterRetrieveUpdateDestroyAPIView.as_view(), name="center-detail"),

    path("payments/", internship_admin.CoursePaymentListCreateAPIView.as_view()),
    path("payments/<int:pk>/detail/", internship_admin.StudentPaymentDetailAPIView.as_view()),
    path("payments/<int:pk>/delete/", internship_admin.CoursePaymentDestroyAPIView.as_view()),
    path("payments/<int:pk>/", internship_admin.CoursePaymentRetrieveAPIView.as_view()),
    path("payments-list/", internship_admin.StudentPaymentListAPIView.as_view()),

    path("class/", internship_admin.ClassListCreateAPIView.as_view()),
    path("class/<int:pk>/", internship_admin.ClassRetrieveUpdateDestroyAPIView.as_view()),
    path("sections/", internship_admin.SectionListCreateAPIView.as_view()),
    path("sections/<int:pk>/", internship_admin.SectionRetrieveUpdateDeleteAPIView.as_view()),

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
    path('', include((internship_admin_patterns))),
    path('applications/', application.InternshipApplicationAPIView.as_view(), name='internship-application-list-create'),
    path('applications/<int:pk>/', application.InternshipApplicationAPIView.as_view(), name='internship-application-detail'),
    path('report/', include(report_patterns)),
]

