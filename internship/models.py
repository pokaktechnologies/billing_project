from django.db import models
from accounts.models import Department, SalesPerson, StaffProfile


class Center(models.Model):
    name = models.CharField(max_length=100)
    country_name = models.CharField(max_length=50, null=True, blank=True)
    state_name = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    def __str__(self):
        return self.name
class Student(models.Model):
    profile  = models.OneToOneField(StaffProfile, on_delete=models.CASCADE, related_name="student_profile")
    student_id = models.CharField(max_length=20, unique=True)
    center = models.ForeignKey(Center, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    payment_type = models.ForeignKey('InstallmentPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    councellor = models.ForeignKey(SalesPerson, on_delete=models.SET_NULL, null=True, blank=True, related_name="counselled_students")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def get_full_name(self):
        user = self.profile.user
        return f"{user.first_name} {user.last_name}"
    
    def __str__(self):
        return self.profile.user.first_name

class Faculty(models.Model):
    user = models.OneToOneField(StaffProfile, on_delete=models.CASCADE, related_name="faculty_profile")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="faculties", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    def get_full_name(self):
        user = self.user.user
        return f"{user.first_name} {user.last_name}"
    
    def __str__(self):
        return self.user.user.first_name

class CourseFaculty(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="course_faculties")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="course_faculties")
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.faculty.user.user.first_name
    
    def get_full_name(self):
        user = self.faculty.user.user
        return f"{user.first_name} {user.last_name}"

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
    batch        = models.ForeignKey("Batch", on_delete=models.CASCADE)
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
    

from django.core.exceptions import ValidationError

class InstallmentPlan(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='installment_plans')
    total_installments = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['course', 'total_installments']
        ordering = ['total_installments']
        indexes = [
            models.Index(fields=['course']),
        ]

    def clean(self):
        total = sum(item.amount for item in self.items.all())
        if total != self.course.total_fee:
            raise ValidationError("Installments total must match course fee")

    def __str__(self):
        return f"{self.course.title} - {self.total_installments} Installments"
    
class InstallmentItem(models.Model):
    plan = models.ForeignKey(
        InstallmentPlan,
        on_delete=models.CASCADE,
        related_name='items'
    )

    installment_number = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_days = models.PositiveIntegerField()

    class Meta:
        ordering = ['installment_number']
        unique_together = ['plan', 'installment_number']

    def __str__(self):
        return f"{self.plan} - Installment {self.installment_number}"

###############
class CourseInstallment(models.Model):#######
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="installments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_days_after_enrollment = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)


    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.course.title} - Installment {self.id}"

# enroll student with installment plan
class StudentCourseEnrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    installment_plan = models.ForeignKey(InstallmentPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    enrollment_date = models.DateField(auto_now_add=True)
    class Meta:
        unique_together = ['student', 'course']

    def save(self, *args, **kwargs):
        if self.batch:
            self.course = self.batch.course
        elif not self.course:
            raise ValueError("Course must be set either directly or via batch.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.profile.user.email} - {self.course.title}"

class CoursePayment(models.Model):
    PAYMENT_METHODS = [
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('upi', 'UPI'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="course_payments",
        null=True,
        blank=True
    )

    installments = models.ForeignKey(
        InstallmentItem,
        on_delete=models.CASCADE,
        related_name="course_payments",
        null=True,
        blank=True
    )

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS
    )

    transaction_id = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    payment_date = models.DateField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-payment_date"]



#################
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
        related_name='tasks'
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

#  Internship Application

from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from django.core.exceptions import ValidationError


# -----------------------------
# Validators
# -----------------------------
phone_validator = RegexValidator(
    regex=r'^\+?\d{10,15}$',
    message="Enter a valid phone number (10–15 digits, optional +)."
)


# -----------------------------
# Main Model
# -----------------------------
class InternshipApplication(models.Model):

    QUALIFICATION_CHOICES = [
        ('sslc', 'SSLC'),
        ('plus_two', 'Plus Two'),
        ('ug', 'Undergraduate'),
        ('pg', 'Postgraduate'),
    ]

    WHERE_DID_YOU_FIND_US_CHOICES = [
        ('google', 'Google'),
        ('social_media', 'Social Media'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    COURSE_TYPE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    # Basic Info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    primary_phone = models.CharField(max_length=15, validators=[phone_validator])
    secondary_phone = models.CharField(max_length=15, validators=[phone_validator], blank=True, null=True)

    email = models.EmailField(unique=False)
    dob = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    # Education
    qualification = models.CharField(max_length=20, choices=QUALIFICATION_CHOICES)
    course_name = models.CharField(max_length=255, blank=True, null=True)

    # Address
    address = models.TextField()
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # Source Info
    where_did_you_find_us = models.CharField(
        max_length=20,
        choices=WHERE_DID_YOU_FIND_US_CHOICES,
        blank=True,
        null=True
    )
    other_source = models.CharField(max_length=255, blank=True, null=True)

    # Course Info
    course_applied_for = models.CharField(max_length=255)
    course_duration = models.PositiveIntegerField(help_text="Duration in months")
    course_type = models.CharField(max_length=10, choices=COURSE_TYPE_CHOICES)

    # Profiles
    linkedin_profile_url = models.URLField(blank=True, null=True)
    github_profile_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)

    academic_counselor = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # -----------------------------
    # Validation Logic
    # -----------------------------
    def clean(self):
        # Handle "other" source logic
        if self.where_did_you_find_us == 'other' and not self.other_source:
            raise ValidationError("Please specify 'other_source' when selecting 'Other'.")

        if self.where_did_you_find_us != 'other' and self.other_source:
            raise ValidationError("'other_source' should only be filled when 'Other' is selected.")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


# -----------------------------
# Document Model
# -----------------------------
class InternshipDocument(models.Model):

    DOCUMENT_TYPE_CHOICES = [
        ('qualification', 'Qualification Document'),
        ('legal', 'Legal Document'),
    ]

    application = models.ForeignKey(
        InternshipApplication,
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )

    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, null=True, blank=True)

    file = models.FileField(
        upload_to='documents/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        ],
        null=True,
        blank=True
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        first_name = self.application.first_name if self.application else "No"
        last_name = self.application.last_name if self.application else "Application"
        return f"{self.document_type} - {first_name} {last_name} (ID: {self.id})"