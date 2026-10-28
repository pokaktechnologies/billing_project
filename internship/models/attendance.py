from django.db import models
from .academic import Section, Faculty
from .student import Student


class ClassAttendanceSession(models.Model):
    """
    Represents an attendance session held on a specific date for a Section (Class + Batch).
    """
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="attendance_sessions"
    )
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_attendances"
    )
    date = models.DateField(db_index=True)
    topic_covered = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional syllabus topic or lecture summary"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Optional session notes or remarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('section', 'date')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.section} - {self.date}"


class StudentAttendanceRecord(models.Model):
    """
    Individual student attendance status for a class session.
    """
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave / Excused'),
        ('late', 'Late'),
    ]

    session = models.ForeignKey(
        ClassAttendanceSession,
        on_delete=models.CASCADE,
        related_name="records"
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="class_attendances"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='present'
    )
    remarks = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional note (e.g., Informed leave, Medical)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'student')
        ordering = ['student__profile__user__first_name', 'student__student_id']

    def __str__(self):
        return f"{self.student} - {self.status} ({self.session.date})"
