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


from .models import Account

class AccountFilter(django_filters.FilterSet):
    # parent=id: only list the children of this parent
    parent = django_filters.NumberFilter(field_name='parent_account__id')
    
    # another parent for only listing the parents (Level 2/Roots, where parent is null)
    # usage: ?parent_only=true
    parent_only = django_filters.BooleanFilter(method='filter_parent_only')

    # filter by posting accounts only (or not)
    is_posting = django_filters.BooleanFilter(field_name='is_posting')
    
    # Standard fields
    type = django_filters.ChoiceFilter(choices=Account.ACCOUNT_TYPES)
    status = django_filters.ChoiceFilter(choices=Account.STATUS_CHOICES)
    account_number = django_filters.CharFilter(lookup_expr='exact')
    name = django_filters.CharFilter(lookup_expr='icontains')
    
    # Range filters for numeric/date fields
    opening_balance_min = django_filters.NumberFilter(field_name='opening_balance', lookup_expr='gte')
    opening_balance_max = django_filters.NumberFilter(field_name='opening_balance', lookup_expr='lte')
    
    created_at__after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_at__before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Account
        fields = [
            'parent', 'is_posting', 'type', 'status', 
            'account_number', 'name', 'opening_balance',
            'created_at__after', 'created_at__before'
        ]

    def filter_parent_only(self, queryset, name, value):
        if value:
            # Return only accounts that have NO parent (Roots)
            return queryset.filter(parent_account__isnull=True)
        return queryset
