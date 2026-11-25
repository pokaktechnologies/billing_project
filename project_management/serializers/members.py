from rest_framework import serializers
from accounts.models import CustomUser, Department
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
        fields = [
            'id', 'user', 'full_name', 'department', 'role',
            'phone_number', 'email', 'status', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at', 'full_name', 'department', 'role', 'phone_number', 'email']

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def validate_user(self, user):
        existing = Member.objects.filter(user=user).first()
        if existing and existing.is_active and existing.status == 'active':
            raise serializers.ValidationError("This user is already an active member.")
        staff_profile = getattr(user, 'staff_profile', None)
        if not staff_profile:
            raise serializers.ValidationError("User is not a staff member")

        job_detail = getattr(staff_profile, 'job_detail', None)
        if not job_detail:
            raise serializers.ValidationError("Staff profile does not have job details")

        return user


class StackSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Stack
        fields = ['id', 'name', 'members_count']

    def get_members_count(self, obj):
        return obj.projectmember_set.count()


class ProjectMemberSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='member.user.id', read_only=True)
    role = serializers.CharField(source='member.user.staff_profile.job_detail.role', read_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=False,
        allow_null=True
    )
    department_name = serializers.SerializerMethodField()
    stack = serializers.PrimaryKeyRelatedField(
        queryset=Stack.objects.all(),
        required=False,
        allow_null=True
    )
    stack_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    phone_number = serializers.CharField(source='member.user.staff_profile.phone_number', read_only=True)
    email = serializers.CharField(source='member.user.email', read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            'id', 'member', 'user_id', 'member_name', 'role',
            'department', 'department_name', 'stack', 'stack_name',
            'project', 'project_name', 'phone_number', 'email',
            'status', 'is_active', 'created_at'
        ]

    def get_member_name(self, obj):
        first = getattr(obj.member.user, 'first_name', '')
        last = getattr(obj.member.user, 'last_name', '')
        return f"{first} {last}".strip()

    def get_department_name(self, obj):
        if obj.department:
            return obj.department.name
        staff_prof = getattr(obj.member.user, 'staff_profile', None)
        if staff_prof and getattr(staff_prof, 'job_detail', None) and staff_prof.job_detail.department:
            return staff_prof.job_detail.department.name
        return None

    def get_stack_name(self, obj):
        if obj.stack:
            return obj.stack.name
        return self.get_department_name(obj)
