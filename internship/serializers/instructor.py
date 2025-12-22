from rest_framework import serializers
from internship.models import *
from accounts.models import StaffProfile
from accounts.serializers.user import *


class SimpleStaffProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = ["id", "user_email", "full_name"]

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class CourseInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseInstallment
        fields = [
            "id",
            "amount",
            "due_days_after_enrollment",
        ]


class CourseSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True
    )
    installments = CourseInstallmentSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "department",
            "department_name",
            "total_fee",
            "number_of_installments",
            "installments",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, data):
        installments = data.get("installments", [])
        total_fee = data.get("total_fee", getattr(self.instance, "total_fee", None))

        if installments:
            total = sum(i["amount"] for i in installments)

            if total != total_fee:
                raise serializers.ValidationError(
                    "Sum of installment amounts must equal total_fee."
                )

            if self.instance is None:
                expected_count = data.get("number_of_installments")
            else:
                expected_count = data.get(
                    "number_of_installments",
                    self.instance.number_of_installments
                )

            if len(installments) != expected_count:
                raise serializers.ValidationError(
                    "Installment count must match number_of_installments."
                )

        return data

    def create(self, validated_data):
        installments_data = validated_data.pop("installments", [])
        course = Course.objects.create(**validated_data)

        for inst in installments_data:
            CourseInstallment.objects.create(
                course=course,
                **inst
            )

        return course

    def update(self, instance, validated_data):
        installments_data = validated_data.pop("installments", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if installments_data is not None:
            # Hard reset installments (simple & predictable)
            instance.installments.all().delete()

            for inst in installments_data:
                CourseInstallment.objects.create(
                    course=instance,
                    **inst
                )

        return instance

class CoursePaymentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(
        source="installment.course.title",
        read_only=True
    )

    installment_amount = serializers.DecimalField(
        source="installment.amount",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = CoursePayment
        fields = [
            "id",
            "staff",
            "installment",
            "course_title",
            "installment_amount",
            "amount_paid",
            "payment_method",
            "transaction_id",
            "payment_date",
        ]
        read_only_fields = ["payment_date"]

    def validate(self, data):
        staff = data["staff"]
        installment = data["installment"]
        amount_paid = data["amount_paid"]
        payment_method = data["payment_method"]
        transaction_id = data.get("transaction_id")

        course = installment.course

        # --------------------------------------------------
        # Rule 1: Staff must be assigned to this course
        # --------------------------------------------------
        if not AssignedStaffCourse.objects.filter(
            staff=staff,
            course=course
        ).exists():
            raise serializers.ValidationError(
                "Staff is not assigned to this course."
            )

        # --------------------------------------------------
        # Rule 2: Transaction ID required for non-cash
        # --------------------------------------------------
        if payment_method != "cash" and not transaction_id:
            raise serializers.ValidationError(
                "Transaction ID is required for non-cash payments."
            )

        # --------------------------------------------------
        # Rule 3: Installment must be paid in FULL (no partials)
        # --------------------------------------------------
        if amount_paid != installment.amount:
            raise serializers.ValidationError(
                "Installment must be paid in full."
            )

        # --------------------------------------------------
        # Rule 4: Prevent duplicate payment of same installment
        # --------------------------------------------------
        if installment.payments.filter(staff=staff).exists():
            raise serializers.ValidationError(
                "This installment has already been paid."
            )

        return data

    def update(self, instance, validated_data):
        # Immutable financial records
        raise serializers.ValidationError(
            "Payments cannot be updated once created."
        )

# class CoursePaymentListSerializer(serializers.ModelSerializer):
#     staff_full_name = serializers.SerializerMethodField()
#     employee_id = serializers.CharField(source="staff.job_detail.employee_id", read_only=True)
#     course_title = serializers.CharField(source="installment.course.title", read_only=True)
#     course_total_fee = serializers.CharField(source="installment.course.total_fee", read_only=True)
#     installment_amount = serializers.DecimalField(source="installment.amount",max_digits=10,decimal_places=2,read_only=True)
#     pending_fee = serializers.SerializerMethodField()
#     next_due_date = serializers.SerializerMethodField()

#     class Meta:
#         model = CoursePayment
#         fields = [
#             "id",
#             "staff",
#             "staff_full_name",
#             "employee_id",
#             "course_title",
#             "course_total_fee",
#             "installment",
#             "installment_amount",
#             "amount_paid",
#             "pending_fee",
#             "next_due_date",
#             "payment_method",
#             "transaction_id",
#             "payment_date"
#         ]

#     def get_staff_full_name(self, obj):
#         return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"
    
#     def get_pending_fee(self, obj):
#         course = obj.installment.course
#         total_paid = CoursePayment.objects.filter(
#             staff=obj.staff,
#             installment__course=course
#         ).aggregate(total=models.Sum('amount_paid'))['total'] or 0
#         pending = course.total_fee - total_paid
#         return pending
    
#     def get_next_due_date(self, obj):
#         course = obj.installment.course
#         staff = obj.staff
#         next_installment = CourseInstallment.objects.filter(
#             course=course,
#             payments__staff=staff
#         ).order_by('due_days_after_enrollment').last()
#         if next_installment:
#             enrollment = AssignedStaffCourse.objects.filter(
#                 course=course,
#                 staff=staff
#             ).first()
#             if enrollment:
#                 enrollment_date = enrollment.assigned_date
#                 due_date = enrollment_date + timezone.timedelta(days=next_installment.due_days_after_enrollment)
#                 return due_date
#         return None



class CourceInstallmentListSerializer(serializers.ModelSerializer):
    # installment_no = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    due_date = serializers.SerializerMethodField()
    paid_date = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = CourseInstallment
        fields = [
            "id",
            # "installment_no",
            "amount",
            "status",
            "due_date",
            "paid_date",
            "payment_method",
        ]

    #  Get payment ONLY for this staff
    def get_payment(self, obj):
        staff = self.context.get("staff")
        if not staff:
            return None
        return obj.payments.filter(staff=staff).order_by("-payment_date").first()

    # #  Installment number (1,2,3…)
    # def get_installment_no(self, obj):
    #     ids = list(
    #         obj.course.installments
    #         .order_by("due_days_after_enrollment")
    #         .values_list("id", flat=True)
    #     )
    #     return f"#{ids.index(obj.id) + 1}"

    #  Paid / Pending (staff-specific)
    def get_status(self, obj):
        return "Paid" if self.get_payment(obj) else "Pending"

    #  Paid date
    def get_paid_date(self, obj):
        payment = self.get_payment(obj)
        return payment.payment_date if payment else None

    #  Payment method
    def get_payment_method(self, obj):
        payment = self.get_payment(obj)
        return payment.payment_method if payment else "-"

    #  Due date (based on staff enrollment)
    def get_due_date(self, obj):
        staff = self.context.get("staff")
        enrollment = AssignedStaffCourse.objects.filter(
            course=obj.course,
            staff=staff
        ).first()

        if enrollment:
            return enrollment.assigned_date + timezone.timedelta(
                days=obj.due_days_after_enrollment
            )
        return None




class CoursePaymentDetailSerializer(serializers.ModelSerializer):
    staff_full_name = serializers.SerializerMethodField()
    employee_id = serializers.CharField(source="staff.job_detail.employee_id", read_only=True)
    phone_number = serializers.CharField(source="staff.phone_number", read_only=True)
    email = serializers.CharField(source="staff.user.email", read_only=True)
    course_title = serializers.CharField(source="installment.course.title", read_only=True)
    course_id = serializers.CharField(source="installment.course.id", read_only=True)

    course_total_fee = serializers.CharField(source="installment.course.total_fee", read_only=True)
    total_paid = serializers.SerializerMethodField()
    pending_fee = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()

    installment_list = CourceInstallmentListSerializer(many=True, source="installment.course.installments", read_only=True)




    class Meta:
        model = CoursePayment
        fields = [
            "id",
            "staff",
            "staff_full_name",
            "employee_id",
            "phone_number",
            "email",
            "course_title",
            "course_id",
            # "installment",

            "course_total_fee",
            "total_paid",
            "pending_fee",
            "next_due_date",

            "installment_list",
        ]

    def get_staff_full_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"
    
    def get_total_paid(self, obj):
        course = obj.installment.course
        total_paid = CoursePayment.objects.filter(
            staff=obj.staff,
            installment__course=course
        ).aggregate(total=models.Sum('amount_paid'))['total'] or 0
        return total_paid

    def get_pending_fee(self, obj):
        course = obj.installment.course
        total_paid = self.get_total_paid(obj)
        pending = course.total_fee - total_paid
        return pending
    
    def get_next_due_date(self, obj):
        course = obj.installment.course
        staff = obj.staff
        next_installment = CourseInstallment.objects.filter(
            course=course,
            payments__staff=staff
        ).order_by('due_days_after_enrollment').last()
        if next_installment:
            enrollment = AssignedStaffCourse.objects.filter(
                course=course,
                staff=staff
            ).first()
            if enrollment:
                enrollment_date = enrollment.assigned_date
                due_date = enrollment_date + timezone.timedelta(days=next_installment.due_days_after_enrollment)
                return due_date
        return None
    
    def to_representation(self, instance):
        self.fields["installment_list"].context.update({
            "staff": instance.staff
        })
        return super().to_representation(instance)


class AssignedStaffCourseSerializer(serializers.ModelSerializer):
    staff = serializers.IntegerField(source="staff.id", read_only=True)
    staff_email = serializers.CharField(source="staff.user.email", read_only=True)
    staff_full_name = serializers.SerializerMethodField()
    course = serializers.IntegerField(source="course.id", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = AssignedStaffCourse
        fields = [
            "id",
            "staff",
            "staff_email",
            "staff_full_name",
            "course",
            "course_title",
            "assigned_date",
        ]

    def get_staff_full_name(self, obj):
        return f"{obj.staff.user.first_name} {obj.staff.user.last_name}"




# ====== BULK CREATE SERIALIZER ======
class AssignedStaffCourseCreateSerializer(serializers.Serializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    staff_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    def validate(self, attrs):
        course = attrs["course"]
        staff_ids = attrs["staff_ids"]

        staff_qs = StaffProfile.objects.filter(id__in=staff_ids)
        found_ids = set(staff_qs.values_list("id", flat=True))

        # Missing staff
        missing = [sid for sid in staff_ids if sid not in found_ids]
        if missing:
            raise serializers.ValidationError({
                "staff_ids": f"Staff ids not found: {missing}"
            })

        # Staff already assigned
        existing = AssignedStaffCourse.objects.filter(
            course=course, staff__in=staff_qs
        ).values_list("staff_id", flat=True)

        existing_list = list(existing)
        if existing_list:
            raise serializers.ValidationError({
                "staff_ids": f"Staff already assigned to the course: {existing_list}"
            })

        # Validate job_type
        invalid = []
        for s in staff_qs:
            jd = getattr(s, "job_detail", None)
            if not jd or (jd.job_type or "").lower() != "internship":
                invalid.append(s.id)

        if invalid:
            raise serializers.ValidationError({
                "staff_ids": f"These staff are not internship staff: {invalid}"
            })

        attrs["staff_qs"] = staff_qs
        return attrs


    def create(self, validated_data):
        course = validated_data["course"]
        staff_qs = validated_data["staff_qs"]

        existing = AssignedStaffCourse.objects.filter(
            course=course, staff__in=staff_qs
        ).values_list("staff_id", flat=True)

        to_create = [
            AssignedStaffCourse(course=course, staff=sp)
            for sp in staff_qs if sp.id not in existing
        ]

        return AssignedStaffCourse.objects.bulk_create(to_create)


# ====== DETAIL SERIALIZER (GET/PUT/PATCH/DELETE) ======
class AssignedStaffCourseDetailSerializer(serializers.ModelSerializer):
    Staff_email = serializers.CharField(source="staff.user.email", read_only=True)
    course_details = CourseSerializer(source="course", read_only=True)
    
    class Meta:
        model = AssignedStaffCourse
        fields = ["id", "staff", "course", "assigned_date", "Staff_email", "course_details"]

    def validate(self, attrs):
        staff = attrs.get("staff", getattr(self.instance, "staff", None))
        course = attrs.get("course", getattr(self.instance, "course", None))

        jd = getattr(staff, "job_detail", None)
        if not jd or (jd.job_type or "").lower() != "internship":
            raise serializers.ValidationError({
                "staff": "Staff must have job_type 'internship'."
            })

        qs = AssignedStaffCourse.objects.filter(staff=staff, course=course)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "This staff is already assigned."
            )
        return attrs

# ====== Study Material Serializer ======
    
class StudyMaterialSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudyMaterial
        fields = "__all__"

    def validate(self, attrs):
        file = attrs.get("file")
        url = attrs.get("url")

        if not file and not url:
            raise serializers.ValidationError("Either file or url is required.")
        return attrs


class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ['id', 'file']


class TaskAssignmentSerializer(serializers.ModelSerializer):
    staff = SimpleStaffProfileSerializer(read_only=True)

    class Meta:
        model = TaskAssignment
        fields = "__all__"

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    assigned_to_ids = serializers.SerializerMethodField()

    total_staff_count = serializers.SerializerMethodField()
    attachments = TaskAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description',
            'start_date', 'due_date', 'course',
            'assigned_to', 'attachments',
            'total_staff_count', 'assigned_to_ids'
        ]

    def get_total_staff_count(self, obj):
        return obj.assigned_to.count()
    
    def get_assigned_to_ids(self, obj):
        return list(obj.assigned_to.values_list('id', flat=True))

    # ===== CREATE =====
    def create(self, validated_data):
        staff_ids = validated_data.pop('assigned_to', [])
        request = self.context['request']
        files = request.FILES.getlist('files')
        course = validated_data.get("course")

        if not course:
            raise serializers.ValidationError({"course": "Course is required."})

        valid_staff_ids = AssignedStaffCourse.objects.filter(
            course=course,
            staff_id__in=staff_ids
        ).values_list("staff_id", flat=True)

        invalid_staff = set(staff_ids) - set(valid_staff_ids)

        # friendly message
        if invalid_staff:
            staff_info = StaffProfile.objects.filter(id__in=invalid_staff).values(
                "user__email",
                "user__first_name",
                "user__last_name"
            )
            readable = [
                f"{s['user__first_name']} {s['user__last_name']} ({s['user__email']})"
                for s in staff_info
            ]
            raise serializers.ValidationError({
                "assigned_to": "These staff are not assigned to this course: " + ", ".join(readable)
            })

        task = Task.objects.create(**validated_data)

        for staff_id in valid_staff_ids:
            TaskAssignment.objects.create(task=task, staff_id=staff_id)

        for file in files:
            TaskAttachment.objects.create(task=task, file=file)

        return task


    # ===== UPDATE =====
    def update(self, instance, validated_data):
        staff_ids = validated_data.pop('assigned_to', None)
        request = self.context['request']
        files = request.FILES.getlist('files')

        # update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if staff_ids is not None:
            course = instance.course

            valid_staff_ids = AssignedStaffCourse.objects.filter(
                course=course,
                staff_id__in=staff_ids
            ).values_list("staff_id", flat=True)

            invalid_staff = set(staff_ids) - set(valid_staff_ids)

            if invalid_staff:
                staff_info = StaffProfile.objects.filter(id__in=invalid_staff).values(
                    "user__email",
                    "user__first_name",
                    "user__last_name"
                )
                readable = [
                    f"{s['user__first_name']} {s['user__last_name']} ({s['user__email']})"
                    for s in staff_info
                ]
                raise serializers.ValidationError({
                    "assigned_to": "These staff are not assigned to this course: " + ", ".join(readable)
                })

            TaskAssignment.objects.filter(task=instance).delete()

            for staff_id in valid_staff_ids:
                TaskAssignment.objects.create(task=instance, staff_id=staff_id)

        # new attachments
        for file in files:
            TaskAttachment.objects.create(task=instance, file=file)

        return instance


class InstructorTaskDetailSerializer(serializers.ModelSerializer):
    staff_assignments = TaskAssignmentSerializer(
        many=True,
        read_only=True,
        source='assignments'   # <-- this is the fix
    )
    attachments = TaskAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'start_date', 'due_date',
            'course', 'attachments', 'staff_assignments'
        ]



from rest_framework import serializers
from django.utils import timezone

class InstructorSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSubmission
        fields = "__all__"

class InstructorSubmissionReviewSerializer(serializers.ModelSerializer):
    # Map status and revision_due_date to the related assignment fields
    status = serializers.ChoiceField(
        choices=[("revision_required", "revision_required"), ("completed", "completed")],
        required=True,
        source="assignment.status",
    )
    revision_due_date = serializers.DateField(required=False, allow_null=True, source="assignment.revision_due_date")

    class Meta:
        model = TaskSubmission
        fields = [
            "id",
            "instructor_feedback",
            "reviewed_at",
            "status",
            "revision_due_date",
        ]

    def update(self, instance, validated_data):
        # Pop nested assignment data (if present)
        assignment_data = validated_data.pop("assignment", {})

        # update task submission fields
        instance.instructor_feedback = validated_data.get("instructor_feedback", instance.instructor_feedback)
        # ensure reviewed_at is a timezone-aware datetime (DateTimeField expects datetime)
        instance.reviewed_at = validated_data.get("reviewed_at", timezone.now())
        instance.save()

        # now update assignment if assignment data provided
        assignment = instance.assignment
        if assignment_data:
            new_status = assignment_data.get("status")
            if new_status is not None:
                assignment.status = new_status
                if new_status == "revision_required":
                    assignment.revision_due_date = assignment_data.get("revision_due_date", None)
                else:
                    assignment.revision_due_date = None
                assignment.save()

        return instance
