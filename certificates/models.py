from django.db import models
from accounts.models import CustomUser, StaffProfile
class Certificate(models.Model):
    CATEGORY_CHOICES = [
        ('Internship', 'Internship'),
        ('Training', 'Training'),
        ('Employee', 'Employee'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Issued', 'Issued'),
    ]

    full_name = models.CharField(max_length=200, help_text="Full name of the certificate requester")
    start_date = models.DateField(help_text="Start date of the certificate period")
    end_date = models.DateField(help_text="End date of the certificate period")
    designation = models.CharField(max_length=200, blank=True, null=True, help_text="Designation or role of the requester")
    email = models.EmailField(max_length=254, help_text="Email address of the requester")
    proof_document = models.FileField(upload_to='certificate_proofs/', blank=True, null=True, help_text="Upload ID proof or supporting document")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, help_text="Category of the certificate")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', help_text="Status of the certificate request")
    requested_at = models.DateTimeField(auto_now_add=True, help_text="Date and time the request was submitted")
    processed_at = models.DateTimeField(blank=True, null=True, help_text="Date and time the request was processed")

    # New fields for employee certificates
    employee = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates', help_text="Linked employee for internal certificates")
    is_internal = models.BooleanField(default=False, help_text="Indicates if the certificate is for an internal staff member")

    def __str__(self):
        return f"{self.full_name} - {self.category} Certificate (Status: {self.status})"

    class Meta:
        verbose_name = "Certificate Request"
        verbose_name_plural = "Certificate Requests"


class CertificateHistory(models.Model):
    name = models.CharField(max_length=200, help_text="Full name of the certificate requester")
    certificate_type = models.CharField(max_length=20, help_text="Type of the certificate")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date and time the certificate was created")
    def __str__(self):
        return f"{self.name} - {self.certificate_type} Certificate"




class SignatoryPerson(models.Model):
    name        = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    signature   = models.ImageField(upload_to='signatures/', null=True, blank=True)
    is_active   = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.designation}"


class CertificateSignatory(models.Model):
    certificate = models.ForeignKey('CertificateRecord', on_delete=models.CASCADE, related_name='signatories')
    signatory = models.ForeignKey(
        'SignatoryPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificate_signatories'
    )
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order']
        unique_together = ('certificate', 'order')

    def __str__(self):
        return f"{self.certificate} — Signatory {self.order}: {self.signatory}"
    


class CertificateRecord(models.Model):
    class CertificateType(models.TextChoices):
        INTERNSHIP = 'Internship', 'Internship'
        JOB_TRAINING = 'Job Training', 'Job Training'
        EXPERIENCE = 'Experience', 'Experience'
        EMPLOYEE = 'Employee', 'Employee'
        WEBINAR = 'Webinar', 'Webinar'
        INTERNSHIP_COLLEGE = 'Internship College', 'Internship College'
    
    class DurationUnit(models.TextChoices):
        HOURS = 'Hours', 'Hours'
        DAYS = 'Days', 'Days'

    # ── User link ──────────────────────────────────────────────────────────
    user = models.ForeignKey(
        'accounts.StaffProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificates'
    )

    # ── Common fields (all types) ──────────────────────────────────────────
    certificate_type = models.CharField(max_length=50, choices=CertificateType.choices)
    certificate_number = models.CharField(max_length=100, unique=True, blank=True)
    full_name        = models.CharField(max_length=255)
    designation      = models.CharField(max_length=255, null=True, blank=True)
    issue_date       = models.DateField(auto_now_add=True)

    # ── Date fields (not used in Webinar) ─────────────────────────────────
    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)

    # ── Webinar-specific ───────────────────────────────────────────────────
    webinar_title  = models.CharField(max_length=255, null=True, blank=True)
    topics_covered = models.TextField(null=True, blank=True)
    webinar_date   = models.DateField(null=True, blank=True)

    # ── Internship College-specific ────────────────────────────────────────
    college_name   = models.CharField(max_length=255, null=True, blank=True)
    duration_value = models.PositiveIntegerField(null=True, blank=True)
    duration_unit  = models.CharField(max_length=20, choices=DurationUnit.choices, null=True, blank=True)

    # ── Internship / College shared ────────────────────────────────────────
    course = models.CharField(max_length=255, null=True, blank=True)

    # ── Job Training-specific ──────────────────────────────────────────────
    training_topic = models.CharField(max_length=255, null=True, blank=True)

    # ── Experience / Employee-specific ─────────────────────────────────────
    department         = models.CharField(max_length=255, null=True, blank=True)
    employee_id        = models.CharField(max_length=100, null=True, blank=True)
    reason_for_leaving = models.TextField(null=True, blank=True)

    # ── Meta ───────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        no_user_types = ['Webinar', 'Internship College']
        if self.certificate_type not in no_user_types and self.user is None:
            raise ValidationError("User is required for this certificate type.")
        
    def save(self, *args, **kwargs):
        if not self.certificate_number:
            from certificates.utils import generate_certificate_number
            self.certificate_number = generate_certificate_number(self.certificate_type)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Certificate Record'
        verbose_name_plural = 'Certificate Records'

    def __str__(self):
        return f"{self.full_name} — {self.certificate_type} ({self.issue_date})"