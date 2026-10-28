from django.db import models
from accounts.models import StaffProfile
from .academic import Course, Batch
from .student import Student

class StudyMaterial(models.Model):
    STUDY_MATERIAL_TYPES = [
        ('video', 'Video'),
        ('image', 'Image'),
        ('document', 'Document'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    batches = models.ManyToManyField(Batch, blank=True, related_name="study_materials")
    title = models.CharField(max_length=200)
    description = models.TextField()
    material_type = models.CharField(max_length=20, choices=STUDY_MATERIAL_TYPES)
    file = models.FileField(upload_to='study_materials/', null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.course.title if self.course else 'No Course'})"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    due_date = models.DateField()
    course = models.ForeignKey(Course,on_delete=models.CASCADE,related_name='tasks',)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    assigned_to = models.ManyToManyField(
        Student,
        through='TaskAssignment',
        related_name='tasks',
    )

    def __str__(self):
        return self.title


class TaskAssignment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('revision_required', 'Revision Required'),
        ('completed', 'Completed'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, db_index=True,related_name="assignments")
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, db_index=True, blank=True, null=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, db_index=True, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    revision_due_date = models.DateField(null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'student')

    def __str__(self):
        return f"{self.student} - {self.task} [{self.status}]"


class TaskAttachment(models.Model):
    task = models.ForeignKey(
        Task,
        related_name="attachments",
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to="task_attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class TaskSubmission(models.Model):
    assignment = models.ForeignKey(
        TaskAssignment,
        related_name='submissions',
        on_delete=models.CASCADE
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    link = models.URLField(null=True, blank=True)
    response = models.TextField(null=True, blank=True)

    instructor_feedback = models.TextField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']  # latest first

    def __str__(self):
        return f"Submission by {self.assignment.staff} on {self.submitted_at}"


class TaskSubmissionAttachment(models.Model):
    submission = models.ForeignKey(
        TaskSubmission,
        related_name='attachments',
        on_delete=models.CASCADE
    )
    file = models.FileField(upload_to='task_submission_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']  # latest first

    def __str__(self):
        return self.file.name
