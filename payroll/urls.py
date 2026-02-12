from .views import (
    PayrollPeriodListView, PayrollPeriodDetailView, 
    GenerateBulkStaffPayrollView, ResetStaffPayrollView,
    PayrollListView, PayrollDetailView, MyPayrollListView
)
from django.urls import path

urlpatterns = [
    path('periods/', PayrollPeriodListView.as_view(), name='payroll-period-list'),
    path('periods/<int:pk>/', PayrollPeriodDetailView.as_view(), name='payroll-period-detail'),
    path('generate-bulk/', GenerateBulkStaffPayrollView.as_view(), name='payroll-generate-bulk'),
    path('reset-staff/', ResetStaffPayrollView.as_view(), name='payroll-reset-staff'),
    path('me/', MyPayrollListView.as_view(), name='my-payroll-list'),
    path('', PayrollListView.as_view(), name='payroll-list'),
    path('<int:pk>/', PayrollDetailView.as_view(), name='payroll-detail'),
]
