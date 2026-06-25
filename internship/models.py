from django.db import models
from accounts.models import Department, SalesPerson, StaffProfile
from project_management.models import STATUS_CHOICES

PAYMENT_METHODS = [
    ('card', 'Card'),
    ('bank_transfer', 'Bank Transfer'),
    ('cash', 'Cash'),
    ('upi', 'UPI'),
]

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
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, related_name="students") # Unused
    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name="students") # Unused
    payment_type = models.ForeignKey('InstallmentPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name="students") # Unused
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    STATUS_CHOICES = [
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    councellor = models.ForeignKey(SalesPerson, on_delete=models.SET_NULL, null=True, blank=True, related_name="counselled_students")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def get_full_name(self):
        user = self.profile.user
        return f"{user.first_name} {user.last_name}"
    
    def __str__(self):
        return self.profile.user.first_name

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

# class CourseFaculty(models.Model):
#     faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="course_faculties")
#     department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="course_faculties")
#     is_active = models.BooleanField(default=True)
#     def __str__(self):
#         return self.faculty.user.user.first_name
    
#     def get_full_name(self):
#         user = self.faculty.user.user
#         return f"{user.first_name} {user.last_name}"

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

    # advance payment fields
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    transaction_id = models.CharField(max_length=200, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    class Meta:
        unique_together = ['student', 'course']

    def save(self, *args, **kwargs):
        old_plan_id = None
        if self.pk:
            try:
                old_plan_id = StudentCourseEnrollment.objects.filter(pk=self.pk).values_list('installment_plan_id', flat=True).first()
            except Exception:
                pass

        if old_plan_id and old_plan_id != self.installment_plan_id:
            from .models import CoursePayment
            has_payments = CoursePayment.objects.filter(
                student_installment__enrollment=self
            ).exists()
            
            if has_payments:
                raise ValidationError(
                    "Cannot change installment plan because payments have already been made under the current plan."
                )

        if self.batch:
            self.course = self.batch.course
        elif not self.course:
            raise ValueError("Course must be set either directly or via batch.")
        
        super().save(*args, **kwargs)

        if old_plan_id and old_plan_id != self.installment_plan_id:
            self.student_installment_items.all().delete()

        if self.installment_plan and not self.student_installment_items.exists():
            from .models import StudentInstallmentItem
            from decimal import Decimal

            # global_items = self.installment_plan.items.all()  # old code 
            global_items = list(self.installment_plan.items.all().order_by('installment_number'))  
            total_installment = len(global_items)

            if total_installment == 0:
                return
            
            course_fee = Decimal(self.course.total_fee)
            advance_amount = Decimal(self.advance_amount or 0)
            balance_fee = course_fee - advance_amount

            installment_amount = (
                balance_fee / total_installment
            ).quantize(Decimal('0.01'))
            
            student_items = []

            for index, item in enumerate(global_items, start=1):
                amount = installment_amount

                if index == total_installment:
                    assignment_total = installment_amount * (total_installment - 1)

                    amount = balance_fee - assignment_total

                student_items.append(
                    StudentInstallmentItem(
                        enrollment=self,
                        installment_number=item.installment_number,
                        amount=amount,
                        due_days=item.due_days
                    )
                )
            
            StudentInstallmentItem.objects.bulk_create(student_items)
            from .models import CoursePayment

            if self.advance_amount and self.advance_amount > 0:
                advance_exist = CoursePayment.objects.filter(
                    enrollment=self,
                    payment_type='advance'
                ).exists()

                if not advance_exist:
                    CoursePayment.objects.create(
                        enrollment=self,
                        student=self.student,
                        installments=None,
                        amount_paid=self.advance_amount,
                        payment_method=self.payment_method,
                        transaction_id=self.transaction_id,
                        payment_type='advance',
                        payment_date=self.payment_date
                    )

    def __str__(self):
        return f"{self.student.profile.user.email} - {self.course.title}"


class StudentInstallmentItem(models.Model):
    enrollment = models.ForeignKey(
        'StudentCourseEnrollment',
        on_delete=models.CASCADE,
        related_name="student_installment_items"
    )
    installment_number = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_days = models.PositiveIntegerField()

    class Meta:
        ordering = ['installment_number']
        unique_together = ['enrollment', 'installment_number']

    def __str__(self):
        return f"{self.enrollment.student} - Installment {self.installment_number} ({self.amount})"


class CoursePayment(models.Model):
    PAYMENT_METHODS = [
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('upi', 'UPI'),
    ]

    PAYMENT_TYPES = [
        ('advance', 'Advance'),
        ('installment', 'Installment'),
    ]

    enrollment = models.ForeignKey(
        'StudentCourseEnrollment',
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="course_payments",
        null=True,
        blank=True
    )

    # installments = models.ForeignKey(
    #     InstallmentItem,
    #     on_delete=models.CASCADE,
    #     related_name="course_payments",
    #     null=True,
    #     blank=True
    # )

    installments = models.ForeignKey(StudentInstallmentItem, on_delete=models.PROTECT, related_name="course_payments", null=True, blank=True)

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

    payment_date = models.DateField()

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='installment'
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



# Test models

class Test(models.Model):
    TEST_TYPE_CHOICES = [
        ('mcq', 'MCQ'),
        ('descriptive', 'Descriptive'),
        ('mixed', 'Mixed'),
    ]

    name = models.CharField(max_length=200)
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    course = models.ForeignKey(
        'Course', on_delete=models.CASCADE, related_name='tests'
    )
    batch = models.ForeignKey(
        'Batch', on_delete=models.CASCADE, related_name='tests'
    )
    duration_minutes = models.PositiveIntegerField()
    total_marks = models.PositiveIntegerField()
    instructions = models.TextField(blank=True, null=True)

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.batch_id:
            self.course = self.batch.course
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TestSection(models.Model):
    SECTION_TYPE_CHOICES = [
        ('mcq', 'MCQ'),
        ('descriptive', 'Descriptive'),
    ]

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=100)          # Part A, Part B ...
    section_type = models.CharField(max_length=20, choices=SECTION_TYPE_CHOICES)
    marks = models.PositiveIntegerField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.test.name} - {self.name}"


class TestQuestion(models.Model):
    section = models.ForeignKey(
        TestSection, on_delete=models.CASCADE, related_name='questions'
    )
    question_text = models.TextField()
    marks = models.PositiveIntegerField(null=True, blank=True)
    file = models.FileField(upload_to='test_questions/', null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    # Descriptive specific
    word_limit = models.PositiveIntegerField(null=True, blank=True)
    manual_evaluation = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order} - {self.section.name}"


class QuestionOption(models.Model):
    question = models.ForeignKey(
        TestQuestion, on_delete=models.CASCADE, related_name='options'
    )
    label = models.CharField(max_length=5)       # A, B, C, D
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ['label']

    def __str__(self):
        return f"{self.question} - {self.label}"


# models.py

class TestAttempt(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='test_attempts'
    )
    test = models.ForeignKey(
        Test, on_delete=models.CASCADE, related_name='attempts'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(null=True, blank=True)
    overall_feedback = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ['student', 'test']

    def __str__(self):
        return f"{self.student} - {self.test.name} [{self.status}]"


class TestAnswer(models.Model):
    attempt = models.ForeignKey(
        TestAttempt, on_delete=models.CASCADE, related_name='answers'
    )
    question = models.ForeignKey(
        TestQuestion, on_delete=models.CASCADE, related_name='answers'
    )

    # MCQ — selected option
    selected_option = models.ForeignKey(
        QuestionOption, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='answers'
    )

    # Descriptive — text answer
    text_answer = models.TextField(null=True, blank=True)

    # Instructor feedback (descriptive)
    marks_awarded = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    is_marked_for_review = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['attempt', 'question']  # per question ഒരു answer

    def __str__(self):
        return f"{self.attempt} - Q{self.question.id}"

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




# report based models

class ReportTemplate(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="report_templates")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class TemplateSection(models.Model):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=250)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.template.name} - {self.title}"


