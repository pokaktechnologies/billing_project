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