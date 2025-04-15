from rest_framework import serializers
from .models import ProjectManagement, Member, Stack, ProjectMember, Task


class ProjectManagementSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()  # for human-readable display only
    members_count = serializers.SerializerMethodField()  # for human-readable display only

    class Meta:
        model = ProjectManagement
        fields = [
            'id',
            'project_name',
            'project_description',
            'start_date',
            'end_date',
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


        

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'name', 'email', 'phone_number', 'role', 'created_at']

class StackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stack
        fields = ['id', 'name']
# serializers.py

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
            'created_at',
            'updated_at'
        ]
