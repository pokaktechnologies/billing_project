from rest_framework import serializers
from ..models import StudyMaterial, TaskAttachment, TaskSubmission, TaskAssignment, Task, TaskSubmissionAttachment
from ..utils import get_authenticated_student, get_student_task_assignment
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

    def _get_assignment(self, obj):
        request = self.context.get("request")
        student = get_authenticated_student(getattr(request, "user", None))
        return get_student_task_assignment(obj, student)

    def get_status(self, obj):
        assignment = self._get_assignment(obj)
        return assignment.status if assignment else None

    def get_assignment_details(self, obj):
        assignment = self._get_assignment(obj)
        if not assignment:
            return []

        return TaskAssignmentSerializer(assignment).data
    
    def get_task_attachment(self, obj):
        attachments = obj.attachments.all()
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
    student_name = serializers.SerializerMethodField(read_only=True)
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
            "student_name",
            "staff",
            "due_date",
        ]
        read_only_fields = ["submitted_at", "instructor_feedback", "reviewed_at"]

    def _get_assignee_name(self, assignment):
        student = assignment.student
        if student and student.profile and student.profile.user:
            user = student.profile.user
            return f"{user.first_name} {user.last_name}".strip()

        staff = assignment.staff
        if staff and staff.user:
            return f"{staff.user.first_name} {staff.user.last_name}".strip()

        return None

    def get_student_name(self, obj):
        return self._get_assignee_name(obj.assignment)

    def get_staff(self, obj):
        # Backward-compatible alias for older clients.
        return self._get_assignee_name(obj.assignment)
    
    def get_task_attachment(self, obj):
        attachments = obj.assignment.task.attachments.all()
        return TaskAttachmentSerializer(attachments, many=True).data

    def validate(self, data):
        assignment = data.get("assignment") or self.instance.assignment
        request = self.context.get("request")
        student = get_authenticated_student(getattr(request, "user", None))

        if not student:
            raise serializers.ValidationError("User has no student profile.")

        if assignment.student_id != student.id:
            raise serializers.ValidationError(
                "You are not assigned to this task."
            )

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
    status = serializers.CharField(source="latest_status")
    course = serializers.CharField(source="course.title")
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
            "attachment",
        ]

    def get_attachment(self, obj):
        attachments = obj.attachments.all()
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
