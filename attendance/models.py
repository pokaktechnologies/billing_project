from django.db import models
from django.utils import timezone
from accounts.models import StaffProfile
from datetime import datetime, timedelta
class DailyAttendance(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="daily_attendance")
    date = models.DateField(default=timezone.localdate)
    total_working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    STATUS_CHOICES = [
    ("absent", "Absent"),        # default
    ("leave", "Approved Leave"), # HR-approved only
    ("half_day", "Half Day"),
    ("full_day", "Full Day"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="absent")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('staff', 'date')

    def __str__(self):
        return f"{self.staff.user.email} - {self.date} - {self.status}"

class AttendanceSession(models.Model):
    SESSION_CHOICES = [
        ('session1', 'Session 1'),
        ('session2', 'Session 2'),
        ('session3', 'Session 3'),
    ]
    SESSION_STATUS = [
        ("leave", "Leave"),
        ("late", "Late"),
        ("present", "Present"),
    ]
    daily_attendance = models.ForeignKey(DailyAttendance, on_delete=models.CASCADE, related_name="sessions")
    session = models.CharField(max_length=10, choices=SESSION_CHOICES)
    status = models.CharField(max_length=10, choices=SESSION_STATUS, default="leave")
    login_time = models.DateTimeField(blank=True, null=True)
    logout_time = models.DateTimeField(blank=True, null=True)

    # session_start = models.TimeField()
    # session_end = models.TimeField()

    def session_duration(self):
        if self.login_time and self.logout_time:
            delta = self.logout_time - self.login_time
            return delta.total_seconds() / 3600  # return hours
        return 0

    def __str__(self):
        return f"{self.session} - {self.status} - {self.daily_attendance.staff.user.email} "


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)
    is_paid = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.date} - {self.is_paid}"


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='leave_requests_staff')
    start_date = models.DateField()
    end_date = models.DateField()

    # half day fields
    is_half_day = models.BooleanField(default=False)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    reason = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    requested_at = models.DateTimeField(auto_now_add=True)
    actioned_at = models.DateTimeField(null=True, blank=True)
    action_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_requests_actioned')
    @property
    def duration_hours(self):
        """Return the requested duration in hours for half-day leave."""
        if (
            not self.is_half_day
            or not self.start_time
            or not self.end_time
        ):
            return None

        start = datetime.combine(self.start_date, self.start_time)
        end = datetime.combine(self.end_date, self.end_time)

        return round((end - start).total_seconds() / 3600, 2)

    @property
    def leave_days(self):
        """Return 0.5 day for half-day leave or the full date range."""
        if self.is_half_day:
            return 0.5

        return (self.end_date - self.start_date).days + 1


    def __str__(self):
        return f"{self.staff.user.email} - {self.start_date} to {self.end_date} - {self.status}"
