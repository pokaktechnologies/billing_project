from django.db import models
from accounts.models import StaffProfile

class PayrollPeriod(models.Model):
    month = models.CharField(max_length=7, unique=True)  # YYYY-MM
    STATUS_CHOICES = [
        ("open", "Open"),
        ("generated", "Generated"),
        ("locked", "Locked"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    generated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.month} - {self.status}"


class AttendanceSummary(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="attendance_summaries")
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name="attendance_summaries", null=True)
    month = models.CharField(max_length=7)

    working_days = models.PositiveSmallIntegerField()
    full_days = models.PositiveSmallIntegerField()
    half_days = models.PositiveSmallIntegerField()
    leave_days = models.PositiveSmallIntegerField()
    absent_days = models.PositiveSmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("staff", "period")

    def __str__(self):
        return f"{self.staff.user.email} - {self.period.month if self.period else self.month}"


class Payroll(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="payrolls")
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name="payrolls", null=True)
    month = models.CharField(max_length=7)

    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    working_days = models.PositiveSmallIntegerField()

    paid_leave_used = models.PositiveSmallIntegerField()
    unpaid_leave_days = models.DecimalField(max_digits=5, decimal_places=2)

    deduction = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=10,
        choices=[("Draft", "Draft"), ("Paid", "Paid")],
        default="Draft"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("staff", "period")

    @property
    def attendance_summary(self):
        """
        Returns the corresponding AttendanceSummary for this payroll record.
        """
        from .models import AttendanceSummary
        return AttendanceSummary.objects.filter(staff=self.staff, period=self.period).first()

    def __str__(self):
        return f"{self.staff.user.email} - {self.period.month if self.period else self.month}"