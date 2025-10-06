from django.urls import path
from .views import DailyAttendanceListView, DailyAttendanceTodayView, DailyAttendanceDetailView, DailyAttendanceEmployeeView, StaffAttendanceTodayView,DailyAttendanceDaysCountView, DailyAttendanceSessionView

urlpatterns = [
    path('', DailyAttendanceListView.as_view(), name='attendance-list'),
    path('today/', DailyAttendanceTodayView.as_view(), name='attendance-today'),
    path('<int:id>/', DailyAttendanceDetailView.as_view(), name='attendance-detail'),

    path('employee/<int:id>/', DailyAttendanceEmployeeView.as_view(), name='attendance-employee'),
    path('employee/<int:id>/days-count/', DailyAttendanceDaysCountView.as_view(), name='attendance-employee-days-count'),
    path('employee/<int:id>/sessions/', DailyAttendanceSessionView.as_view(), name='attendance-employee-sessions'),

    path('today/staff/',StaffAttendanceTodayView.as_view(), name='staff-attendance-today'),
]
