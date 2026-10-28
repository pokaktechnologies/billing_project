from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from accounts.models import SalesPerson
from .academic import Course
from .student import Student
from .payments import PAYMENT_METHODS

phone_validator = RegexValidator(
    regex=r'^\+?\d{10,15}$',
    message="Enter a valid phone number (10–15 digits, optional +)."
)


class InternshipApplication(models.Model):

    FORM_CHOICE = [
        ("internship_form", "Internship Form"),
        ("free_course_form", "Free Course Form")
    ]

    QUALIFICATION_CHOICES = [
        ('sslc', 'SSLC'),
        ('plus_two', 'Plus Two'),
        ('ug', 'Undergraduate'),
        ('pg', 'Postgraduate'),
    ]

    WHERE_DID_YOU_FIND_US_CHOICES = [
        ('google', 'Google'),
        ('social_media', 'Social Media'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    COURSE_TYPE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('recorded', 'Recorded'),
    ]

    form_type = models.CharField(max_length=20, choices=FORM_CHOICE, default="internship_form")
    # Basic Info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    primary_phone = models.CharField(max_length=15, validators=[phone_validator])
    secondary_phone = models.CharField(max_length=15, validators=[phone_validator], blank=True, null=True)

    email = models.EmailField(unique=False)
    dob = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    # Education
    qualification = models.CharField(max_length=20, choices=QUALIFICATION_CHOICES)
    course_name = models.CharField(max_length=255, blank=True, null=True)

    # Address
    address = models.TextField()
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # Source Info
    where_did_you_find_us = models.CharField(
        max_length=20,
        choices=WHERE_DID_YOU_FIND_US_CHOICES,
        blank=True,
        null=True
    )
    other_source = models.CharField(max_length=255, blank=True, null=True)

    # Course Info
    course_applied_for = models.CharField(max_length=255, blank=True, null=True)# unused
    course_duration = models.PositiveIntegerField(help_text="Duration in months")
    course_type = models.CharField(max_length=10, choices=COURSE_TYPE_CHOICES)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="internship_applications", blank=True, null=True)
    # Profiles
    linkedin_profile_url = models.URLField(blank=True, null=True)
    github_profile_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    academic_counselor = models.CharField(max_length=50, blank=True, null=True)# unused
    councellor = models.ForeignKey(
        SalesPerson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internship_applications"
    )
    # slot booking
    slot_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    slot_payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True, null=True)
    slot_transaction_id = models.CharField(max_length=200, null=True, blank=True)
    slot_payment_date = models.DateField(null=True, blank=True)

    #conversion fields
    is_converted = models.BooleanField(default=False)
    converted_students = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="converted_applications")


    created_at = models.DateTimeField(auto_now_add=True)

    # -----------------------------
    # Validation Logic
    # -----------------------------
    def clean(self):
        # Handle "other" source logic
        if self.where_did_you_find_us == 'other' and not self.other_source:
            raise ValidationError("Please specify 'other_source' when selecting 'Other'.")

        if self.where_did_you_find_us != 'other' and self.other_source:
            raise ValidationError("'other_source' should only be filled when 'Other' is selected.")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class InternshipDocument(models.Model):

    DOCUMENT_TYPE_CHOICES = [
        ('qualification', 'Qualification Document'),
        ('legal', 'Legal Document'),
    ]

    application = models.ForeignKey(
        InternshipApplication,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )

    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, null=True, blank=True)

    file = models.FileField(
        upload_to='documents/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        ],
        null=True,
        blank=True
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        first_name = self.application.first_name if self.application else "No"
        last_name = self.application.last_name if self.application else "Application"
        return f"{self.document_type} - {first_name} {last_name} (ID: {self.id})"
