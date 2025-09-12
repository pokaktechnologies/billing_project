from django.db import models
from accounts.models import CustomUser  # Import CustomUser for the ForeignKey

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