from django.urls import path
from .views import *

urlpatterns = [
    path('',project_management.as_view(), name='project_management'),
    path('<int:pk>/', project_management_detail.as_view(), name='project_management_detail'),
    path('members/', MembersView.as_view(), name='project_members'),
    path('members/<int:pk>/', MembersViewDetail.as_view(), name='project_members_detail'),
    path('<int:project_id>/members/', ProjectMembersListByProjectView.as_view(), name='project_members_list_by_project'),
    path('stack/', StackView.as_view(), name='project_stacks'),
    path('stack/<int:pk>/', StackViewDetail.as_view(), name='project_stack_detail'),
    path('project_members/', ProjectMembersView.as_view(), name='project_members'),
    path('project_members/<int:pk>/', ProjectMembersDetail.as_view(), name='project_members_detail'),
    path('task/', TaskView.as_view(), name='tasks'),
    path('task/<int:pk>/', TaskDetail.as_view(), name='task_detail'),
    path('task/<int:member_id>/members/', TaskListByMembers.as_view(), name='task_list_by_members'),
    path('task/<int:project_member_id>/project_members/', TaskListByProjectMember.as_view(), name='task_list_by_project_member'),

    path('search/', ProjectSearchView.as_view(), name='project_search'),
    path('project_members/search/', ProjectMemebrsSearchView.as_view(), name='member_search'),
    path('members/search/', MembersSearchView.as_view(), name='members_search'),
]