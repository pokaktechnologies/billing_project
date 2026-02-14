from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from ..models import Payroll
from ..serializers.payroll import PayrollListSerializer, PayrollDetailSerializer
from ..filters import PayrollFilter
from ..pagination import OptionalPagination
from ..services import bulk_mark_payroll_as_paid

class PayrollListView(generics.ListAPIView):
    """
    GET → List all payroll records with summary staff/period info.
    Supports filtering by staff, employee_id, email, name, department, period, status, date range, and salary range.
    """
    queryset = Payroll.objects.all().select_related(
        'staff__user', 'staff__job_detail', 'staff__job_detail__department', 'period'
    ).order_by('-created_at')
    serializer_class = PayrollListSerializer
    pagination_class = OptionalPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PayrollFilter
    search_fields = [
        'staff__user__first_name', 'staff__user__last_name', 
        'staff__user__email', 'staff__job_detail__employee_id'
    ]
    ordering_fields = ['gross_salary', 'net_salary', 'created_at', 'working_days']

class PayrollDetailView(generics.RetrieveAPIView):
    """
    GET → Retrieve a detailed payroll record including staff, period, and attendance summary.
    """
    queryset = Payroll.objects.all()
    serializer_class = PayrollDetailSerializer

class MyPayrollListView(generics.ListAPIView):
    """
    GET → List only the logged-in staff member's payroll records.
    """
    serializer_class = PayrollListSerializer
    pagination_class = OptionalPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PayrollFilter
    search_fields = ['period__month', 'status']
    ordering_fields = ['gross_salary', 'net_salary', 'created_at']

    def get_queryset(self):
        return Payroll.objects.filter(staff__user=self.request.user).select_related(
            'staff__user', 'staff__job_detail', 'period'
        ).order_by('-created_at')

class BulkPayrollPayView(APIView):
    """
    POST → Bulk mark multiple payroll records as Paid.
    Body: {"payroll_ids": [1, 2, 3]}
    """
    def post(self, request, *args, **kwargs):
        payroll_ids = request.data.get('payroll_ids', [])
        if not payroll_ids or not isinstance(payroll_ids, list):
            return Response(
                {"success": False, "error": "A list of payroll_ids is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = bulk_mark_payroll_as_paid(payroll_ids)
        if not result.get('success', False):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(result, status=status.HTTP_200_OK)
