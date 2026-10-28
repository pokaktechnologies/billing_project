from django.db import models
from django.core.validators import FileExtensionValidator
from .academic import Course, Batch, Faculty
from .student import Student

def recorded_class_upload_path(instance, filename):
    course_id = instance.batch.course_id if instance.batch else instance.course_id
    batch_id = instance.batch_id if instance.batch_id else "general"
    return f"recorded_classes/course_{course_id}/batch_{batch_id}/{filename}"


class RecordedClass(models.Model):
    SOURCE_CHOICES = [
        ('upload', 'Direct VPS Upload'),
        ('livekit_recording', 'LiveKit Recorded Session'),
        ('external_url', 'External URL / Embed'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Association with Course & Batch
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="recorded_classes"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_classes",
        help_text="Optional: Leave blank if the recording is common to all batches in this course"
    )
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_classes"
    )

    # Video storage & source
    source_type = models.CharField(
        max_length=25,
        choices=SOURCE_CHOICES,
        default='upload'
    )
    video_file = models.FileField(
        upload_to=recorded_class_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mkv', 'webm', 'mov'])],
        null=True,
        blank=True,
        help_text="Uploaded directly to VPS media storage"
    )
    external_url = models.URLField(
        blank=True,
        null=True,
        help_text="External video link, stream URL, or future LiveKit recording link"
    )

    # Metadata
    thumbnail = models.ImageField(
        upload_to="recorded_classes/thumbnails/",
        null=True,
        blank=True
    )
    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Video duration in seconds"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order or lesson index"
    )

    # Status
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def video_stream_url(self):
        """Returns direct VPS media file URL or external URL"""
        if self.video_file:
            return self.video_file.url
        return self.external_url


class LiveClass(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="live_classes"
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="live_classes",
        help_text="Optional: specific batch, or null if open to the entire course"
    )
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="live_classes"
    )

    room_name = models.CharField(
        max_length=150,
        unique=True,
        help_text="Unique room name identifier for LiveKit"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )

    scheduled_start_time = models.DateTimeField()
    scheduled_end_time = models.DateTimeField(null=True, blank=True)

    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)

    is_recording_enabled = models.BooleanField(
        default=False,
        help_text="Indicates whether LiveKit session should be recorded"
    )
    recorded_class = models.OneToOneField(
        RecordedClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_live_class",
        help_text="Link to RecordedClass once recording is processed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_start_time', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()}) - {self.course.title}"


class LiveClassAttendance(models.Model):
    live_class = models.ForeignKey(
        LiveClass,
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="live_class_attendances"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.student} in {self.live_class.title}"
