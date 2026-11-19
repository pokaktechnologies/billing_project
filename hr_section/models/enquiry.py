from django.db import models


class Enquiry(models.Model):
    STATUS = (
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('responded', 'Responded'),
    )

    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Last Name")
    email = models.EmailField(max_length=254, verbose_name="Email Address")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")
    message = models.TextField(verbose_name="Enquiry Message")
    status = models.CharField(max_length=20, choices=STATUS, default='new', verbose_name="Enquiry Status")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = "Enquiry"
        verbose_name_plural = "Enquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} - {self.email}"


class ErpEnquiry(models.Model):
    HEARD_ABOUT_CHOICES = (
        ('google', 'Google Search'),
        ('social_media', 'Social Media'),
        ('referral', 'Referral'),
        ('advertisement', 'Advertisement'),
        ('other', 'Other'),
    )

    STATUS = (
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('responded', 'Responded'),
    )

    full_name = models.CharField(max_length=255)
    work_email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=255)
    company_website = models.URLField(blank=True, null=True)
    heard_about = models.CharField(max_length=50, choices=HEARD_ABOUT_CHOICES, blank=True, null=True)
    key_business_challenge = models.TextField(blank=True, null=True)
    preferred_datetime = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.company_name} ({self.created_at.date()})"

