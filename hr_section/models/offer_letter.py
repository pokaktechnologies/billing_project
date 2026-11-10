from django.db import models
from accounts.models import CustomUser


class StatusChoices(models.TextChoices):
    DRAFT = "draft", "Draft"
    SENT = "sent", "Sent"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class DutyTypeChoices(models.TextChoices):
    ONSITE = "onsite", "Onsite"
    REMOTE = "remote", "Remote"
    HYBRID = "hybrid", "Hybrid"


class OfferLetter(models.Model):
    candidate_name  = models.CharField(max_length=255)
    candidate_email = models.EmailField(blank=True, null=True)
    job_title       = models.CharField(max_length=255)
    introduction    = models.TextField(blank=True, null=True)

    responsibilities = models.JSONField(default=list, blank=True)

    basic_salary   = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    allowances = models.JSONField(default=list, blank=True)

    is_target_based = models.BooleanField(default=False)
    target_details  = models.TextField(blank=True, null=True)

    contract_period  = models.CharField(max_length=100, blank=True, null=True)
    notice_period    = models.CharField(max_length=100, blank=True, null=True)
    probation_period = models.CharField(max_length=100, blank=True, null=True)

    duty_type    = models.CharField(max_length=20, choices=DutyTypeChoices.choices, default="ONSITE")
    working_days = models.CharField(max_length=100, blank=True, null=True)
    timing       = models.CharField(max_length=100, blank=True, null=True)

    food_accommodation = models.CharField(max_length=255, default="NIL", blank=True, null=True)
    joining_date       = models.DateField()

    note = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    company_name     = models.CharField(max_length=255)
    hr_name          = models.CharField(max_length=255, blank=True, null=True)
    company_location = models.CharField(max_length=255, blank=True, null=True)

    status     = models.CharField(max_length=20, choices=StatusChoices.choices, default="DRAFT")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.candidate_name} - {self.job_title} ({self.status})"


class OfferLetterSection(models.Model):
    offer_letter = models.ForeignKey(
        OfferLetter,
        on_delete=models.CASCADE,
        related_name="sections"
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class OfferLetterSubtitle(models.Model):
    section = models.ForeignKey(
        OfferLetterSection,
        on_delete=models.CASCADE,
        related_name="subtitles"
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class OfferLetterPoint(models.Model):
    subtitle = models.ForeignKey(
        OfferLetterSubtitle,
        on_delete=models.CASCADE,
        related_name="points"
    )
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.content[:100]

