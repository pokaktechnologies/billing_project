from django.db import models
from accounts.models import CustomUser
from .projects import ProjectManagement
from .members import ProjectMember


class ProjectNote(models.Model):
    project = models.ForeignKey(
        ProjectManagement,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Document/notepad-style long-form content")
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # new fields
    meeting_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Project Note'
        verbose_name_plural = 'Project Notes'

    def __str__(self):
        project_name = self.project.project_name if self.project_id and self.project else "No Project"
        return f"{self.title} - {project_name}"


class MeetingAttendance(models.Model):
    meeting = models.ForeignKey(
        ProjectNote,
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    project_member = models.ForeignKey(
        ProjectMember,
        on_delete=models.CASCADE,
        related_name="meeting_attendances"
    )
    is_present = models.BooleanField(default=False)

    class Meta:
        unique_together = ("meeting", "project_member")

    def __str__(self):
        return (
            f"{self.project_member.member.user.first_name} - "
            f"{self.meeting.title}"
        )
