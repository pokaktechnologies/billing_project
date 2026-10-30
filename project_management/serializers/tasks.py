from rest_framework import serializers
from ..models import TaskBoard, StatusColumns, Task, TaskAssign


class TaskBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskBoard
        fields = ['id', 'project', 'name', 'start_date', 'end_date', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TaskMiniSerializer(serializers.ModelSerializer):
    board_name = serializers.CharField(source='board.name', read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'task_name',
            'difficulty',
            'status',
            'start_time',
            'end_time',
            'duration',
            'end_date',
            'board_name',
        ]

    def get_duration(self, obj):
        seconds = obj.get_duration_seconds()
        if seconds is None:
            return None

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        return {
            "seconds": seconds,
            "formatted": f"{hours}h {minutes}m {remaining_seconds}s"
        }


class StatusColumnWithTasksSerializer(serializers.ModelSerializer):
    tasks = TaskMiniSerializer(
        source='task_set',
        many=True,
        read_only=True
    )

    class Meta:
        model = StatusColumns
        fields = [
            'id',
            'board',
            'name',
            'created_at',
            'updated_at',
            'tasks'
        ]


class TaskAssignSerializer(serializers.ModelSerializer):
    assigned_by = serializers.SerializerMethodField(read_only=True)
    assigned_to = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TaskAssign
        fields = ['id', 'assigned_by', 'task', 'assigned_to', 'assigned_at']
        read_only_fields = ['assigned_at']

    def get_assigned_by(self, obj):
        return obj.assigned_by.first_name + " " + obj.assigned_by.last_name.strip()

    def get_assigned_to(self, obj):
        return obj.assigned_to.member.user.first_name + " " + obj.assigned_to.member.user.last_name.strip()


class TaskSerializer(serializers.ModelSerializer):
    assignments = TaskAssignSerializer(many=True, read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    board_name = serializers.CharField(source='board.name', read_only=True)
    status = serializers.ChoiceField(choices=[
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ])
    duration = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'project',
            'project_name',
            'board',
            'board_name',
            'status',
            'task_name',
            'description',
            'difficulty',
            'end_date',
            'duration',
            'start_time',
            'end_time',
            'created_at',
            'updated_at',
            'assignments'
        ]
        read_only_fields = ['created_at', 'updated_at', 'duration', 'start_time', 'end_time']

    def get_duration(self, obj):
        seconds = obj.get_duration_seconds()
        if seconds is None:
            return None

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        return {
            "seconds": seconds,
            "hours": hours,
            "minutes": minutes,
            "seconds_remaining": remaining_seconds,
            "formatted": f"{hours}h {minutes}m"
        }


class AssignedTaskListSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source="task.task_name", read_only=True)
    task_status = serializers.CharField(source="task.status", read_only=True)
    start_date = serializers.DateField(source="task.start_date", read_only=True)
    end_date = serializers.DateField(source="task.end_date", read_only=True)
    project_name = serializers.CharField(source="task.project_member.project.project_name", read_only=True)
    assigned_to = serializers.CharField(source="assigned_to.member.name", read_only=True)

    class Meta:
        model = TaskAssign
        fields = [
            "id",
            "task_name",
            "task_status",
            "start_date",
            "end_date",
            "project_name",
            "assigned_to",
            "assigned_at",
        ]
