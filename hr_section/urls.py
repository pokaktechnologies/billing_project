from django.urls import path
from .views import *

urlpatterns = [
    path('enquiry/', EnquiryCreateView.as_view(), name='enquiry'),
    path('enquiry/<int:pk>/', EnquiryDetailView.as_view(), name='enquiry_detail'),
    path('enquiry/<int:pk>/status/', EnquiryStatusUpdateView.as_view(), name='enquiry_status_update'),
    path('enquiry/statistics/', EnquiryStatisticsView.as_view(), name='enquiry_statistics'),
    path('enquiry/search/', SearchEnquiryView.as_view(), name='enquiry_search'),


    path('designation/', DesignationView.as_view(), name='designation_list'),
    path('designation/<int:pk>/', DesignationDetailView.as_view(), name='designation_detail'),
    path('job_posting/', JobPostingView.as_view(), name='job_posting'),
    path('job_posting/<int:pk>/', JobPostingDetailView.as_view(), name='job_posting_detail'),
    path('job_posting/<int:job_id>/apply/', JobApplicationView.as_view(), name='job-apply'),
    path('job_posting/apply/', JobApplicationWithoutJob.as_view(), name='job_application_without_job'),

    path('job_posting/user/', JobPostingDisplayForUserView.as_view(), name='job_posting_display_for_user'),
    path('job_posting/user/<int:job_id>/', JobPostingDisplayForUserView.as_view(), name='job_posting_display_for_user_detail'),

    path('job_application/', JobApplicationListView.as_view(), name='job_application_list'),
    path('job_application/<int:application_id>/', JobApplicationDetailView.as_view(), name='job_application_detail'),
    path('job_application/<int:application_id>/status/', JobApplicationStatusUpdateView.as_view(), name='job_application_status_update'),
]