class TemplateField(models.Model):
    FIELD_TYPES = [
        ("text", "Text"),
        ("number", "Number"),
        ("rating", "Rating"),
        ("dropdown", "Dropdown"),
        ("table", "Table"),
        ("textarea", "Textarea"),
        ("checkbox_grid", "Checkbox Grid")
    ]

    section = models.ForeignKey(TemplateSection, on_delete=models.CASCADE, related_name="fields")
    label = models.CharField(max_length=250)
    field_type =models.CharField(max_length=20, choices=FIELD_TYPES)
    placeholder = models.CharField(max_length=250, blank=True, null=True)
    is_required = models.BooleanField(default=False)
    order = models.PositiveBigIntegerField(default=0)
    config = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.section.title} - {self.label}"


class StudentReport(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="reports")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="reports")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reports")
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_reports")
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_reports")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["student", "batch"]

    def save(self, *args, **kwargs):
        if self.batch_id:
            self.course = self.batch.course
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.template.name if self.template else 'No Template'}"

class ReportFieldValue(models.Model):
    report = models.ForeignKey(StudentReport, on_delete=models.CASCADE,related_name="field_values")
    field = models.ForeignKey(TemplateField, on_delete=models.CASCADE,related_name="field_values")
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["report", "field"]

    def __str__(self):
        return f"{self.report} - {self.field.label}"