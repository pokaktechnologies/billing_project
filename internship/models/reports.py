from django.db import models
from django.conf import settings
from accounts.models import SalesPerson, CustomUser
from .academic import Course, Batch, Faculty
from .student import Student

class ReportTemplate(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="report_templates")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class TemplateSection(models.Model):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=250)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.template.name} - {self.title}"


class TemplateField(models.Model):
    FIELD_TYPES = [
        ("text", "Text"),
        ("number", "Number"),
        ("rating", "Rating"),
        ("dropdown", "Dropdown"),
        ("table", "Table"),
        ("textarea", "Textarea"),
        ("checkbox_grid", "Checkbox Grid")
    ]

    section = models.ForeignKey(TemplateSection, on_delete=models.CASCADE, related_name="fields")
    label = models.CharField(max_length=250)
    field_type =models.CharField(max_length=20, choices=FIELD_TYPES)
    placeholder = models.CharField(max_length=250, blank=True, null=True)
    is_required = models.BooleanField(default=False)
    order = models.PositiveBigIntegerField(default=0)
    config = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.section.title} - {self.label}"


class StudentReport(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="reports")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="reports")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reports")
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_reports")
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_reports")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["student", "batch"]

    def save(self, *args, **kwargs):
        if self.batch_id:
            self.course = self.batch.course
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.template.name if self.template else 'No Template'}"


class ReportFieldValue(models.Model):
    report = models.ForeignKey(StudentReport, on_delete=models.CASCADE,related_name="field_values")
    field = models.ForeignKey(TemplateField, on_delete=models.CASCADE,related_name="field_values")
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["report", "field"]

    def __str__(self):
        return f"{self.report} - {self.field.label}"


class CounsellorHRSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted to HR'),
        ('approved', 'Approved by HR'),
        ('rejected', 'Rejected by HR'),
    ]

    counsellor = models.ForeignKey(
        SalesPerson,
        on_delete=models.CASCADE,
        related_name="hr_submissions"
    )
    start_date = models.DateField(help_text="Start date of conversion period")
    end_date = models.DateField(help_text="End date of conversion period")
    period_label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. 'April 2026' or 'Q1 2026'"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='submitted'
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_counsellor_hr_batches"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_counsellor_hr_batches"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['counsellor', 'start_date', 'end_date']

    def __str__(self):
        return f"{self.counsellor} ({self.start_date} to {self.end_date}) - {self.status}"
