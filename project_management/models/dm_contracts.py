from datetime import date
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from accounts.models import CustomUser, Customer


def dm_contract_attachment_path(instance, filename):
    safe_number = str(instance.contract.contract_number).replace('|', '_').replace('/', '_')
    return f"dm_contracts/{safe_number}/{filename}"


class DMPlatform(models.Model):
    """
    Reusable master table for Digital Marketing platforms
    (e.g., Instagram, Facebook, Google, Snapchat, YouTube, LinkedIn, Twitter, Pinterest, Threads, WhatsApp).
    """
    name = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Digital Marketing Platform'
        verbose_name_plural = 'Digital Marketing Platforms'

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()
            # Case-insensitive uniqueness check
            existing = DMPlatform.objects.filter(name__iexact=self.name)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({'name': f"A platform with the name '{self.name}' already exists."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DMWorkType(models.Model):
    """
    Reusable master table for Digital Marketing work types / deliverables
    (e.g., Poster, Reel, Campaign, Video, SEO, Blog Writing, Website Management, Ads Management, Thumbnail).
    """
    name = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Digital Marketing Work Type'
        verbose_name_plural = 'Digital Marketing Work Types'

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()
            # Case-insensitive uniqueness check
            existing = DMWorkType.objects.filter(name__iexact=self.name)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({'name': f"A work type with the name '{self.name}' already exists."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DMContract(models.Model):
    """
    Main Digital Marketing Contract model.
    Maintains client association, original schedule, and calculated extensions.
    """
    WORK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]

    contract_number = models.CharField(max_length=100, unique=True, db_index=True)
    client = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='dm_contracts',
        help_text="Customer record with module_type='client'"
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='dm_contracts',
        help_text="User who created/owns this contract"
    )
    contract_name = models.CharField(max_length=255)
    contract_date = models.DateField(default=date.today)
    description = models.TextField(blank=True, null=True)
    work_status = models.CharField(max_length=50, choices=WORK_STATUS_CHOICES, default='in_progress')
    start_date = models.DateField()
    original_end_date = models.DateField(help_text="Fixed original contract end date")
    duration = models.IntegerField(help_text="Original contract duration in days")
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Digital Marketing Contract'
        verbose_name_plural = 'Digital Marketing Contracts'

    def __str__(self):
        return f"{self.contract_number} - {self.contract_name} ({self.client})"

    def clean(self):
        super().clean()
        # Validate client is module_type='client'
        if self.client_id:
            if getattr(self.client, 'module_type', None) != 'client':
                raise ValidationError({'client': "Only converted clients (module_type='client') can have contracts."})

        # Validate start_date <= original_end_date
        if self.start_date and self.original_end_date:
            if self.original_end_date < self.start_date:
                raise ValidationError({'original_end_date': "End date cannot be earlier than start date."})

    def save(self, *args, **kwargs):
        # Calculate duration automatically if dates present
        if self.start_date and self.original_end_date:
            self.duration = (self.original_end_date - self.start_date).days
        self.clean()
        super().save(*args, **kwargs)

    @property
    def latest_extension(self):
        """Returns the latest valid contract extension if any exists."""
        return self.extensions.order_by('-extended_until', '-created_at').first()

    @property
    def revised_end_date(self):
        """Returns the current effective end date factoring in all extensions."""
        latest = self.latest_extension
        return latest.extended_until if latest else self.original_end_date

    @property
    def total_duration(self):
        """Total duration in days from start date to the latest revised end date."""
        effective_end = self.revised_end_date
        if self.start_date and effective_end:
            return (effective_end - self.start_date).days
        return self.duration

    @property
    def total_additional_days(self):
        """Sum of additional days granted across all extensions."""
        if not self.pk:
            return 0
        extensions = self.extensions.all()
        return sum(ext.additional_days for ext in extensions) if extensions.exists() else 0


class DMContractPlatform(models.Model):
    """
    Platform assignments for a Digital Marketing Contract.
    Prevents duplicate platform assignment within the same contract.
    """
    contract = models.ForeignKey(
        DMContract,
        on_delete=models.CASCADE,
        related_name='contract_platforms'
    )
    platform = models.ForeignKey(
        DMPlatform,
        on_delete=models.PROTECT,
        related_name='contract_platforms'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('contract', 'platform')
        ordering = ['platform__name']
        verbose_name = 'Contract Platform'
        verbose_name_plural = 'Contract Platforms'

    def __str__(self):
        return f"{self.contract.contract_number} - {self.platform.name}"


class DMContractWork(models.Model):
    """
    Work item deliverables for a Digital Marketing Contract.
    Supports both count-based deliverables (e.g. 20 Posters) and included services (e.g. SEO: Included).
    """
    QUANTITY_TYPE_CHOICES = [
        ('count', 'Count'),
        ('included', 'Included'),
    ]

    contract = models.ForeignKey(
        DMContract,
        on_delete=models.CASCADE,
        related_name='contract_works'
    )
    work_type = models.ForeignKey(
        DMWorkType,
        on_delete=models.PROTECT,
        related_name='contract_works'
    )
    quantity_type = models.CharField(
        max_length=20,
        choices=QUANTITY_TYPE_CHOICES,
        default='count'
    )
    quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Numeric quantity when quantity_type is 'count'"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('contract', 'work_type')
        ordering = ['work_type__name']
        verbose_name = 'Contract Work Deliverable'
        verbose_name_plural = 'Contract Work Deliverables'

    def clean(self):
        super().clean()
        if self.quantity_type == 'count':
            if self.quantity is None or self.quantity <= 0:
                raise ValidationError({'quantity': "A positive quantity is required when quantity type is 'count'."})
        elif self.quantity_type == 'included':
            # Always ensure quantity is null when included
            self.quantity = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        qty_str = f"{self.quantity}" if self.quantity_type == 'count' else "Included"
        return f"{self.contract.contract_number} - {self.work_type.name}: {qty_str}"


class DMContractLink(models.Model):
    """
    Social profile / reference URLs linked to a contract.
    """
    contract = models.ForeignKey(
        DMContract,
        on_delete=models.CASCADE,
        related_name='contract_links'
    )
    url = models.URLField(max_length=500)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name = 'Contract Link'
        verbose_name_plural = 'Contract Links'

    def __str__(self):
        return f"{self.contract.contract_number} - {self.url}"


class DMContractAttachment(models.Model):
    """
    Uploaded contract attachments (PDFs, images, documents).
    """
    ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'webp', 'zip']

    contract = models.ForeignKey(
        DMContract,
        on_delete=models.CASCADE,
        related_name='contract_attachments'
    )
    file = models.FileField(
        upload_to=dm_contract_attachment_path,
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)]
    )
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.PositiveIntegerField(blank=True, null=True, help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Contract Attachment'
        verbose_name_plural = 'Contract Attachments'

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            # Extract plain filename from file object
            self.file_name = self.file.name.split('/')[-1].split('\\')[-1]
        if self.file and hasattr(self.file, 'size') and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract.contract_number} - {self.file_name or self.file.name}"


class DMContractExtension(models.Model):
    """
    Contract Extension history record.
    Preserves original end date snapshot, previous effective end date, and calculates additional days.
    """
    contract = models.ForeignKey(
        DMContract,
        on_delete=models.CASCADE,
        related_name='extensions'
    )
    original_end_date = models.DateField(help_text="Snapshot of contract original end date")
    previous_effective_end_date = models.DateField(help_text="Effective end date prior to this extension")
    extended_until = models.DateField(help_text="New extended end date")
    additional_days = models.IntegerField(help_text="Backend calculated additional days")
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='+'
    )
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contract Extension'
        verbose_name_plural = 'Contract Extensions'

    def clean(self):
        super().clean()
        if self.extended_until and self.previous_effective_end_date:
            if self.extended_until <= self.previous_effective_end_date:
                raise ValidationError({
                    'extended_until': f"Extended until date ({self.extended_until}) must be strictly later than current effective end date ({self.previous_effective_end_date})."
                })

    def save(self, *args, **kwargs):
        if self.extended_until and self.previous_effective_end_date:
            self.additional_days = (self.extended_until - self.previous_effective_end_date).days
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract.contract_number} extended to {self.extended_until} (+{self.additional_days}d)"
