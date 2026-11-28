from django.urls import path

from .views.testing import *
from .views import *

urlpatterns = [
    # Client contract (Development & Testing)
    path('client_contract/', ClientContractView.as_view(), name='client_contract_list'),
    path('client_contract/<int:pk>/', ClientContractDetailView.as_view(), name='client_contract_detail'),

    # Digital Marketing Contracts
    path('dm-contracts/', DMContractListCreateAPIView.as_view(), name='dm-contract-list-create'),
    path('dm-contracts/<int:pk>/', DMContractDetailAPIView.as_view(), name='dm-contract-detail'),
    path('dm-contracts/<int:pk>/extensions/', DMContractExtensionListCreateAPIView.as_view(), name='dm-contract-extensions'),
    path('dm-contracts/<int:pk>/attachments/', DMContractAttachmentUploadView.as_view(), name='dm-contract-attachments-upload'),
    path('dm-contracts/attachments/<int:pk>/', DMContractAttachmentDeleteView.as_view(), name='dm-contract-attachment-delete'),
    path('dm-attachments/<int:pk>/', DMContractAttachmentDeleteView.as_view(), name='dm-attachment-delete-alias'),

    # Digital Marketing Masters
    path('dm-platforms/', DMPlatformListCreateAPIView.as_view(), name='dm-platform-list-create'),
    path('dm-work-types/', DMWorkTypeListCreateAPIView.as_view(), name='dm-work-type-list-create'),

    # Project management
    path('', project_management.as_view(), name='project_management'),
    path('<int:pk>/', project_management_detail.as_view(), name='project_management_detail'),

    #project progression
    path('progression/<int:project_id>/', ProjectProgressionView.as_view(), name='project_progression_list'),

    # Members
    path('members/', MembersView.as_view(), name='members_list'),
    path('members/<int:pk>/', MembersViewDetail.as_view(), name='members_detail'),
    path('department-staff/', DepartmentStaffListView.as_view(), name='department_staff_list'),

    # Stack
    path('stack/', StackView.as_view(), name='stack_list'),
    path('stack/<int:pk>/', StackViewDetail.as_view(), name='stack_detail'),


    # Project members
    path('project_members/', ProjectMembersView.as_view(), name='project_members_list'),
    path('project_members/<int:pk>/', ProjectMembersDetail.as_view(), name='project_members_detail'),
    path('<int:project_id>/members/', ProjectMembersListByProjectView.as_view(), name='project_members_by_project'),
    path('<int:project_id>/members_view/', ProjectMembersViewListByProjectView.as_view(), name='project_members_by_project_member_view'),
    path('<int:project_id>/boards/', TaskBoardListByProjectView.as_view(), name='task_board_by_project'),
    path('my_projects/', MyProjectsView.as_view(), name='my_projects'),
    path('my_projects/<int:project_id>/', MyProjectDetailView.as_view(), name='my_project_detail'),

    # Project Notes
    path('<int:project_id>/notes/', ProjectNoteListCreateView.as_view(), name='project_notes_list_create'),
    path('<int:project_id>/notes/<int:note_id>/', ProjectNoteDetailView.as_view(), name='project_notes_detail'),
    path('projects/<int:project_id>/notes/', ProjectNoteListCreateView.as_view(), name='project_notes_list_create_alt'),
    path('projects/<int:project_id>/notes/<int:note_id>/', ProjectNoteDetailView.as_view(), name='project_notes_detail_alt'),
    path("meetings/<int:meeting_id>/tasks/", MeetingTaskListCreateView.as_view(), name="meeting_tasks"),
    path("meetings/<int:meeting_id>/attendance/", MeetingAttendanceView.as_view(), name="meeting_attendance"),



    # Tasks
    path('task/board/', CreateListBoard.as_view(), name='task_board_list'),
    path('task/board/<int:pk>/', DistroyUpdateBoard.as_view(), name='task_board_detail'),

    path('myprojects/board/', ListBoardMember.as_view(), name='myprojects_board_list'),

    path('task/column/', CreateStatusColumn.as_view(), name='status_column_list'),
    path('task/column/<int:pk>/', DistroyUpdateStatusColumn.as_view(), name='status_column_detail'),
    
    path('task/', TaskListCreateView.as_view(), name='task_list'),
    path('task/<int:pk>/', TaskRetrieveUpdateDeleteView.as_view(), name='task_detail'),
    path('task/myprojects/', MyProjectTaskListView.as_view()),
    path('task/myprojects/<int:task_id>/', MyProjectTaskListView.as_view()),
        
    path('task/<int:member_id>/members/', TaskListByMembers.as_view(), name='task_by_members'),
    path('task/<int:project_member_id>/project_members/', TaskListByProjectMember.as_view(), name='task_by_project_members'),

    # Search
    path('search/', ProjectSearchView.as_view(), name='project_search'),
    path('project_members/<int:project_id>/search/', ProjectMembersSearchView.as_view(), name='project_members_search'),
    path('members/search/', MembersSearchView.as_view(), name='members_search'),
    path('task/<int:project_member_id>/project_members/search/', TaskSearchByProjectMembersView.as_view(), name='task_search_by_project_members'),
    path('task/<int:member_id>/members/search/', TaskSearchByMembersView.as_view(), name='task_search_by_members'),

    # Employee Report
    path('report/prefill/', ReportPrefillView.as_view(), name='project_report_prefill'),
    path('report/', ReportView.as_view(), name='project_report'),
    path('report/<int:id>/', ReportView.as_view(), name='project_report_detail'), # RETRIVE/CREATE/UPDATE
    
    path('manager/report/', ReportListManagerView.as_view(), name='manager_report_list'),
    path('manager/report/<int:id>/', ReportManagerDetailView.as_view(), name='manager_report'),
    path('manager/daily_report_summary/', ManagerDailyReportSummaryView.as_view(), name='manager_daily_report_summary'),
    path('manager/weekly_report_summary/', ManagerWeeklyReportSummaryView.as_view(), name='manager_weekly_report_summary'),
    path('manager/monthly_report_summary/', ManagerMonthlyReportSummaryView.as_view(), name='manager_monthly_report_summary'),
    path('manager/staff_reports/', ManagerStaffReportsConsolidatedView.as_view(), name='manager_staff_reports_consolidated'),


    #Dashaboard
    path('dashboard/', ProjectManagerDashboardView.as_view(), name='dashboard'),

    # Reports
    path('reports/project/', ProjectReportView.as_view(), name='project_report'),
    path('reports/project-timeline/<int:id>/', ProjectTimelineReportView.as_view(), name='project_report_timeline'),
    path('reports/contract/', ContractReportView.as_view(), name='project_contract_report'),
    
    # Number Generator
    path('generate-number/', NumberGeneratorView.as_view(), name='generate_project_contract_number'),


    # Testing
    path('bug-sheet/', BugSheetListCreateAPIView.as_view(), name='bug-sheet'),
    path('bug-sheet/<int:bug_id>/', BugReportDetailAPIView.as_view(), name='bug-report-detail'),
    path('bug-sheet/<int:bug_id>/status/', BugStatusUpdateAPIView.as_view(), name='bug-status-update'),

    # Pending Controls / Works Dashboards (3 Dedicated APIs)
    path('pending-dashboard/', ProjectManagementPendingDashboardAPIView.as_view(), name='project_management_pending_dashboard'),
    path('pending-works/', ProjectManagementPendingDashboardAPIView.as_view(), name='project_management_pending_works'),
    
    path('digital-marketing/pending-dashboard/', DigitalMarketingPendingDashboardAPIView.as_view(), name='dm_pending_dashboard'),
    path('dm/pending-dashboard/', DigitalMarketingPendingDashboardAPIView.as_view(), name='dm_pending_dashboard_alias'),
    path('dm/pending-works/', DigitalMarketingPendingDashboardAPIView.as_view(), name='dm_pending_works'),

    path('testing/pending-dashboard/', TestingManagementPendingDashboardAPIView.as_view(), name='testing_pending_dashboard'),
    path('testing/pending-works/', TestingManagementPendingDashboardAPIView.as_view(), name='testing_pending_works'),
]
