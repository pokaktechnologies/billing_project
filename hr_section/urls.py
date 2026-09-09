from django.urls import path
from .views import *
from .views_dashboard import *

urlpatterns = [
    path('enquiry/', EnquiryCreateView.as_view(), name='enquiry'),
    path('enquiry/<int:pk>/', EnquiryDetailView.as_view(), name='enquiry_detail'),
    path('enquiry/<int:pk>/status/', EnquiryStatusUpdateView.as_view(), name='enquiry_status_update'),
    path('enquiry/statistics/', EnquiryStatisticsView.as_view(), name='enquiry_statistics'),
    path('enquiry/search/', SearchEnquiryView.as_view(), name='enquiry_search'),

    path('erp/enquiry/', ErpEnquiryListCreateView.as_view(), name='erp-enquiry'),
    path('erp/enquiry/<int:pk>/', ErpEnquiryDetailView.as_view(), name='erp-enquiry-detail'),
    path('erp/enquiry/<int:pk>/status/', ErpEnquiryStatusUpdateView.as_view(), name='erp-enquiry-status-update'),
    path('erp/enquiry/statistics/', ErpEnquiryStatisticsView.as_view(), name='erp-enquiry-statistics'),


    path('designation/', DesignationView.as_view(), name='designation_list'),
    path('designation/<int:pk>/', DesignationDetailView.as_view(), name='designation_detail'),
    path('job_posting/', JobPostingView.as_view(), name='job_posting'),
    path('job_posting/<int:pk>/', JobPostingDetailView.as_view(), name='job_posting_detail'),
    path('job_posting/<int:job_id>/apply/', JobApplicationView.as_view(), name='job-apply'),
    path('job_posting/apply/', JobApplicationWithoutJob.as_view(), name='job_application_without_job'),
    path('job_posting/stats/', JobPostingStats.as_view(), name='job_posting_stats'),

    path('job_posting/user/', JobPostingDisplayForUserView.as_view(), name='job_posting_display_for_user'),
    path('job_posting/user/<int:job_id>/', JobPostingDisplayForUserView.as_view(), name='job_posting_display_for_user_detail'),

    path('job_application/', JobApplicationListView.as_view(), name='job_application_list'),
    path('job_application/<int:application_id>/', JobApplicationDetailView.as_view(), name='job_application_detail'),
    path('job_application/<int:application_id>/status/', JobApplicationStatusUpdateView.as_view(), name='job_application_status_update'),
    path('job_application/search/', JobApplicationSearchView.as_view(), name='job_application_resume'),
    path('job_application/stats/', JobApplicationStatsAPIView.as_view(), name='job_application_stats'),

    # Offer Letter
    path("offer-letters/", OfferLetterListCreateAPIView.as_view(), name="offer-letter-list-create"),
    path("offer-letters/<int:pk>/", OfferLetterDetailAPIView.as_view(), name="offer-letter-detail"),
    
    # Dashboard
    path('dashboard/', HrDashaboardView.as_view(), name='hr_dashboard_overview'),
    path('dashboard/metrics/', HrDashboardMetricsAPIView.as_view(), name='hr_dashboard_metrics'),
    path('dashboard/action-items/', HrDashboardActionItemsAPIView.as_view(), name='hr_dashboard_action_items'),
    path('dashboard/attendance-live/', HrDashboardLiveAttendanceAPIView.as_view(), name='hr_dashboard_attendance_live'),
    path('dashboard/leaves/active-upcoming/', HrDashboardLeavesActiveUpcomingAPIView.as_view(), name='hr_dashboard_leaves_active_upcoming'),
    path('dashboard/holidays/upcoming/', HrDashboardUpcomingHolidaysAPIView.as_view(), name='hr_dashboard_holidays_upcoming'),
    path('dashboard/departments-summary/', HrDashboardDepartmentsSummaryAPIView.as_view(), name='hr_dashboard_departments_summary'),
    path('dashboard/employee-milestones/', HrDashboardMilestonesAPIView.as_view(), name='hr_dashboard_milestones'),
    path('dashboard/recruitment/jobs-summary/', HrDashboardRecruitmentJobsSummaryAPIView.as_view(), name='hr_dashboard_recruitment_jobs'),
    path('dashboard/recruitment/recent-applications/', HrDashboardRecentApplicationsAPIView.as_view(), name='hr_dashboard_recent_applications'),
    path('dashboard/payroll/current-status/', HrDashboardPayrollStatusAPIView.as_view(), name='hr_dashboard_payroll_status'),
]
