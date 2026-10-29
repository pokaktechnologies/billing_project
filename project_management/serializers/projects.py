from rest_framework import serializers
from ..models import ProjectManagement, ProjectMember
from .members import ProjectMemberSerializer


class ProjectManagementSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()  # for human-readable display only
    members_count = serializers.SerializerMethodField()  # for human-readable display only
    client_first_name = serializers.CharField(source='contract.client.first_name', read_only=True)
    client_last_name = serializers.CharField(source='contract.client.last_name', read_only=True)

    class Meta:
        model = ProjectManagement
        fields = [
            'id',
            'project_number',
            'contract',  # ForeignKey to ClientContract
            'client_first_name',  # shows client name from ClientContract
            'client_last_name',
            'project_type',
            'project_name',
            'project_description',
            'start_date',
            'end_date',
            'duration',         # duration in days
            'status',           # accept "on_hold", "in_progress", etc.
            'status_display',   # shows "On Hold", "In Progress", etc.
            'created_at',
            'updated_at',
            'members_count',    # shows number of members in the project
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date cannot be after end date.")
        return data

    def get_members_count(self, obj):
        return obj.projectmember_set.count()


class ProjectManagementDetailsSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()  # for human-readable display only
    members_count = serializers.SerializerMethodField()  # for human-readable display only
    client_first_name = serializers.CharField(source='contract.client.first_name', read_only=True)
    client_last_name = serializers.CharField(source='contract.client.last_name', read_only=True)
    project_members = serializers.SerializerMethodField()  # for human-readable display only

    class Meta:
        model = ProjectManagement
        fields = [
            'id',
            'project_number',
            'contract',  # ForeignKey to ClientContract
            'client_first_name',  # shows client name from ClientContract
            'client_last_name',
            'project_name',
            'project_type',
            'project_description',
            'start_date',
            'end_date',
            'duration',         # duration in days
            'status',           # accept "on_hold", "in_progress", etc.
            'status_display',   # shows "On Hold", "In Progress", etc.
            'created_at',
            'updated_at',
            'members_count',    # shows number of members in the project
            'project_members',  # shows project members
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date cannot be after end date.")
        return data

    def get_project_members(self, obj):
        project_members = ProjectMember.objects.filter(project=obj)
        return ProjectMemberSerializer(project_members, many=True).data

    def get_members_count(self, obj):
        return obj.projectmember_set.count()


class ProjectManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectManagement
        fields = ['id', 'project_number', 'project_name', 'status', 'start_date', 'end_date']


class ProjectTimelineSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    stack_name = serializers.CharField(source='stack.name', read_only=True)

    total_tasks = serializers.SerializerMethodField()
    completed_tasks = serializers.SerializerMethodField()
    pending_tasks = serializers.SerializerMethodField()

    easy_tasks = serializers.SerializerMethodField()
    medium_tasks = serializers.SerializerMethodField()
    hard_tasks = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = [
            'id',
            'project',
            'project_name',
            'member',
            'member_name',
            'stack',
            'stack_name',
            'created_at',
            'total_tasks',
            'completed_tasks',
            'pending_tasks',
            'easy_tasks',
            'medium_tasks',
            'hard_tasks',
        ]

    def get_member_name(self, obj):
        return f"{obj.member.user.first_name} {obj.member.user.last_name}".strip()

    def get_task_data(self, obj):
        task_map = self.context.get('task_map', {})
        return task_map.get(obj.id, {})

    def get_total_tasks(self, obj):
        return self.get_task_data(obj).get('total_tasks', 0)

    def get_completed_tasks(self, obj):
        return self.get_task_data(obj).get('completed_tasks', 0)

    def get_pending_tasks(self, obj):
        return self.get_task_data(obj).get('pending_tasks', 0)

    def get_easy_tasks(self, obj):
        return self.get_task_data(obj).get('easy_tasks', 0)

    def get_medium_tasks(self, obj):
        return self.get_task_data(obj).get('medium_tasks', 0)

    def get_hard_tasks(self, obj):
        return self.get_task_data(obj).get('hard_tasks', 0)
