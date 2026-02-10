from django.urls import path
from .views import *

urlpatterns = [
    path('', DailyAttendanceListView.as_view(), name='attendance-list'),
    path('today/', DailyAttendanceTodayView.as_view(), name='attendance-today'),
    path('<int:id>/', DailyAttendanceDetailView.as_view(), name='attendance-detail'),

    path('employee/<int:id>/', DailyAttendanceEmployeeView.as_view(), name='attendance-employee'),
    path('employee/<int:id>/days-count/', DailyAttendanceDaysCountView.as_view(), name='attendance-employee-days-count'),
    path('employee/<int:id>/sessions/', DailyAttendanceSessionView.as_view(), name='attendance-employee-sessions'),

    path('today/staff/',StaffAttendanceTodayView.as_view(), name='staff-attendance-today'),
    path('staff-wise-attendance-stats/',StaffWiseAttendanceStats.as_view(), name='staff-wise-attendance-stats'),
    path('all-staff-wise-attendance-stats/',AllStaffWiseAttendanceStats.as_view(), name='all-staff-wise-attendance-stats'),

    # Holiday CRUD
    path('holidays/', HolidayViewSet.as_view({'get': 'list', 'post': 'create'}), name='holiday-list-create'),
    path('holidays/<int:pk>/', HolidayViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='holiday-detail'),

    # Leave Request (Employee)
    path('leave-requests/', EmployeeLeaveRequestView.as_view(), name='employee-leave-request-list'),
    path('leave-requests/<int:pk>/', EmployeeLeaveRequestDetailView.as_view(), name='employee-leave-request-detail'),

    # HR Leave Report (Admin)
    path('hr/leave-requests/', HrLeaveRequestListCreateView.as_view(), name='hr-leave-request-list-create'),
    path('hr/leave-requests/<int:pk>/', HrLeaveRequestDetailView.as_view(), name='hr-leave-request-detail'),
]
