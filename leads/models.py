from django.db import models
# Create your models here.
from accounts.models import  CustomUser
from django.utils import timezone

class Lead(models.Model):
    CustomUser = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leads')
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100,blank=True, null=True)
    email = models.EmailField(unique=False, blank=True, null=True)
    phone = models.CharField(max_length=15, unique=False, blank=True, null=True)
    enquiry = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    lead_status = models.CharField(max_length=50, choices=[
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('lost', 'Lost'),
        ('follow_up', 'Follow Up'),
        ('in_progress', 'In Progress'),
        ('converted', 'Converted'),
    ], default='new')
    location = models.CharField(max_length=100, blank=True, null=True)
    lead_source = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=timezone.now)

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

