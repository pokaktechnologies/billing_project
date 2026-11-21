from rest_framework import serializers
from ..models import Payroll, AttendanceSummary
from accounts.models import StaffProfile


class StatementStaffSerializer(serializers.ModelSerializer):
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


class StatementAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSummary
        fields = [
            'working_days', 'full_days', 'half_days',
            'leave_days', 'absent_days'
        ]


class SalaryStatementSerializer(serializers.ModelSerializer):
    staff_details = StatementStaffSerializer(source='staff', read_only=True)
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
        attendance_map = self.context.get('attendance_map')
        if attendance_map is not None:
            summary = attendance_map.get((obj.staff_id, obj.period_id))
        else:
            summary = obj.attendance_summary
        if summary:
            return StatementAttendanceSerializer(summary).data
        return None


class SalaryStatementSummarySerializer(serializers.Serializer):
    """One-line aggregated salary statement row per staff member."""

    staff_id = serializers.IntegerField()
    employee_id = serializers.CharField(source='staff__job_detail__employee_id', allow_null=True)
    staff_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='staff__user__email')
    phone_number = serializers.CharField(source='staff__phone_number', allow_null=True)
    department = serializers.CharField(source='staff__job_detail__department__name', allow_null=True)
    role = serializers.CharField(source='staff__job_detail__role', allow_null=True)
    job_type = serializers.CharField(source='staff__job_detail__job_type', allow_null=True)
    period = serializers.SerializerMethodField()
    months_count = serializers.IntegerField()
    payroll_id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    paid_months = serializers.IntegerField()
    draft_months = serializers.IntegerField()
    working_days = serializers.IntegerField(source='working_days_total')
    total_working_hours = serializers.DecimalField(
        source='total_working_hours_sum', max_digits=10, decimal_places=2
    )
    paid_leave_used = serializers.IntegerField(source='paid_leave_used_total')
    unpaid_leave_days = serializers.DecimalField(
        source='unpaid_leave_days_total', max_digits=8, decimal_places=2
    )
    gross_salary = serializers.DecimalField(
        source='gross_salary_total', max_digits=12, decimal_places=2
    )
    deduction = serializers.DecimalField(
        source='deduction_total', max_digits=12, decimal_places=2
    )
    net_salary = serializers.DecimalField(
        source='net_salary_total', max_digits=12, decimal_places=2
    )
    full_days = serializers.SerializerMethodField()
    half_days = serializers.SerializerMethodField()
    leave_days = serializers.SerializerMethodField()
    absent_days = serializers.SerializerMethodField()
    latest_created_at = serializers.DateTimeField()

    def get_staff_name(self, obj):
        first = obj.get('staff__user__first_name') or ''
        last = obj.get('staff__user__last_name') or ''
        return f'{first} {last}'.strip()

    def get_period(self, obj):
        earliest = obj.get('earliest_period')
        latest = obj.get('latest_period')
        if obj.get('months_count') == 1 or earliest == latest:
            return latest
        if earliest and latest:
            return f'{earliest} to {latest}'
        return latest or earliest

    def get_payroll_id(self, obj):
        if obj.get('months_count') == 1:
            return obj.get('latest_payroll_id')
        return None

    def get_status(self, obj):
        paid = obj.get('paid_months') or 0
        draft = obj.get('draft_months') or 0
        if draft == 0 and paid > 0:
            return 'Paid'
        if paid == 0 and draft > 0:
            return 'Draft'
        if paid > 0 and draft > 0:
            return 'Partial'
        return None

    def _get_attendance_field(self, obj, field_name):
        attendance_totals = self.context.get('attendance_totals') or {}
        return attendance_totals.get(obj['staff_id'], {}).get(field_name, 0)

    def get_full_days(self, obj):
        return self._get_attendance_field(obj, 'full_days')

    def get_half_days(self, obj):
        return self._get_attendance_field(obj, 'half_days')

    def get_leave_days(self, obj):
        return self._get_attendance_field(obj, 'leave_days')

    def get_absent_days(self, obj):
        return self._get_attendance_field(obj, 'absent_days')


class FlatSalaryStatementSerializer(serializers.ModelSerializer):
    """One-line flat salary statement row per (staff, period) payroll record."""

    payroll_id = serializers.IntegerField(source='id', read_only=True)
    staff_id = serializers.IntegerField(read_only=True)
    employee_id = serializers.SerializerMethodField()
    staff_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='staff.user.email', read_only=True)
    phone_number = serializers.CharField(
        source='staff.phone_number', allow_null=True, read_only=True
    )
    department = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    job_type = serializers.SerializerMethodField()
    period_month = serializers.SerializerMethodField()
    full_days = serializers.SerializerMethodField()
    half_days = serializers.SerializerMethodField()
    leave_days = serializers.SerializerMethodField()
    absent_days = serializers.SerializerMethodField()

    class Meta:
        model = Payroll
        fields = [
            'payroll_id',
            'staff_id',
            'employee_id',
            'staff_name',
            'email',
            'phone_number',
            'department',
            'role',
            'job_type',
            'period_month',
            'working_days',
            'total_working_hours',
            'paid_leave_used',
            'unpaid_leave_days',
            'gross_salary',
            'deduction',
            'net_salary',
            'status',
            'full_days',
            'half_days',
            'leave_days',
            'absent_days',
            'created_at',
        ]

    def _get_job_detail(self, obj):
        return getattr(obj.staff, 'job_detail', None)

    def _get_attendance(self, obj):
        attendance_map = self.context.get('attendance_map')
        if attendance_map is not None:
            return attendance_map.get((obj.staff_id, obj.period_id))
        return obj.attendance_summary

    def get_employee_id(self, obj):
        job = self._get_job_detail(obj)
        return job.employee_id if job else None

    def get_staff_name(self, obj):
        return obj.staff.user.get_full_name()

    def get_department(self, obj):
        job = self._get_job_detail(obj)
        return job.department.name if (job and job.department) else None

    def get_role(self, obj):
        job = self._get_job_detail(obj)
        return job.role if job else None

    def get_job_type(self, obj):
        job = self._get_job_detail(obj)
        return job.job_type if job else None

    def get_period_month(self, obj):
        return obj.period.month if obj.period else obj.month

    def get_full_days(self, obj):
        summary = self._get_attendance(obj)
        return summary.full_days if summary else None

    def get_half_days(self, obj):
        summary = self._get_attendance(obj)
        return summary.half_days if summary else None

    def get_leave_days(self, obj):
        summary = self._get_attendance(obj)
        return summary.leave_days if summary else None

    def get_absent_days(self, obj):
        summary = self._get_attendance(obj)
        return summary.absent_days if summary else None
