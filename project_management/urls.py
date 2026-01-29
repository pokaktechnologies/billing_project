from django.urls import path
from .views import *

urlpatterns = [
    # Client contract
    path('client_contract/', ClientContractView.as_view(), name='client_contract_list'),
    path('client_contract/<int:pk>/', ClientContractDetailView.as_view(), name='client_contract_detail'),

    # Project management
    path('', project_management.as_view(), name='project_management'),
    path('<int:pk>/', project_management_detail.as_view(), name='project_management_detail'),

    # Members
    path('members/', MembersView.as_view(), name='members_list'),
    path('members/<int:pk>/', MembersViewDetail.as_view(), name='members_detail'),

    # Stack
    path('stack/', StackView.as_view(), name='stack_list'),
    path('stack/<int:pk>/', StackViewDetail.as_view(), name='stack_detail'),


    # Project members
    path('project_members/', ProjectMembersView.as_view(), name='project_members_list'),
    path('project_members/<int:pk>/', ProjectMembersDetail.as_view(), name='project_members_detail'),
    path('<int:project_id>/members/', ProjectMembersListByProjectView.as_view(), name='project_members_by_project'),


    # Tasks
    path('task/board/', CreateListBoard.as_view(), name='task_board_list'),
    path('task/board/<int:pk>/', DistroyUpdateBoard.as_view(), name='task_board_detail'),

    path('task/column/', CreateStatusColumn.as_view(), name='status_column_list'),
    path('task/column/<int:pk>/', DistroyUpdateStatusColumn.as_view(), name='status_column_detail'),
    
    path('task/', TaskListCreateView.as_view(), name='task_list'),
    path('task/<int:pk>/', TaskRetrieveUpdateDeleteView.as_view(), name='task_detail'),
    
    path('task/<int:member_id>/members/', TaskListByMembers.as_view(), name='task_by_members'),
    path('task/<int:project_member_id>/project_members/', TaskListByProjectMember.as_view(), name='task_by_project_members'),

    # Search
    path('search/', ProjectSearchView.as_view(), name='project_search'),
    path('project_members/<int:project_id>/search/', ProjectMemebrsSearchView.as_view(), name='project_members_search'),
    path('members/search/', MembersSearchView.as_view(), name='members_search'),
    path('task/<int:project_member_id>/project_members/search/', TaskSearchByProjectMembersView.as_view(), name='task_search_by_project_members'),
    path('task/<int:member_id>/members/search/', TaskSearchByMembersView.as_view(), name='task_search_by_members'),

    # Report
    path('report/', ReportView.as_view(), name='project_report'),
    path('report/<int:id>/', ReportView.as_view(), name='project_report_detail'), # RETRIVE/CREATE/UPDATE
    
    path('manager/report/', ReportListManagerView.as_view(), name='manager_report_list'),
    path('manager/report/<int:id>/', ReportManagerDetailView.as_view(), name='manager_report'),
    path('manager/weekly_report_summary/', ManagerWeeklyReportSummaryView.as_view(), name='manager_weekly_report_summary'),

    #Dashaboard
    path('dashboard/', ProjectManagerDashboardView.as_view(), name='dashboard'),
]
