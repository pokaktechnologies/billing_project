from django.utils import timezone
from rest_framework import serializers
from ..models import ProjectNote, Task
from .tasks import TaskAssignSerializer


class ProjectNoteSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source='project.project_name',
        read_only=True
    )

    created_by_name = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    updated_at_formatted = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = ProjectNote
        fields = [
            'id',
            'project',
            'project_name',
            'title',
            'content',
            'meeting_date',
            'start_time',
            'end_time',
            'duration_minutes',
            'created_by',
            'created_by_name',
            'created_by_email',
            'created_at',
            'created_at_formatted',
            'updated_at',
            'updated_at_formatted',
        ]

        read_only_fields = [
            'id',
            'project',
            'created_by',
            'created_at',
            'updated_at',
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return ""

        name = (
            f"{obj.created_by.first_name} "
            f"{obj.created_by.last_name}"
        ).strip()

        return name or obj.created_by.email

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    def get_created_at_formatted(self, obj):
        if obj.created_at:
            return timezone.localtime(
                obj.created_at
            ).strftime("%Y-%m-%d %H:%M:%S")

        return None

    def get_updated_at_formatted(self, obj):
        if obj.updated_at:
            return timezone.localtime(
                obj.updated_at
            ).strftime("%Y-%m-%d %H:%M:%S")

        return None

    def get_duration_minutes(self, obj):
        if not obj.start_time or not obj.end_time:
            return None

        start_minutes = (
            obj.start_time.hour * 60
            + obj.start_time.minute
        )

        end_minutes = (
            obj.end_time.hour * 60
            + obj.end_time.minute
        )

        return end_minutes - start_minutes


class ProjectNoteCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectNote
        fields = [
            'title',
            'content',
            'meeting_date',
            'start_time',
            'end_time',
        ]

        extra_kwargs = {
            'title': {
                'required': True,
            },
            'content': {
                'required': False,
                'allow_blank': True,
            },
            'meeting_date': {
                'required': False,
                'allow_null': True,
            },
            'start_time': {
                'required': False,
                'allow_null': True,
            },
            'end_time': {
                'required': False,
                'allow_null': True,
            },
        }

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Meeting title cannot be blank."
            )

        return value.strip()

    def validate(self, attrs):
        # For PATCH, use existing values when a field is omitted.
        start_time = attrs.get(
            'start_time',
            getattr(self.instance, 'start_time', None)
        )

        end_time = attrs.get(
            'end_time',
            getattr(self.instance, 'end_time', None)
        )

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                'end_time': (
                    "End time must be later than start time."
                )
            })

        return attrs


class MeetingTaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.IntegerField(write_only=True, required=True)
    project_name = serializers.CharField(
        source="project.project_name",
        read_only=True
    )
    assignments = TaskAssignSerializer(
        many=True,
        read_only=True
    )
    board_name = serializers.CharField(
        source="board.name",
        read_only=True
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "task_name",
            "description",
            "project",
            "project_name",
            "board",
            "board_name",
            "assigned_to",
            "assignments",
            "meeting",
            "difficulty",
            "status",
            "end_date",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        meeting = attrs.get("meeting")
        board = attrs.get("board")

        # Support partial updates
        if self.instance:
            meeting = attrs.get("meeting", self.instance.meeting)
            board = attrs.get("board", self.instance.board)

        if meeting and board and board.project_id != meeting.project_id:
            raise serializers.ValidationError({
                "board": "The selected board must belong to the meeting's project."
            })

        return attrs
