from rest_framework import serializers
from ..models import Payroll, AttendanceSummary, PayrollPeriod
from accounts.serializers.user import StaffProfileSerializer
from .payroll_period import PayrollPeriodSerializer

class AttendanceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSummary
        fields = [
            'id', 'working_days', 'full_days', 'half_days', 
            'leave_days', 'absent_days', 'created_at'
        ]

class PayrollListSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    staff_email = serializers.EmailField(source='staff.user.email', read_only=True)
    department = serializers.CharField(source='staff.job_detail.department.name', read_only=True)
    role = serializers.CharField(source='staff.job_detail.role', read_only=True)
    period_month = serializers.CharField(source='period.month', read_only=True)
    attendance_summary = serializers.SerializerMethodField()
    employee_id = serializers.CharField(source='staff.job_detail.employee_id', read_only=True)

    class Meta:
        model = Payroll
        fields = "__all__"

    def get_staff_name(self, obj):
        return obj.staff.user.get_full_name()

    def get_attendance_summary(self, obj):
        summary = obj.attendance_summary
        if summary:
            return AttendanceSummarySerializer(summary).data
        return None
    

class PayrollDetailSerializer(serializers.ModelSerializer):
    staff_details = StaffProfileSerializer(source='staff', read_only=True)
    period_details = PayrollPeriodSerializer(source='period', read_only=True)
    attendance_summary = serializers.SerializerMethodField()

    class Meta:
        model = Payroll
        fields = "__all__"

    def get_attendance_summary(self, obj):
        summary = obj.attendance_summary
        if summary:
            return AttendanceSummarySerializer(summary).data
        return None
