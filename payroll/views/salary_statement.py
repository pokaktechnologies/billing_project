from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from ..models import Payroll
from ..serializers.salary_statement import SalaryStatementSerializer
from ..filters import PayrollFilter
from ..pagination import OptionalPagination

class SalaryStatementListView(generics.ListAPIView):
    """
    GET → List salary statements with advanced duration filters.
    Query parameters:
    - duration: 1m, 3m, 6m, 9m, 12m (default: all)
    - Standard filters (staff_id, department, status, etc.) from PayrollFilter
    """
    queryset = Payroll.objects.all().select_related(
        'staff__user', 'staff__job_detail', 'staff__job_detail__department', 'period'
    ).order_by('-period__month')
    serializer_class = SalaryStatementSerializer
    pagination_class = OptionalPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PayrollFilter
    search_fields = [
        'staff__user__first_name', 'staff__user__last_name', 
        'staff__user__email', 'staff__job_detail__employee_id'
    ]
    ordering_fields = ['gross_salary', 'net_salary', 'created_at', 'period__month']

    def get_queryset(self):
        staff_id = self.kwargs.get('staff_id')
        queryset = super().get_queryset().filter(staff_id=staff_id)
        
        duration = self.request.query_params.get('duration')
        start_month = self.request.query_params.get('start_month')
        end_month = self.request.query_params.get('end_month')
        
        if start_month:
            queryset = queryset.filter(period__month__gte=start_month)
        if end_month:
            queryset = queryset.filter(period__month__lte=end_month)
            
        if duration and not (start_month or end_month):
            months = 0
            if duration == '1m': months = 1
            elif duration == '3m': months = 3
            elif duration == '6m': months = 6
            elif duration == '9m': months = 9
            elif duration == '12m': months = 12
            
            if months > 0:
                today = timezone.localdate()
                current_month_start = today.replace(day=1)
                start_date = current_month_start - relativedelta(months=months)
                start_month_str = start_date.strftime('%Y-%m')
                queryset = queryset.filter(period__month__gte=start_month_str)
        
        return queryset
