from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from .projects import ProjectManagement, STATUS_CHOICES
from .members import ProjectMember


class TaskBoard(models.Model):
    project = models.ForeignKey(ProjectManagement, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)  # planned
    end_date = models.DateField(null=True, blank=True)    # deadline
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class StatusColumns(models.Model):
    board = models.ForeignKey(TaskBoard, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    difficulty_choice = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ]
    project = models.ForeignKey(ProjectManagement, on_delete=models.CASCADE, null=True, blank=True)
    board = models.ForeignKey(TaskBoard, on_delete=models.DO_NOTHING, null=True, blank=True)

    task_name = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=100, choices=difficulty_choice, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started', null=True, blank=True)
    end_date = models.DateField()
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    meeting = models.ForeignKey(
        'project_management.ProjectNote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meeting_tasks"
    )

    def get_duration_seconds(self):
        if not self.start_time:
            return None

        end_time = self.end_time or timezone.now()
        duration = end_time - self.start_time
        return int(duration.total_seconds())

    def __str__(self):
        return f"{self.task_name} ({self.project})"


class TaskAssign(models.Model):
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="assigned_tasks")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    assigned_to = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="received_tasks")
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Task: {self.task.task_name} → "
