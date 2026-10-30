from rest_framework import serializers
from accounts.models import CustomUser
from ..models import Member, Stack, ProjectMember


class MemberSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        write_only=True
    )

    full_name = serializers.SerializerMethodField()
    department = serializers.CharField(
        source='user.staff_profile.job_detail.department.name',
        read_only=True
    )
    role = serializers.CharField(
        source='user.staff_profile.job_detail.role',
        read_only=True
    )
    phone_number = serializers.CharField(
        source='user.staff_profile.phone_number',
        read_only=True
    )
    email = serializers.CharField(
        source='user.email',
        read_only=True
    )

    class Meta:
        model = Member
        fields = ['id', 'user', 'full_name', 'department', 'role', 'phone_number', 'email', 'created_at']
        read_only_fields = ['created_at', 'full_name', 'department', 'role', 'phone_number', 'email']

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def validate_user(self, user):
        if Member.objects.filter(user=user).exists():
            raise serializers.ValidationError("This user is already a member.")
        staff_profile = getattr(user, 'staff_profile', None)
        if not staff_profile:
            raise serializers.ValidationError("User is not a staff member")

        job_detail = getattr(staff_profile, 'job_detail', None)
        if not job_detail:
            raise serializers.ValidationError("Staff profile does not have job details")

        return user


class StackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stack
        fields = ['id', 'name']


class ProjectMemberSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    stack_name = serializers.CharField(source='stack.name', read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    phone_number = serializers.CharField(source='member.user.staff_profile.phone_number', read_only=True)
    email = serializers.CharField(source='member.user.email', read_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'member', 'member_name', 'stack', 'stack_name', 'project', 'project_name', 'phone_number', 'email', 'created_at']

    def get_member_name(self, obj):
        return obj.member.user.first_name + " " + obj.member.user.last_name.strip()
