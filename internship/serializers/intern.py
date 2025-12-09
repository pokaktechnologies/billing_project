from rest_framework import serializers
from ..models import TaskSubmission, TaskAssignment, Task, TaskSubmissionAttachment
from datetime import date


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
