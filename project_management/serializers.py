from rest_framework import serializers
from .models import ChallengeResolution, ProjectManagement, Member, Report, ReportingTask, Stack, ProjectMember, Task,ClientContract, TaskAssign

class ClientContractSerializer(serializers.ModelSerializer):
    client_first_name =  serializers.CharField(source='client.first_name', read_only=True)
    client_last_name =  serializers.CharField(source='client.last_name', read_only=True)

    class Meta:
        model = ClientContract
        fields = [
            'id',
            'client',
            'client_first_name',
            'client_last_name',
            'contract_name',
            'description',
            'contract_date',
            'start_date',
            'end_date',
            'duration',         # duration in days
            'created_at',
            'updated_at',
        ]


class ProjectManagementSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()  # for human-readable display only
    members_count = serializers.SerializerMethodField()  # for human-readable display only
    client_first_name =  serializers.CharField(source='contract.client.first_name', read_only=True)
    client_last_name =  serializers.CharField(source='contract.client.last_name', read_only=True)

    class Meta:
        model = ProjectManagement
        fields = [
            'id',
            'contract',  # ForeignKey to ClientContract
            'client_first_name', # shows client name from ClientContract
            'client_last_name',
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
    client_first_name =  serializers.CharField(source='contract.client.first_name', read_only=True)
    client_last_name =  serializers.CharField(source='contract.client.last_name', read_only=True)
    project_members = serializers.SerializerMethodField()  # for human-readable display only

    class Meta:
        model = ProjectManagement
        fields = [
            'id',
            'contract',  # ForeignKey to ClientContract
            'client_first_name', # shows client name from ClientContract
            'client_last_name',
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
        

class MemberSerializer(serializers.ModelSerializer):

    role_display = serializers.SerializerMethodField()  # for human-readable display only

    class Meta:
        model = Member
        fields = ['id', 'name', 'email', 'phone_number', 'role','role_display', 'created_at']
    
    def get_role_display(self, obj):
        return obj.get_role_display()

class StackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stack
        fields = ['id', 'name']

class ProjectMemberSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    stack_name = serializers.CharField(source='stack.name', read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = ['id', 'member', 'stack','stack_name' , 'member_name', 'project', 'project_name', 'task_count', 'created_at']
    
    def get_task_count(self, obj):
        return obj.task_set.count()



class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project_member.project.project_name', read_only=True)
    status_display = serializers.SerializerMethodField()  # for human-readable display only

    class Meta:
        model = Task
        fields = [
            'id',
            'project_member',
            'project_name',
            'task_name',
            'task_description',
            'start_date',
            'end_date',
            'status',
            'status_display',
            'created_at',
            'updated_at'
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()


## DASHBOARD VIEW------#

class ProjectManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectManagement
        fields = ['id', 'project_name', 'status', 'start_date', 'end_date']

class AssignedTaskListSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source="task.task_name", read_only=True)
    task_status = serializers.CharField(source="task.status", read_only=True)
    start_date = serializers.DateField(source="task.start_date", read_only=True)
    end_date = serializers.DateField(source="task.end_date", read_only=True)
    project_name = serializers.CharField(source="task.project_member.project.project_name",read_only=True)
    assigned_to = serializers.CharField(source="assigned_to.member.name",read_only=True)

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


#-----------------
# Report Serializers
#-----------------

class ReportingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingTask
        fields = [
            'id',
            'task_name',
            'task_description',
            'status',
            'progress_percentage',
            'hours',
        ]

class ChallengeResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChallengeResolution
        fields = [
            'id',
            'issue',
            'impact',
            'resolution',
        ]


class ReportSerializer(serializers.ModelSerializer):
    tasks = ReportingTaskSerializer(many=True, write_only=True)
    challenges = ChallengeResolutionSerializer(many=True, write_only=True)
    total_worked_hours = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        read_only_fields = ['submitted_by', 'submitted_at']
        fields = [
            'id',
            'project',
            'report_type',
            'executive_summary',
            'next_period_plan',
            'attachment_file',
            'link',
            'submitted_by',
            'submitted_at',
            'tasks',
            'challenges',
            'total_worked_hours',
        ]

    def get_total_worked_hours(self, obj):
        return obj.total_worked_hours
    
    def get_submitted_by(self, obj):
        if obj.submitted_by:
            return f"{obj.submitted_by.first_name} {obj.submitted_by.last_name}".strip()

    def create(self, validated_data):
        tasks_data = validated_data.pop('tasks', [])
        challenges_data = validated_data.pop('challenges', [])

        report = Report.objects.create(**validated_data)

        ReportingTask.objects.bulk_create([
            ReportingTask(report=report, **task)
            for task in tasks_data
        ])

        ChallengeResolution.objects.bulk_create([
            ChallengeResolution(report=report, **challenge)
            for challenge in challenges_data
        ])

        return report
