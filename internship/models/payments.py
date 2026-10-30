from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from .academic import Course, Batch
from .student import Student

PAYMENT_METHODS = [
    ('card', 'Card'),
    ('bank_transfer', 'Bank Transfer'),
    ('cash', 'Cash'),
    ('upi', 'UPI'),
]


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


class StudentCourseEnrollment(models.Model):

    PAYMENT_PLAN_TYPES = [
    ("default_installment", "Default Installment"),
    ("custom_installment", "Custom Installment"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    installment_plan = models.ForeignKey(InstallmentPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    enrollment_date = models.DateField(auto_now_add=True)

    # Snapshot of course fee agreed upon at enrollment
    course_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Snapshot of the course fee agreed upon at enrollment"
    )

    # advance payment fields
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    transaction_id = models.CharField(max_length=200, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)

    # methid1 and methid 2 fields

    payment_plan_type = models.CharField(max_length=30, choices=PAYMENT_PLAN_TYPES, default="default_installment")
    custom_installments = models.PositiveIntegerField(null=True, blank=True)

    # descount integrations model
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_reason = models.TextField(blank=True, null=True)

    application = models.ForeignKey("InternshipApplication", on_delete=models.PROTECT, related_name="enrollments", null=True, blank=True)
    class Meta:
        unique_together = ['student', 'course']
        
    def save(self, *args, **kwargs):
        from decimal import Decimal
        from internship.models import StudentInstallmentItem, CoursePayment

        old_plan_id = None
        old_payment_plan_type = None
        old_custom_installments = None
        old_discount_amount = None
        old_advance_amount = None
        old_course_fee = None

        # -------------------------------------------------
        # Only fetch old values while updating
        # -------------------------------------------------
        if self.pk:
            try:
                old_data = StudentCourseEnrollment.objects.filter(
                    pk=self.pk
                ).values(
                    "installment_plan_id",
                    "payment_plan_type",
                    "custom_installments",
                    "discount_amount",
                    "advance_amount",
                    "course_fee",
                ).first()

                if old_data:
                    old_plan_id = old_data["installment_plan_id"]
                    old_payment_plan_type = old_data["payment_plan_type"]
                    old_custom_installments = old_data["custom_installments"]
                    old_discount_amount = old_data["discount_amount"]
                    old_advance_amount = old_data["advance_amount"]
                    old_course_fee = old_data["course_fee"]

            except Exception:
                pass

        # -------------------------------------------------
        # Detect payment structure change
        # (ONLY FOR UPDATE)
        # -------------------------------------------------
        payment_structure_changed = False

        if self.pk:
            payment_structure_changed = (
                old_plan_id != self.installment_plan_id
                or old_payment_plan_type != self.payment_plan_type
                or old_custom_installments != self.custom_installments
                or Decimal(str(old_discount_amount or 0))
                != Decimal(str(self.discount_amount or 0))
                or Decimal(str(old_advance_amount or 0))
                != Decimal(str(self.advance_amount or 0))
                or Decimal(str(old_course_fee or 0))
                != Decimal(str(self.course_fee or 0))
            )

        # -------------------------------------------------
        # Assign Course
        # -------------------------------------------------
        if self.batch:
            self.course = self.batch.course
        elif not self.course:
            raise ValueError(
                "Course must be set either directly or via batch."
            )

        # -------------------------------------------------
        # Snapshot Course Fee if not already set
        # -------------------------------------------------
        if self.course_fee is None and self.course:
            self.course_fee = self.course.total_fee

        super().save(*args, **kwargs)

        # -------------------------------------------------
        # Delete old installment items
        # -------------------------------------------------
        if payment_structure_changed:
            self.student_installment_items.all().delete()

        # -------------------------------------------------
        # Create Installment Items
        # -------------------------------------------------
        if not self.student_installment_items.exists():

            course_fee = Decimal(str(self.course_fee or (self.course.total_fee if self.course else 0)))

            slot_amount = Decimal(
                str(self.student.slot_amount or 0)
            )

            remaining_fee = course_fee - slot_amount

            discount_amount = Decimal(
                str(self.discount_amount or 0)
            )

            discounted_fee = remaining_fee - discount_amount

            advance_amount = Decimal(
                str(self.advance_amount or 0)
            )

            balance_fee = discounted_fee - advance_amount

            student_items = []

            # ==========================================
            # DEFAULT INSTALLMENT
            # ==========================================
            if self.payment_plan_type == "default_installment":

                if not self.installment_plan:
                    raise ValidationError(
                        "Installment plan is required."
                    )

                global_items = list(
                    self.installment_plan.items.all().order_by(
                        "installment_number"
                    )
                )

                total_installments = len(global_items)

                if total_installments == 0:
                    raise ValidationError(
                        "Selected installment plan has no installment items."
                    )

                installment_amount = (
                    balance_fee / total_installments
                ).quantize(Decimal("0.01"))

                for index, item in enumerate(
                    global_items,
                    start=1
                ):

                    amount = installment_amount

                    if index == total_installments:

                        assigned_total = (
                            installment_amount
                            * (total_installments - 1)
                        )

                        amount = (
                            balance_fee
                            - assigned_total
                        )

                    student_items.append(
                        StudentInstallmentItem(
                            enrollment=self,
                            installment_number=item.installment_number,
                            amount=amount,
                            due_days=item.due_days,
                        )
                    )

            # ==========================================
            # CUSTOM INSTALLMENT
            # ==========================================
            elif self.payment_plan_type == "custom_installment":

                if not self.custom_installments:
                    raise ValidationError(
                        "Custom installments are required."
                    )

                total_installments = self.custom_installments

                installment_amount = (
                    balance_fee / total_installments
                ).quantize(Decimal("0.01"))

                DEFAULT_INTERVAL_DAYS = 30

                for number in range(
                    1,
                    total_installments + 1
                ):

                    amount = installment_amount

                    if number == total_installments:

                        assigned_total = (
                            installment_amount
                            * (total_installments - 1)
                        )

                        amount = (
                            balance_fee
                            - assigned_total
                        )

                    student_items.append(
                        StudentInstallmentItem(
                            enrollment=self,
                            installment_number=number,
                            amount=amount,
                            due_days=number * DEFAULT_INTERVAL_DAYS,
                        )
                    )

            else:
                raise ValidationError(
                    "Invalid payment plan type."
                )

            StudentInstallmentItem.objects.bulk_create(
                student_items
            )

        # -------------------------------------------------
        # Create Advance Payment
        # -------------------------------------------------
        if self.advance_amount and self.advance_amount > 0:

            advance_exists = CoursePayment.objects.filter(
                enrollment=self,
                payment_type="advance",
            ).exists()

            if not advance_exists:

                CoursePayment.objects.create(
                    enrollment=self,
                    student=self.student,
                    installments=None,
                    amount_paid=self.advance_amount,
                    payment_method=self.payment_method,
                    transaction_id=self.transaction_id,
                    payment_type="advance",
                    payment_date=self.payment_date,
                )


    @property
    def effective_course_fee(self):
        from decimal import Decimal
        if self.course_fee is not None:
            return Decimal(str(self.course_fee))
        if self.course and getattr(self.course, "total_fee", None) is not None:
            return Decimal(str(self.course.total_fee))
        return Decimal("0.00")

    @property
    def effective_slot_amount(self):
        from decimal import Decimal
        if self.student and self.student.slot_amount is not None:
            return Decimal(str(self.student.slot_amount))
        if self.application and self.application.slot_amount is not None:
            return Decimal(str(self.application.slot_amount))
        return Decimal("0.00")

    @property
    def effective_discounted_fee(self):
        from decimal import Decimal
        discount = Decimal(str(self.discount_amount or 0))
        net = self.effective_course_fee - self.effective_slot_amount - discount
        return max(Decimal("0.00"), net)

    @property
    def effective_balance_fee(self):
        from decimal import Decimal
        advance = Decimal(str(self.advance_amount or 0))
        balance = self.effective_discounted_fee - advance
        return max(Decimal("0.00"), balance)

    @property
    def total_paid_amount(self):
        from decimal import Decimal
        payments = [
            p for p in self.student.course_payments.all()
            if p.enrollment_id == self.id
        ]
        return sum((p.amount_paid for p in payments), Decimal("0.00"))

    @property
    def pending_balance(self):
        from decimal import Decimal
        return max(Decimal("0.00"), self.effective_discounted_fee - self.total_paid_amount)

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
