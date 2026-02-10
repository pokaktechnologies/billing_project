from attendance.models import DailyAttendance, Holiday
from .models import AttendanceSummary

def generate_attendance_summary(staff, year, month):
    records = DailyAttendance.objects.filter(
        staff=staff,
        date__year=year,
        date__month=month
    )

    working_days = records.count()

    summary = AttendanceSummary.objects.create(
        staff=staff,
        month=f"{year}-{month:02d}",
        working_days=working_days,
        full_days=records.filter(status="full_day").count(),
        half_days=records.filter(status="half_day").count(),
        leave_days=records.filter(status="leave").count(),
        absent_days=records.filter(status="absent").count(),
    )

    # HARD validation
    if (
        summary.full_days +
        summary.half_days +
        summary.leave_days +
        summary.absent_days
    ) != working_days:
        raise ValueError("Attendance mismatch")

    return summary


from .models import Payroll, PayrollPeriod

PAID_LEAVE_LIMIT = 2

def generate_payroll(summary, monthly_salary):
    paid_leave_used = min(summary.leave_days, PAID_LEAVE_LIMIT)
    unpaid_leave = max(summary.leave_days - paid_leave_used, 0)

    half_day_unpaid = summary.half_days * 0.5

    unpaid_days = (
        unpaid_leave +
        summary.absent_days +
        half_day_unpaid
    )

    per_day_salary = monthly_salary / summary.working_days
    deduction = unpaid_days * per_day_salary
    net_salary = monthly_salary - deduction

    payroll = Payroll.objects.create(
        staff=summary.staff,
        month=summary.month,
        gross_salary=monthly_salary,
        unpaid_days=unpaid_days,
        paid_leave_used=paid_leave_used,
        deduction=deduction,
        net_salary=max(net_salary, 0)
    )

    PayrollPeriod.objects.update_or_create(
        month=summary.month,
        defaults={"is_locked": True}
    )

    return payroll
