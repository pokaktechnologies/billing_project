from rest_framework import serializers
from ..models import Payroll, AttendanceSummary, PayrollDeduction, PayrollEarning, PayrollPeriod
from accounts.serializers.user import StaffProfileSerializer
from .payroll_period import PayrollPeriodSerializer

class AttendanceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSummary
        fields = [
            'id', 'working_days', 'full_days', 'half_days', 
            'leave_days', 'absent_days', 'created_at'
        ]
class PayrollEarningSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayrollEarning
        fields = [
            "id",
            "earning_type",
            "amount",
        ]
        extra_kwargs = {
            "id": {"required": False}
        }


class PayrollDeductionSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayrollDeduction
        fields = [
            "id",
            "deduction_type",
            "amount",
        ]
        extra_kwargs = {
            "id": {"required": False}
        }


class PayrollListSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    staff_email = serializers.EmailField(source='staff.user.email', read_only=True)
    department = serializers.CharField(source='staff.job_detail.department.name', read_only=True)
    role = serializers.CharField(source='staff.job_detail.role', read_only=True)
    period_month = serializers.CharField(source='period.month', read_only=True)
    attendance_summary = serializers.SerializerMethodField()
    employee_id = serializers.CharField(source='staff.job_detail.employee_id', read_only=True)

    earnings = PayrollEarningSerializer(
        many=True,
        read_only=True
    )

    deductions = PayrollDeductionSerializer(
        many=True,
        read_only=True
    )

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
    earnings = PayrollEarningSerializer(
        many=True,
        read_only=True
    )

    deductions = PayrollDeductionSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Payroll
        fields = "__all__"

    def get_attendance_summary(self, obj):
        summary = obj.attendance_summary
        if summary:
            return AttendanceSummarySerializer(summary).data
        return None


from ..models import (
    Payroll,
    PayrollEarning,
    PayrollDeduction,
)
from decimal import Decimal

class PayrollEditSerializer(serializers.ModelSerializer):

    earnings = PayrollEarningSerializer(
        many=True,
        required=False
    )

    deductions = PayrollDeductionSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = Payroll
        fields = [
            'gross_salary',
            'working_days',
            'total_working_hours',
            'paid_leave_used',
            'unpaid_leave_days',
            'deduction',
            'net_salary',
            'earnings',
            'deductions',
        ]

    def update(self, instance, validated_data):

        earnings_data = validated_data.pop('earnings', None)
        deductions_data = validated_data.pop('deductions', None)

        # --------------------------------
        # Update normal Payroll fields
        # --------------------------------

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # --------------------------------
        # Update Earnings
        # --------------------------------

        if earnings_data is not None:

            existing_earning_ids = []

            for earning_data in earnings_data:

                earning_id = earning_data.pop('id', None)

                if earning_id:

                    earning = PayrollEarning.objects.get(
                        id=earning_id,
                        payroll=instance
                    )

                    for attr, value in earning_data.items():
                        setattr(earning, attr, value)

                    earning.save()

                    existing_earning_ids.append(earning.id)

                else:

                    earning = PayrollEarning.objects.create(
                        payroll=instance,
                        **earning_data
                    )

                    existing_earning_ids.append(earning.id)

            # Anything removed from the submitted list is deleted
            PayrollEarning.objects.filter(
                payroll=instance
            ).exclude(
                id__in=existing_earning_ids
            ).delete()

        # --------------------------------
        # Update Deductions
        # --------------------------------

        if deductions_data is not None:

            existing_deduction_ids = []

            for deduction_data in deductions_data:

                deduction_id = deduction_data.pop('id', None)

                if deduction_id:

                    deduction = PayrollDeduction.objects.get(
                        id=deduction_id,
                        payroll=instance
                    )

                    for attr, value in deduction_data.items():
                        setattr(deduction, attr, value)

                    deduction.save()

                    existing_deduction_ids.append(deduction.id)

                else:

                    deduction = PayrollDeduction.objects.create(
                        payroll=instance,
                        **deduction_data
                    )

                    existing_deduction_ids.append(deduction.id)

            # Anything removed from the submitted list is deleted
            PayrollDeduction.objects.filter(
                payroll=instance
            ).exclude(
                id__in=existing_deduction_ids
            ).delete()

        # --------------------------------
        # Recalculate totals
        # --------------------------------

        total_earnings = sum(
            (
                earning.amount
                for earning in instance.earnings.all()
            ),
            Decimal('0.00')
        )

        total_deductions = sum(
            (
                deduction.amount
                for deduction in instance.deductions.all()
            ),
            Decimal('0.00')
        )

        instance.gross_salary = total_earnings
        instance.deduction = total_deductions
        instance.net_salary = max(
            total_earnings - total_deductions,
            Decimal('0.00')
        )

        instance.save()

        return instance
