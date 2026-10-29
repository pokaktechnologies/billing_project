from django.db import models
from accounts.models import CustomUser
from .contracts import ClientContract

STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('on_hold', 'On Hold'),
    ('cancelled', 'Cancelled'),
]


class ProjectManagement(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('dev', 'Developer'),
        ('dm', 'Digital Marketing'),
        ('testing', 'Testing'),
    ]
    project_number = models.CharField(max_length=255, unique=True, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    # NEW FIELD
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        default='dev',
        db_index=True
    )
    contract = models.ForeignKey(ClientContract, on_delete=models.CASCADE, null=True, blank=True)
    project_name = models.CharField(max_length=255)
    project_description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in days", null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='not_started')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project_name} ({self.user.first_name})"
