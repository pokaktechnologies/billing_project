import django_filters
from .models import JournalLine

class JournalLineFlatFilter(django_filters.FilterSet):
    # ----- Date range filters -----
    from_date = django_filters.DateFilter(
        field_name='journal__date', lookup_expr='gte', label='From Date'
    )
    to_date = django_filters.DateFilter(
        field_name='journal__date', lookup_expr='lte', label='To Date'
    )

    # ----- Select filters -----
    salesperson = django_filters.NumberFilter(
        field_name='journal__salesperson__id', lookup_expr='exact', label='Salesperson'
    )
    entry_type = django_filters.CharFilter(
        field_name='journal__type', lookup_expr='exact', label='Entry Type'
    )
    account = django_filters.NumberFilter(
        field_name='account__id', lookup_expr='exact', label='Account'
    )

    class Meta:
        model = JournalLine
        fields = ['from_date', 'to_date', 'salesperson', 'entry_type', 'account']
