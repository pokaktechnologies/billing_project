from django.db import models
from accounts.models import Department,StaffProfile

# Create your models here.
class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class AssignedStaffCourse(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    assigned_date = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["staff", "course"],
                name="unique_staff_course"
            )
        ]

    def __str__(self):
        return f"{self.staff.user.email} - {self.course.title}"


class StudyMaterial(models.Model):
    STUDY_MATERIAL_TYPES = [
        ('video', 'Video'),
        ('image', 'Image'),
        ('document', 'Document'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    material_type = models.CharField(max_length=20, choices=STUDY_MATERIAL_TYPES)
    file = models.FileField(upload_to='study_materials/', null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # def clean(self):
    #     if not self.file and not self.url:
    #         raise ValidationError("Either file or url must be provided")

    def __str__(self):
        return f"{self.title} ({self.course.title})"
