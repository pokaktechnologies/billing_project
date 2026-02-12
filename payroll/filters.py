import django_filters
from .models import Payroll
from accounts.models import Department

class PayrollFilter(django_filters.FilterSet):
    # Staff filters
    staff_email = django_filters.CharFilter(field_name='staff__user__email', lookup_expr='icontains')
    staff_name = django_filters.CharFilter(method='filter_by_staff_name')
    employee_id = django_filters.CharFilter(field_name='staff__job_detail__employee_id', lookup_expr='icontains')
    
    # Staff job filters
    department = django_filters.NumberFilter(field_name='staff__job_detail__department_id')
    job_type = django_filters.CharFilter(field_name='staff__job_detail__job_type')
    
    # Period filters
    period_month = django_filters.CharFilter(field_name='period__month')
    
    # Date range filters
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    # Salary range filters
    min_salary = django_filters.NumberFilter(field_name='net_salary', lookup_expr='gte')
    max_salary = django_filters.NumberFilter(field_name='net_salary', lookup_expr='lte')

    class Meta:
        model = Payroll
        fields = ['staff', 'period', 'status', 'month']

    def filter_by_staff_name(self, queryset, name, value):
        return queryset.filter(
            django_filters.db.models.Q(staff__user__first_name__icontains=value) |
            django_filters.db.models.Q(staff__user__last_name__icontains=value)
        )
