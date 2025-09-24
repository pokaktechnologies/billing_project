from django.urls import path
from .views import DailyAttendanceListView, DailyAttendanceTodayView, DailyAttendanceDetailView

urlpatterns = [
    path('', DailyAttendanceListView.as_view(), name='attendance-list'),
    path('today/', DailyAttendanceTodayView.as_view(), name='attendance-today'),
    path('<int:id>/', DailyAttendanceDetailView.as_view(), name='attendance-detail'),
]
