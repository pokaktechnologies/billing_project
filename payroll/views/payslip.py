from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from ..models import Payroll
from ..serializers.payslip import EmployeePayslipSerializer

class EmployeePayslipView(APIView):
    """
    GET → Retrieve a detailed payslip for an employee for a specific period.
    Query parameters:
    - staff_id: ID of the staff
    - period_id: ID of the payroll period
    OR
    - month: Month in YYYY-MM format
    """
    def get(self, request, *args, **kwargs):
        staff_id = request.query_params.get('staff_id')
        period_id = request.query_params.get('period_id')
        month = request.query_params.get('month')

        if not staff_id:
            return Response(
                {"success": False, "error": "staff_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build query
        query_params = {'staff_id': staff_id}
        if period_id:
            query_params['period_id'] = period_id
        elif month:
            query_params['period__month'] = month
        else:
            return Response(
                {"success": False, "error": "Either period_id or month query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        payroll = Payroll.objects.filter(**query_params).select_related(
            'staff__user', 'staff__job_detail', 'staff__job_detail__department', 'period'
        ).first()

        if not payroll:
            return Response(
                {"success": False, "error": "No payslip found for the specified staff and period."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EmployeePayslipSerializer(payroll)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
