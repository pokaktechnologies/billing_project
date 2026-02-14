from rest_framework import serializers
from ..models import Payroll, AttendanceSummary
from accounts.models import StaffProfile

class PayslipStaffSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    employee_id = serializers.CharField(source='job_detail.employee_id', read_only=True)
    department = serializers.CharField(source='job_detail.department.name', read_only=True)
    role = serializers.CharField(source='job_detail.role', read_only=True)
    job_type = serializers.CharField(source='job_detail.job_type', read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'first_name', 'last_name', 'email', 
            'employee_id', 'department', 'role', 'job_type',
            'phone_number', 'address'
        ]

class PayslipAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSummary
        fields = [
            'working_days', 'full_days', 'half_days', 
            'leave_days', 'absent_days'
        ]

class EmployeePayslipSerializer(serializers.ModelSerializer):
    staff_details = PayslipStaffSerializer(source='staff', read_only=True)
    attendance_summary = serializers.SerializerMethodField()
    period_month = serializers.CharField(source='period.month', read_only=True)

    class Meta:
        model = Payroll
        fields = [
            'id', 'staff_details', 'period_month', 'gross_salary',
            'working_days', 'paid_leave_used', 'unpaid_leave_days',
            'deduction', 'net_salary', 'status', 'created_at',
            'attendance_summary'
        ]

    def get_attendance_summary(self, obj):
        summary = obj.attendance_summary
        if summary:
            return PayslipAttendanceSerializer(summary).data
        return None
