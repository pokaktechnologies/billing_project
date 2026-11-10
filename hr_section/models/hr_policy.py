from django.db import models
from accounts.models import CustomUser


class HRPolicy(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    )

    CATEGORY_CHOICES = (
        ('general', 'General'),
        ('leave_attendance', 'Leave & Attendance'),
        ('code_of_conduct', 'Code of Conduct'),
        ('compensation_benefits', 'Compensation & Benefits'),
        ('workplace_safety', 'Workplace Safety'),
        ('it_data_security', 'IT & Data Security'),
        ('other', 'Other'),
    )

    title = models.CharField(max_length=255, verbose_name="Policy Title")
    policy_code = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name="Policy Code")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general', verbose_name="Category")
    description = models.TextField(blank=True, null=True, verbose_name="Policy Description / Summary")
    content = models.TextField(blank=True, null=True, verbose_name="Full Policy Content")
    document = models.FileField(upload_to='hr_policies/', blank=True, null=True, verbose_name="Policy Document / PDF")
    version = models.CharField(max_length=20, default='1.0', verbose_name="Version")
    effective_date = models.DateField(blank=True, null=True, verbose_name="Effective Date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Status")

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_hr_policies', verbose_name="Created By")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "HR Policy"
        verbose_name_plural = "HR Policies"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} (v{self.version})"

