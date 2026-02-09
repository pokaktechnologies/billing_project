from django.db import models
from django.utils import timezone
from accounts.models import StaffProfile

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
