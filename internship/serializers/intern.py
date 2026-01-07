from rest_framework import serializers
from ..models import StudyMaterial, TaskAttachment, TaskSubmission, TaskAssignment, Task, TaskSubmissionAttachment, AssignedStaffCourse, CourseInstallment
from datetime import date

# from django.utils import timezone

# from django.db.models import Sum



class TaskAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAssignment
        fields = "__all__"

class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

class InternTaskSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    assignment_details = serializers.SerializerMethodField()
    task_attachment = serializers.SerializerMethodField()

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
            "task_attachment",
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
    
    def get_task_attachment(self, obj):
        attachments = TaskAttachment.objects.filter(task=obj)
        return TaskAttachmentSerializer(attachments, many=True).data



class TaskSubmissionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSubmissionAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class TaskSubmissionSerializer(serializers.ModelSerializer):
    attachments = TaskSubmissionAttachmentSerializer(many=True, read_only=True)
    task_attachment = serializers.SerializerMethodField(read_only=True)
    task_id = serializers.IntegerField(source='assignment.task.id', read_only=True)

    title = serializers.CharField(source='assignment.task.title', read_only=True)
    description = serializers.CharField(source='assignment.task.description', read_only=True)
    status = serializers.CharField(source='assignment.status', read_only=True)
    staff = serializers.SerializerMethodField(read_only=True)
    due_date = serializers.DateField(source='assignment.task.due_date', read_only=True)

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

            "title",
            "description",
            "task_attachment",
            "status",
            "staff",
            "due_date",
        ]
        read_only_fields = ["submitted_at", "instructor_feedback", "reviewed_at"]

    def get_staff(self, obj):
        return f"{obj.assignment.staff.user.first_name} {obj.assignment.staff.user.last_name}"
    
    def get_task_attachment(self, obj):
        attachments = TaskAttachment.objects.filter(task=obj.assignment.task)
        return TaskAttachmentSerializer(attachments, many=True).data

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
    

## DASHABOARD --------------

class InternTaskMiniSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="latest_status")  # ✅ FIX
    course = serializers.CharField(source="course.title")  # ✅ FIX
    attachment = serializers.SerializerMethodField()

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
            "due_date",
            "status",
            "attachment",
        ]

    def get_attachment(self, obj):
        attachments = TaskAttachment.objects.filter(task=obj)
        return TaskAttachmentSerializer(attachments, many=True).data



class StudyMaterialMiniSerializer(serializers.ModelSerializer):
    course = serializers.CharField(source="course.title")

    class Meta:
        model = StudyMaterial
        fields = ["id", "title","course", "material_type", "file", "url"]


# class PaymentSummarySerializer(serializers.Serializer):
#     total_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
#     paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
#     balance_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
#     status = serializers.CharField()
