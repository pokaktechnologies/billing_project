from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from .projects import ProjectManagement, STATUS_CHOICES


class Report(models.Model):
    REPORT_TYPE_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    project = models.ForeignKey(ProjectManagement, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)

    executive_summary = models.TextField()
    next_period_plan = models.TextField(null=True, blank=True)
    remark = models.TextField(null=True, blank=True)

    # daily report fields
    report_date = models.DateField(null=True, blank=True)

    # weekly report fields
    week_start = models.DateField(null=True, blank=True)
    week_end = models.DateField(null=True, blank=True)

    # monthly report fields
    month = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)

    submitted_by = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_worked_hours(self):
        """Auto calculate total hours from tasks"""
        return self.tasks.aggregate(
            total=Sum('hours')
        )['total'] or 0

    def __str__(self):
        return f"Report - {self.project} ({self.report_type}-{self.submitted_by.first_name})"


class ReportingTask(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='tasks')
    task_name = models.CharField(max_length=255)
    task_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    progress_percentage = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.task_name} - {self.report.id}"


class ChallengeResolution(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='challenges')

    issue = models.TextField()
    impact = models.TextField()
    resolution = models.TextField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Challenge for Report {self.report.id}"


class ReportAttachment(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='report_attachments/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for Report {self.report.id}"


class ReportLink(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='links')
    url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Link for Report {self.report.id}"
