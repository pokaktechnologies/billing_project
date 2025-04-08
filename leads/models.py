from django.db import models
# Create your models here.
from accounts.models import  CustomUser
from django.utils import timezone

class Lead(models.Model):
    CustomUser = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='leads')
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    email = models.EmailField(unique=False)
    phone = models.CharField(max_length=15, unique=False)
    interested_in = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    lead_status = models.CharField(max_length=50, choices=[
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('lost', 'Lost'),
        ('follow_up', 'Follow Up'),
        ('in_progress', 'In Progress'),
        ('converted', 'Converted'),
    ], default='new')
    lead_source = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
