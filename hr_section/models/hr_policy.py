from django.core.exceptions import ValidationError
from django.db import models
from accounts.models import CustomUser


class HRPolicy(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    )

    title = models.CharField(max_length=255, verbose_name="Policy Title")
    policy_code = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name="Policy Code")
    description = models.TextField(blank=True, null=True, verbose_name="Summary")
    effective_date = models.DateField(blank=True, null=True, verbose_name="Effective Date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Status")
    document = models.FileField(upload_to='hr_policies/', blank=True, null=True, verbose_name="Document / PDF")

    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_hr_policies', verbose_name="Created By"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "HR Policy"
        verbose_name_plural = "HR Policies"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class HRPolicySection(models.Model):
    """A section of a policy. `content` holds descriptive / intro paragraphs."""
    policy = models.ForeignKey(HRPolicy, related_name="sections", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.policy.title} - {self.title}"


class HRPolicySubtitle(models.Model):
    section = models.ForeignKey(HRPolicySection, related_name="subtitles", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.title


class HRPolicyPoint(models.Model):
    """
    A bullet point. Belongs EITHER directly to a section (no subtitle)
    OR to a subtitle. `title` is an optional label for key-value style rules.
    """
    section = models.ForeignKey(
        HRPolicySection, related_name="direct_points",
        on_delete=models.CASCADE, null=True, blank=True
    )
    subtitle = models.ForeignKey(
        HRPolicySubtitle, related_name="points",
        on_delete=models.CASCADE, null=True, blank=True
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def clean(self):
        # Enforced at application level (a DB CheckConstraint conflicts with
        # Django's cascade-delete collector on MySQL).
        if bool(self.section_id) == bool(self.subtitle_id):
            raise ValidationError("A point must belong to either a section or a subtitle, not both.")

    def __str__(self):
        return self.content[:50]
