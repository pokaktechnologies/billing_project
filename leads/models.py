from django.db import models
# Create your models here.
from accounts.models import  CustomUser,SalesPerson
from django.utils import timezone

class Lead(models.Model):
    CustomUser = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='leads')
    # -------------------
    # CUSTOMER DETAILS
    # -------------------
    name = models.CharField(max_length=100)  # Customer Name
    email = models.EmailField(unique=False, blank=True, null=True)  # Customer Email
    phone = models.CharField(max_length=15, unique=False, blank=True, null=True)  # Mobile
    enquiry = models.CharField(max_length=100, blank=True, null=True)  # Customer Enquiry
    project_requirement = models.TextField(blank=True, null=True)  # Project Requirement

    # -------------------
    # COMPANY DETAILS
    # -------------------
    company = models.CharField(max_length=100, blank=True, null=True)  # Company Name
    company_address = models.CharField(max_length=255, blank=True, null=True)  # Company Address
    company_location = models.CharField(max_length=100, blank=True, null=True)  # Company Location
    

    # -------------------
    # LEAD DETAILS
    # -------------------
    lead_number = models.CharField(max_length=50, unique=True,null=True, blank=True)  # Lead Number
    lead_source = models.CharField(max_length=50)  # Lead Source
    lead_city = models.CharField(max_length=100, blank=True, null=True)  # Lead City
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.PROTECT, blank=True, null=True)
    lead_status = models.CharField(
        max_length=50,
        choices=[
            ('new', 'New'),
            ('contacted', 'Contacted'),
            ('lost', 'Lost'),
            ('follow_up', 'Follow Up'),
            ('created', 'Created'),
            ('in_progress', 'In Progress'),
            ('converted', 'Converted'),
        ],
        default='new'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)  # Date

    def __str__(self):
        return self.name


class Meeting(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='meetings')
    date = models.DateTimeField()
    subject = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, choices=[
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ], default='scheduled')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Meeting with {self.lead.name} on {self.date}"  


# marketing section
class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)  # Date

    def __str__(self):
        return self.name

class Source(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)  # Date

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="categories")
    created_at = models.DateTimeField(default=timezone.now)  # Date

    class Meta:
        unique_together = ('name', 'source')

    def __str__(self):
        return f"{self.name} ({self.source.name})"


# -------------------
# Daily Report (Main Entry)
# -------------------
class MarketingReport(models.Model):
    date = models.DateField()
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name="daily_reports")
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.PROTECT, related_name="reports")
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    calls = models.PositiveIntegerField(default=0)
    leads = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)  # Date
    

    def __str__(self):
        return f"{self.salesperson.first_name} | {self.source.name} | {self.location.name} | {self.category.name}"