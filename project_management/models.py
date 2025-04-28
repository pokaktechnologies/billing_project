from django.db import models
from accounts.models import CustomUser,Customer

STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('on_hold', 'On Hold'),
    ('cancelled', 'Cancelled'),
]

from datetime import date

class ClientContract(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    client = models.ForeignKey(Customer, on_delete=models.CASCADE)
    contract_name = models.CharField(max_length=255)
    description = models.TextField()
    contract_date = models.DateField(null=True, blank=True, default=date.today)
    start_date = models.DateField()
    end_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in days", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.client} - {self.contract_name} ({self.user.id})"


class ProjectManagement(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
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



class Member(models.Model):
    ROLE_CHOICES = [
        ('full_stack_developer', 'Full Stack Developer'),
        ('frontend_developer', 'Frontend Developer'),
        ('backend_developer', 'Backend Developer'),
        ('ui_ux_designer', 'UI/UX Designer'),
        ('project_manager', 'Project Manager'),
        ('app_developer', 'App Developer'),
        ('digital_marketing', 'Digital marketing'),
        ('tester', 'Tester'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"



class Stack(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name



class ProjectMember(models.Model):
    project = models.ForeignKey(ProjectManagement, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    stack = models.ForeignKey(Stack, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.member.name} in {self.project.project_name}"
    
    class Meta:
        unique_together = ('project', 'member')


# null=True, blank=True

class Task(models.Model):
    project_member = models.ForeignKey(ProjectMember, on_delete=models.CASCADE)
    task_name = models.CharField(max_length=255)
    task_description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='not_started')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_name} ({self.project_member})"    

