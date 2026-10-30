from django.db import models
from django.conf import settings
from .academic import Course, Batch
from .student import Student

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
