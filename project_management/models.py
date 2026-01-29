from django.db import models
from django.db.models import Sum
from accounts.models import CustomUser,Customer
from django.core.validators import MinValueValidator, MaxValueValidator

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
    # ROLE_CHOICES = [
    #     ('full_stack_developer', 'Full Stack Developer'),
    #     ('frontend_developer', 'Frontend Developer'),
    #     ('backend_developer', 'Backend Developer'),
    #     ('ui_ux_designer', 'UI/UX Designer'),
    #     ('project_manager', 'Project Manager'),
    #     ('app_developer', 'App Developer'),
    #     ('digital_marketing', 'Digital marketing'),
    #     ('tester', 'Tester'),
    # ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    # name = models.CharField(max_length=255)
    # email = models.EmailField()
    # phone_number = models.CharField(max_length=15)
    # role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.first_name


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



# -------------------------------
# Task Model    
# -------------------------------

#board
class TaskBoard(models.Model):
    project = models.ForeignKey(ProjectManagement, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    
#columns
class StatusColumns(models.Model):
    board = models.ForeignKey(TaskBoard, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    
class Task(models.Model):
    difficulty_choice = [
        ('easy','Easy'),
        ('medium','Medium'),
        ('hard','Hard')
    ]
    project = models.ForeignKey(ProjectManagement, on_delete=models.CASCADE, null=True, blank=True)
    board = models.ForeignKey(TaskBoard, on_delete=models.DO_NOTHING, null=True, blank=True)
    status_column = models.ForeignKey(StatusColumns,on_delete=models.DO_NOTHING, null=True, blank=True)

    task_name = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=100,choices=difficulty_choice, null=True, blank=True)
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # start_date = models.DateField()
    # status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='not_started')
    #     project_member = models.ForeignKey(ProjectMember, on_delete=models.CASCADE)


    def __str__(self):
        return f"{self.task_name} ({self.project})"
    

class TaskAssign(models.Model):
    assigned_by = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name="assigned_tasks")
    task = models.ForeignKey(Task,on_delete=models.CASCADE,related_name="assignments")
    assigned_to = models.ForeignKey(ProjectMember,on_delete=models.CASCADE,related_name="received_tasks")
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Task: {self.task.task_name} → "
            f"{self.assigned_to.member.name}"
        )


# -------------------------------
# Report Model
# -------------------------------
class Report(models.Model):

    REPORT_TYPE_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    project = models.ForeignKey('ProjectManagement',on_delete=models.CASCADE,related_name='reports')
    report_type = models.CharField(max_length=10,choices=REPORT_TYPE_CHOICES)

    executive_summary = models.TextField()
    next_period_plan = models.TextField(null=True, blank=True)

    #daily report fields
    report_date = models.DateField(null=True, blank=True)

    #weekly report fields
    week_start = models.DateField(null=True, blank=True)
    week_end = models.DateField(null=True, blank=True)

    #monthly report fields
    month = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)

    submitted_by = models.ForeignKey('accounts.CustomUser',on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_worked_hours(self):
        """Auto calculate total hours from tasks"""
        return self.tasks.aggregate(
            total=Sum('hours')
        )['total'] or 0

    def __str__(self):
        return f"Report - {self.project} ({self.report_type}-{self.submitted_by.first_name})"
    
class ReportingTask(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='tasks')
    task_name = models.CharField(max_length=255)
    task_description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    progress_percentage = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.task_name} - {self.report.id}"

# -------------------------------
# Challenges & Resolutions
# -------------------------------
class ChallengeResolution(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='challenges')

    issue = models.TextField()
    impact = models.TextField()
    resolution = models.TextField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Challenge for Report {self.report.id}"
    
#-----------
# Attachments
#-----------
class ReportAttachment(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='report_attachments/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for Report {self.report.id}"
    
#-------------
# Links
#-------------
class ReportLink(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='links')
    url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Link for Report {self.report.id}"