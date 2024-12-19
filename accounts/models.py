from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now


class CustomUserManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, password=None):
        if not email:
            raise ValueError("The Email field is required")
        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, password):
        user = self.create_user(first_name, last_name, email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):     
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    is_otp_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # New fields for organization details
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    business_location = models.CharField(max_length=255, blank=True, null=True)
    state_province = models.CharField(max_length=255, blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

class Quotation(models.Model):
    customer_name = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=50, unique=True)
    order_number = models.CharField(max_length=50, blank=True, null=True)
    invoice_date = models.DateField(default=now)
    terms = models.CharField(max_length=255, default="Due on Receipt")
    due_date = models.DateField(blank=True, null=True)
    salesperson = models.CharField(max_length=255, blank=True, null=True)
    subject = models.TextField(blank=True, null=True)
    delivery_location = models.CharField(max_length=255, blank=True, null=True)
    received_location = models.CharField(max_length=255, blank=True, null=True)
    attachments = models.FileField(upload_to="quotations/", blank=True, null=True)

    def __str__(self):
        return self.invoice_number
