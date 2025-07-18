from django.db import models

class Enquiry(models.Model):
    STATUS = (
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('responded', 'Responded'),
    )

    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100,blank=True, null=True, verbose_name="Last Name")
    email = models.EmailField(max_length=254,verbose_name="Email Address")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")
    message = models.TextField(verbose_name="Enquiry Message")
    status = models.CharField(max_length=20, choices=STATUS, default='new', verbose_name="Enquiry Status")
    created_at = models.DateTimeField( auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True,verbose_name="Last Updated")

    class Meta:
        verbose_name = "Enquiry"
        verbose_name_plural = "Enquiries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} - {self.email}"
