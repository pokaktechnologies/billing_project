from django.db import models
from accounts.models import StaffProfile

class PayrollPeriod(models.Model):
    month = models.CharField(max_length=7)  # YYYY-MM
    is_locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("month",)


class AttendanceSummary(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    month = models.CharField(max_length=7)

    working_days = models.PositiveSmallIntegerField()
    full_days = models.PositiveSmallIntegerField()
    half_days = models.PositiveSmallIntegerField()
    leave_days = models.PositiveSmallIntegerField()
    absent_days = models.PositiveSmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("staff", "month")


class Payroll(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    month = models.CharField(max_length=7)

    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    working_days = models.PositiveSmallIntegerField()

    paid_leave_used = models.PositiveSmallIntegerField()
    unpaid_leave_days = models.DecimalField(max_digits=5, decimal_places=2)

    deduction = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=10,
        choices=[("DRAFT", "Draft"), ("PAID", "Paid")],
        default="DRAFT"
    )

    created_at = models.DateTimeField(auto_now_add=True)

 