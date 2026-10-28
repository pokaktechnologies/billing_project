from django.db import models
from accounts.models import Department, StaffProfile

class Center(models.Model):
    name = models.CharField(max_length=100)
    country_name = models.CharField(max_length=50, null=True, blank=True)
    state_name = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.name


class Faculty(models.Model):
    user = models.OneToOneField(StaffProfile, on_delete=models.CASCADE, related_name="faculty_profile")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="legacy_faculties", null=True, blank=True)
    departments = models.ManyToManyField(Department, related_name="faculties", blank=True)
    is_active = models.BooleanField(default=True)
    def get_full_name(self):
        user = self.user.user
        return f"{user.first_name} {user.last_name}"
    
    def __str__(self):
        return self.user.user.first_name


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    faculties = models.ManyToManyField(Faculty, related_name="courses", blank=True)
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.CASCADE,
        related_name="courses"
    )
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    tax_settings = models.ForeignKey(
        'finance.TaxSettings',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True   
    )

    def __str__(self):
        return self.title


class Batch(models.Model):
    batch_number = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    faculties = models.ManyToManyField(Faculty, related_name="batches", blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="batches")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ['course', 'batch_number']

    def __str__(self):
        return f"{self.course.title} - {self.batch_number}"


class Class(models.Model):
    name       = models.CharField(max_length=100)
    center     = models.ForeignKey("Center", on_delete=models.CASCADE, related_name="classes")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Section(models.Model):
    class_obj    = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="sections")   
    batch        = models.ForeignKey(Batch, on_delete=models.CASCADE)
    start_time   = models.TimeField()
    end_time     = models.TimeField()
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.class_obj.name} - {self.batch}"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be greater than start time")


class SectionDay(models.Model):
    DAYS = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="days")
    day     = models.CharField(max_length=3, choices=DAYS)

    class Meta:
        unique_together = ("section", "day")

    def __str__(self):
        return f"{self.section} - {self.day}"


class AssignedStaffCourse(models.Model):####
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, db_index=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_index=True)
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
