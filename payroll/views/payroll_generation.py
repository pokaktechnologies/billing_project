from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from ..services import process_bulk_staff_payroll, reset_staff_payroll
from ..serializers.payroll_generation import (
    BulkStaffPayrollRequestSerializer, 
    BulkStaffPayrollResponseSerializer,
    ResetStaffPayrollSerializer
)

class GenerateBulkStaffPayrollView(APIView):
    """
    POST → In one transaction:
      - Create AttendanceSummary
      - Create Payroll
      - Update PayrollMonth
    """
    def post(self, request):
        request_serializer = BulkStaffPayrollRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        staff_ids = request_serializer.validated_data['staff_ids']
        period_id = request_serializer.validated_data['period_id']
        
        result = process_bulk_staff_payroll(staff_ids, period_id)
        
        if result['success']:
            response_serializer = BulkStaffPayrollResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": result['error']}, status=status.HTTP_400_BAD_REQUEST)

class ResetStaffPayrollView(APIView):
    """
    POST → Reset payroll and attendance for a specific staff and period.
    """
    def post(self, request):
        serializer = ResetStaffPayrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        staff_id = serializer.validated_data['staff_id']
        period_id = serializer.validated_data['period_id']
        generate_now = serializer.validated_data.get('generate_now', False)
        
        result = reset_staff_payroll(staff_id, period_id)
        
        if result['success']:
            if generate_now:
                # Regenerate payroll for this staff member
                gen_result = process_bulk_staff_payroll([staff_id], period_id)
                if gen_result['success']:
                    # Use the response serializer for consistent output
                    response_serializer = BulkStaffPayrollResponseSerializer(gen_result)
                    return Response({
                        "reset": result,
                        "generation": response_serializer.data
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "reset": result,
                        "generation_error": gen_result['error']
                    }, status=status.HTTP_207_MULTI_STATUS)
            
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({"error": result['error']}, status=status.HTTP_400_BAD_REQUEST)
