from rest_framework import serializers
from ..models import CoursePayment, TaskSubmission, TaskAssignment, Task, TaskSubmissionAttachment, AssignedStaffCourse, CourseInstallment
from datetime import date

# from rest_framework import serializers
# from internship.models import *
# from accounts.models import StaffProfile
# from accounts.serializers.user import *
from django.utils import timezone

from django.db.models import Sum



class TaskAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAssignment
        fields = "__all__"

class InternTaskSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    assignment_details = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "start_date",
            "due_date",
            "course",
            "status",
            "assignment_details",
        ]

    def get_status(self, obj):
        staff_profile = getattr(self.context['request'].user, 'staff_profile', None)
        if not staff_profile:
            return None

        assignment = TaskAssignment.objects.filter(task=obj, staff=staff_profile).first()
        return assignment.status if assignment else None

    def get_assignment_details(self, obj):
        staff_profile = getattr(self.context['request'].user, 'staff_profile', None)
        if not staff_profile:
            return []

        assignment = TaskAssignment.objects.filter(task=obj, staff=staff_profile).first()
        if not assignment:
            return []

        return TaskAssignmentSerializer(assignment).data




class TaskSubmissionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSubmissionAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class TaskSubmissionSerializer(serializers.ModelSerializer):
    attachments = TaskSubmissionAttachmentSerializer(many=True, read_only=True)
    task_id = serializers.IntegerField(source='assignment.task.id', read_only=True)

    # accept multiple files on create
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = TaskSubmission
        fields = [
            "id",
            "assignment",
            "submitted_at",
            "link",
            "response",
            "instructor_feedback",
            "reviewed_at",
            "attachments",
            "files",
            "task_id",
        ]
        read_only_fields = ["submitted_at", "instructor_feedback", "reviewed_at"]

    def validate(self, data):
        assignment = data.get("assignment") or self.instance.assignment

        task = assignment.task
        due = task.due_date
        revision = assignment.revision_due_date

        effective_deadline = (
            revision if (revision and revision > due) else due
        )

        # deadline check
        if date.today() > effective_deadline:
            raise serializers.ValidationError(
                "Deadline passed. You cannot create or modify."
            )

        # CREATE
        if self.instance is None:
            if assignment.status not in ["pending", "revision_required"]:
                raise serializers.ValidationError(
                    "You cannot create new submission now."
                )

        # UPDATE
        else:
            # only allowed while submitted
            if assignment.status != "submitted":
                raise serializers.ValidationError(
                    "You can only update when status is submitted."
                )

        return data
    def create(self, validated_data):
        files = validated_data.pop("files", [])
        submission = TaskSubmission.objects.create(**validated_data)

        # save all attachments
        for f in files:
            TaskSubmissionAttachment.objects.create(
                submission=submission,
                file=f
            )

        # update assignment status to 'submitted'
        assignment = submission.assignment
        assignment.status = 'submitted'
        assignment.save()
        return submission

    def update(self, instance, validated_data):
        files = validated_data.pop("files", [])
        print("Updating submission with files:", files)
        
        # normal update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # handle new attachments
        for f in files:
            TaskSubmissionAttachment.objects.create(
                submission=instance,
                file=f
            )

        return instance
    
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
    # staff_full_name = serializers.SerializerMethodField()
    # employee_id = serializers.CharField(source="staff.job_detail.employee_id", read_only=True)
    # phone_number = serializers.CharField(source="staff.phone_number", read_only=True)
    # email = serializers.CharField(source="staff.user.email", read_only=True)
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
            # "staff_full_name",
            # "employee_id",
            # "phone_number",
            # "email",
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
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
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