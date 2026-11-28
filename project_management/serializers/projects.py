from rest_framework import serializers
from ..models import ProjectManagement, ProjectMember, ClientContract, DMContract
from .members import ProjectMemberSerializer


class ProjectManagementSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()  # for human-readable display only
    members_count = serializers.SerializerMethodField()  # for human-readable display only

    contract = serializers.PrimaryKeyRelatedField(
        queryset=ClientContract.objects.all(),
        required=False,
        allow_null=True
    )
    dm_contract = serializers.PrimaryKeyRelatedField(
        queryset=DMContract.objects.all(),
        required=False,
        allow_null=True
    )

    client_first_name = serializers.SerializerMethodField()
    client_last_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    client_company_name = serializers.SerializerMethodField()

    contract_number = serializers.SerializerMethodField()
    contract_name = serializers.SerializerMethodField()
    dm_contract_number = serializers.SerializerMethodField()
    dm_contract_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectManagement
        fields = [
            'id',
            'project_number',
            'contract',  # ForeignKey to ClientContract
            'dm_contract',  # ForeignKey to DMContract
            'client_first_name',  # shows client name from contract/dm_contract
            'client_last_name',
            'client_name',
            'client_company_name',
            'contract_number',
            'contract_name',
            'dm_contract_number',
            'dm_contract_name',
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

    def _get_client_obj(self, obj):
        if obj.project_type == 'dm' and obj.dm_contract:
            return getattr(obj.dm_contract, 'client', None)
        elif obj.contract:
            return getattr(obj.contract, 'client', None)
        elif obj.dm_contract:
            return getattr(obj.dm_contract, 'client', None)
        return None

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_members_count(self, obj):
        return obj.projectmember_set.count()

    def get_client_first_name(self, obj):
        client = self._get_client_obj(obj)
        return getattr(client, 'first_name', None) if client else None

    def get_client_last_name(self, obj):
        client = self._get_client_obj(obj)
        return getattr(client, 'last_name', None) if client else None

    def get_client_name(self, obj):
        client = self._get_client_obj(obj)
        if not client:
            return None
        full = f"{getattr(client, 'first_name', '')} {getattr(client, 'last_name', '')}".strip()
        return full or getattr(client, 'company_name', None)

    def get_client_company_name(self, obj):
        client = self._get_client_obj(obj)
        return getattr(client, 'company_name', None) if client else None

    def get_contract_number(self, obj):
        if obj.project_type == 'dm' and obj.dm_contract:
            return obj.dm_contract.contract_number
        if obj.contract:
            return getattr(obj.contract, 'contract_number', None)
        if obj.dm_contract:
            return obj.dm_contract.contract_number
        return None

    def get_contract_name(self, obj):
        if obj.project_type == 'dm' and obj.dm_contract:
            return obj.dm_contract.contract_name
        if obj.contract:
            return getattr(obj.contract, 'contract_name', None)
        if obj.dm_contract:
            return obj.dm_contract.contract_name
        return None

    def get_dm_contract_number(self, obj):
        return obj.dm_contract.contract_number if obj.dm_contract else None

    def get_dm_contract_name(self, obj):
        return obj.dm_contract.contract_name if obj.dm_contract else None

    def validate(self, data):
        start_date = data.get('start_date') or (self.instance.start_date if self.instance else None)
        end_date = data.get('end_date') or (self.instance.end_date if self.instance else None)
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date cannot be after end date.")

        project_type = data.get('project_type')
        if project_type is None and self.instance:
            project_type = self.instance.project_type
        elif project_type is None:
            project_type = 'dev'

        # Cross contract conflict in submission
        if data.get('contract') is not None and data.get('dm_contract') is not None:
            raise serializers.ValidationError("A project cannot have both a standard contract and a digital marketing contract.")

        # If project type is changing, do not inherit incompatible contract from existing instance
        contract = data.get('contract')
        if 'contract' not in data and self.instance:
            if project_type == 'dm':
                contract = None
            else:
                contract = self.instance.contract

        dm_contract = data.get('dm_contract')
        if 'dm_contract' not in data and self.instance:
            if project_type in ['dev', 'testing']:
                dm_contract = None
            else:
                dm_contract = self.instance.dm_contract

        if project_type == 'dev':
            if not contract:
                raise serializers.ValidationError({"contract": "Contract is required for developer projects."})
            if data.get('dm_contract') is not None:
                raise serializers.ValidationError({"dm_contract": "Digital Marketing contract must be null for developer projects."})
            data['contract'] = contract
            data['dm_contract'] = None

        elif project_type == 'testing':
            if data.get('dm_contract') is not None:
                raise serializers.ValidationError({"dm_contract": "Digital Marketing contract must be null for testing projects."})
            data['dm_contract'] = None

        elif project_type == 'dm':
            if not dm_contract:
                raise serializers.ValidationError({"dm_contract": "dm_contract is required for digital marketing projects."})
            if data.get('contract') is not None:
                raise serializers.ValidationError({"contract": "Standard contract must be null for digital marketing projects."})
            data['dm_contract'] = dm_contract
            data['contract'] = None

        return data


class ProjectManagementDetailsSerializer(ProjectManagementSerializer):
    project_members = serializers.SerializerMethodField()  # for human-readable display only

    class Meta(ProjectManagementSerializer.Meta):
        fields = ProjectManagementSerializer.Meta.fields + ['project_members']

    def get_project_members(self, obj):
        project_members = ProjectMember.objects.filter(project=obj).select_related(
            'member__user',
            'department',
            'stack'
        )
        return ProjectMemberSerializer(project_members, many=True).data


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
