from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.utils import timezone
import django_filters

from .models import Payroll


def _normalize_year_month(value):
    """Normalize 'YYYY-MM' or 'YYYY-M' strings to 'YYYY-MM', or return None if invalid."""
    if not value or not isinstance(value, str):
        return None
    parts = value.strip().split("-")
    if len(parts) != 2:
        return None
    year_part, month_part = parts[0].strip(), parts[1].strip()
    if len(year_part) != 4 or not year_part.isdigit() or not month_part.isdigit():
        return None
    month_num = int(month_part)
    if not 1 <= month_num <= 12:
        return None
    return f"{year_part}-{month_num:02d}"


def _filter_period_month(queryset, lookup, value):
    """Filter by period.month, falling back to Payroll.month when period is NULL."""
    return queryset.filter(
        Q(**{f"period__month__{lookup}": value})
        | Q(period__isnull=True, **{f"month__{lookup}": value})
    )


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
    period_id = django_filters.NumberFilter(field_name='period_id')

    # Status filter (supports paid, draft, all, case-insensitive)
    status = django_filters.CharFilter(method='filter_by_status')

    # Date range filters
    start_date = django_filters.DateFilter(field_name='created_at__date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='created_at__date', lookup_expr='lte')

    # Salary range filters
    min_salary = django_filters.NumberFilter(field_name='net_salary', lookup_expr='gte')
    max_salary = django_filters.NumberFilter(field_name='net_salary', lookup_expr='lte')

    class Meta:
        model = Payroll
        fields = ['staff', 'period', 'status', 'month']

    def filter_by_staff_name(self, queryset, name, value):
        value = (value or '').strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(staff__user__first_name__icontains=value)
            | Q(staff__user__last_name__icontains=value)
        )

    def filter_by_status(self, queryset, name, value):
        val = (value or '').strip().lower()
        if val in ('', 'all'):
            return queryset
        return queryset.filter(status__iexact=val)


class SalaryStatementFilter(PayrollFilter):
    DURATION_MONTHS = {
        '1m': 1,
        '3m': 3,
        '6m': 6,
        '9m': 9,
        '12m': 12,
    }
    EXPLICIT_PERIOD_PARAMS = (
        'start_month',
        'end_month',
        'start_date',
        'end_date',
        'year',
        'month',
        'period_month',
    )

    year = django_filters.CharFilter(method='filter_year')
    month = django_filters.CharFilter(method='filter_month')
    period_month = django_filters.CharFilter(method='filter_period_month')
    start_month = django_filters.CharFilter(method='filter_start_month')
    end_month = django_filters.CharFilter(method='filter_end_month')
    start_date = django_filters.DateFilter(method='filter_start_date')
    end_date = django_filters.DateFilter(method='filter_end_date')
    duration = django_filters.CharFilter(method='filter_duration')

    class Meta(PayrollFilter.Meta):
        model = Payroll
        fields = ['staff', 'period', 'status']

    def filter_year(self, queryset, name, value):
        val = (value or '').strip()
        if not val:
            return queryset
        if len(val) == 4 and val.isdigit():
            return _filter_period_month(queryset, 'startswith', f'{val}-')
        return queryset.none()

    def filter_month(self, queryset, name, value):
        val = (value or '').strip()
        if not val:
            return queryset
        if '-' in val:
            normalized = _normalize_year_month(val)
            if not normalized:
                return queryset.none()
            return _filter_period_month(queryset, 'exact', normalized)
        if val.isdigit():
            month_num = int(val)
            if 1 <= month_num <= 12:
                month_str = f'{month_num:02d}'
                year_param = (self.data.get('year') or '').strip()
                if len(year_param) == 4 and year_param.isdigit():
                    return _filter_period_month(queryset, 'exact', f'{year_param}-{month_str}')
                return _filter_period_month(queryset, 'endswith', f'-{month_str}')
        return queryset.none()

    def filter_period_month(self, queryset, name, value):
        val = (value or '').strip()
        if not val:
            return queryset
        normalized = _normalize_year_month(val)
        if not normalized:
            return queryset.none()
        return _filter_period_month(queryset, 'exact', normalized)

    def filter_start_month(self, queryset, name, value):
        val = (value or '').strip()
        if not val:
            return queryset
        normalized = _normalize_year_month(val)
        if not normalized:
            return queryset.none()
        return _filter_period_month(queryset, 'gte', normalized)

    def filter_end_month(self, queryset, name, value):
        val = (value or '').strip()
        if not val:
            return queryset
        normalized = _normalize_year_month(val)
        if not normalized:
            return queryset.none()
        return _filter_period_month(queryset, 'lte', normalized)

    def filter_start_date(self, queryset, name, value):
        if not value:
            return queryset
        return _filter_period_month(queryset, 'gte', value.strftime('%Y-%m'))

    def filter_end_date(self, queryset, name, value):
        if not value:
            return queryset
        return _filter_period_month(queryset, 'lte', value.strftime('%Y-%m'))

    def filter_duration(self, queryset, name, value):
        val = (value or '').strip().lower()
        if val in ('', 'all'):
            return queryset
        if any((self.data.get(param) or '').strip() for param in self.EXPLICIT_PERIOD_PARAMS):
            return queryset
        months = self.DURATION_MONTHS.get(val)
        if not months:
            return queryset.none()
        today = timezone.localdate()
        current_month_start = today.replace(day=1)
        start_date = current_month_start - relativedelta(months=months)
        start_month_str = start_date.strftime('%Y-%m')
        return _filter_period_month(queryset, 'gte', start_month_str)
