from .views.LeadsViews import *
from .views.MarketingViews import *
from .views.ChartViews import *
from .views.LeadsManagement import *
from django.urls import path

urlpatterns = [

    # path('followup/', LeadsFollowUpView.as_view(), name='lead_followup'),
    path('search/', LeadSearchView.as_view(), name='lead_search'),
    path('no-quotation/', LeadsWithoutQuotationView.as_view(), name='leads-without-quotation'),
    path('meeting/', MeetingsView.as_view(), name='meeting_view'),
    path('meeting/<int:pk>/', MeetingDetailView.as_view(), name='meeting_detail'),
    path('meeting/reminder/', MeetingRemiderView.as_view(), name='meeting_reminder'),

    # marketing leads
    path('location/', LocationtView.as_view(), name='location_view'),
    path('location/<int:pk>/', LocationtDetailView.as_view(), name='location_detail'),
    path('source/', SourceAPIView.as_view(), name='source_view'),
    path('source/<int:pk>/', SourceDetailView.as_view(), name='source_detail'),
    path('category/', CategoryAPIView.as_view(), name='category_view'),
    path('category/<int:pk>/', CategoryDetailAPIView.as_view(), name='category_detail'),
    path('marketing-report/', MarketingReportAPIView.as_view(), name='marketing_report_view'),
    path('marketing-report/<int:pk>/', MarketingReportDetailAPIView.as_view(), name='marketing_report_detail'),
    path('leadschart/', LeadsChartView.as_view(), name='leads_chart'),


    # staff leads management
    path('staff/', StaffLeadView.as_view(), name='staff_create_lead'),
    path('staff/<int:pk>/', StaffLeadDetailView.as_view(), name='lead_detail'),
    path('staff/followups/', StaffFollowUpView.as_view(), name='followup-list-create'),
    path('staff/followups/<int:pk>/', StaffFollowUpDetailView.as_view(), name='followup-detail'),
    path('staff/<int:lead_id>/followup/', LeadFollowUpView.as_view(), name='lead_followup'),
    path('staff/followups/summary/', StaffFollowUpSummaryView.as_view(), name='staff-followup-summary'),
    path('staff/meeting/', MeetingsView.as_view(), name='meeting_view'),
    path('staff/meeting/<int:pk>/', MeetingDetailView.as_view(), name='meeting_detail'),
    path('staff/<int:lead_id>/meeting/', LeadMeetingView.as_view(), name='lead_meeting'),
    path('staff/meeting/summary/', MeetingSummaryView.as_view(), name=''),
    # reminders 
    path('staff/reminders/', RemindersView.as_view(), name='staff-reminders-list-create'),
    path('staff/reminders/<int:pk>/', RemindersDetailView.as_view(), name='staff-reminders-detail'),
    path('staff/<int:lead_id>/reminders/', LeadRemindersView.as_view(), name='staff-lead-reminders'),
    path('staff/reminders/summary/', RemindersSummaryView.as_view(), name='staff-reminders-summary'),

    path("activity/manual/", ManualActivityLogView.as_view()),
    path("activity/manual/<int:pk>/", ManualActivityLogDetailView.as_view()),

    # admin leads management
    path('admin/', AdminLeadsView.as_view(), name='leads_view'),
    path('admin/<int:pk>/', AdminLeadDetailView.as_view(), name='admin_lead_detail'),
    path('admin/assign/', AssignLeadsToSalespersonView.as_view(), name='assign_leads_to_salesperson'),
    path('admin/delete-multiple/', DeleteMultipleLeadsView.as_view(), name='delete_multiple_leads'),
    path('admin/lead-progress/<int:lead_id>/', LeadProgressView.as_view(), name='lead_progress_view'),
    path('admin/lead-activity-log/<int:lead_id>/', LeadActivityLogView.as_view(), name='lead_activity_log_view'),
    path('admin/lead-activity-counts/<int:lead_id>/', LeadActivityCountsView.as_view(), name='lead_activity_counts_view'),

    #lead report
    path("reports/leads/", LeadReportAPIView.as_view(), name="lead-report"),
    path("reports/lead-peformance/",LeadPerformanceAPIView.as_view(),name="lead-report-performance"),
    path("reports/lead-source-report/",LeadSourceReportAPIView.as_view(),name="lead-report-performance"),
    path("reports/enquiry/",EnquiryReportAPIView.as_view(),name="lead-report-performance"),
    path("reports/followup-report/", FollowUpReportAPIView.as_view(), name="followup-report"),
    path("reports/sales-person-lead-report/", SalespersonLeadReportAPIView.as_view(), name="followup-report"),


    

    # salesperson leads management
    path('admin/salesperson/lead-stats/', SalespersonLeadStatsView.as_view(), name='salesperson_lead_stats'),

    #Dashboard
    path('dashboard/', BDEDashboardView.as_view(), name='leads_by_source_chart'),


    
]
