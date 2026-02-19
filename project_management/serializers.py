from rest_framework import serializers
from .models import ChallengeResolution, ProjectManagement, Member, Report, ReportAttachment, ReportLink, ReportingTask, Stack, ProjectMember, StatusColumns, Task,ClientContract, TaskAssign, TaskBoard
from accounts.models import CustomUser
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
        fields = ['id','user','full_name','department','role','phone_number','email','created_at']
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

    # def get_role_display(self, obj):
    #     return obj.get_role_display()

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
    # task_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = ['id', 'member', 'member_name', 'stack','stack_name' , 'project', 'project_name', 'phone_number', 'email', 'created_at']
    
    # def get_task_count(self, obj):
    #     return obj.task_set.count()
    def get_member_name(self, obj):
        return obj.member.user.first_name + " " + obj.member.user.last_name.strip()


#-----------------
# Task Serializers
#-----------------


class TaskBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskBoard
        fields = ['id', 'project', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TaskMiniSerializer(serializers.ModelSerializer):
    board_name = serializers.CharField(source='board.name', read_only=True)


    class Meta:
        model = Task
        fields = [
            'id',
            'task_name',
            'difficulty',
            'status',
            'end_date',
            'board_name',
        ]
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
    assignments  = TaskAssignSerializer(many=True, read_only=True)
    project_name = serializers.CharField(source = 'project.project_name', read_only=True)
    board_name = serializers.CharField(source = 'board.name', read_only=True)
    status = serializers.ChoiceField(choices=[
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ])
    class Meta:
        model = Task
        fields =[
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
            'created_at',
            'updated_at',
            'assignments'
        ]
        read_only_fields = ['created_at', 'updated_at']


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


class ReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAttachment
        fields = ['file']

class ReportLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportLink
        fields = ['url']


from django.db import transaction
from rest_framework import serializers

from rest_framework import serializers
from django.db import transaction
from .models import Report, ReportingTask, ChallengeResolution, ReportAttachment, ReportLink


class ReportSerializer(serializers.ModelSerializer):
    tasks = ReportingTaskSerializer(many=True, write_only=True)
    challenges = ChallengeResolutionSerializer(many=True, write_only=True)
    task_list = ReportingTaskSerializer(source='tasks', many=True, read_only=True)
    challenge_list = ChallengeResolutionSerializer(source='challenges', many=True, read_only=True)

    attachments = ReportAttachmentSerializer(many=True, write_only=True, required=False)
    links = ReportLinkSerializer(many=True, write_only=True, required=False)

    attachment_list = ReportAttachmentSerializer(source='attachments', many=True, read_only=True)
    link_list = ReportLinkSerializer(source='links', many=True, read_only=True)

    total_worked_hours = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField(read_only=True)
    job_title = serializers.SerializerMethodField()
    staff_email = serializers.SerializerMethodField()

    class Meta:
        model = Report
        read_only_fields = ['submitted_by', 'submitted_at']
        fields = [
            'id',
            'project',
            'report_type',
            'executive_summary',
            'next_period_plan',

            # DAILY
            'report_date',

            # WEEKLY
            'week_start',
            'week_end',

            # MONTHLY
            'month',
            'year',

            'attachments',
            'links',
            'attachment_list',
            'link_list',

            'submitted_by',
            'job_title',
            'staff_email',
            'submitted_at',

            'tasks',
            'challenges',
            'task_list',
            'challenge_list',
            'total_worked_hours',
        ]

    # -------------------------
    # READ HELPERS
    # -------------------------
    def get_total_worked_hours(self, obj):
        return obj.total_worked_hours

    def get_submitted_by(self, obj):
        if obj.submitted_by:
            return f"{obj.submitted_by.first_name} {obj.submitted_by.last_name}".strip()

    def get_job_title(self, obj):
        user = obj.submitted_by
        staff_profile = getattr(user, 'staff_profile', None)
        job_detail = getattr(staff_profile, 'job_detail', None) if staff_profile else None
        return job_detail.role if job_detail else None

    def get_staff_email(self, obj):
        user = obj.submitted_by
        if not user:
            return None
        staff_profile = getattr(user, 'staff_profile', None)
        return staff_profile.staff_email if staff_profile else user.email

    # -------------------------
    # VALIDATION
    # -------------------------
    def validate(self, data):
        report_type = data.get('report_type')
        request = self.context.get('request')
        user = request.user if request else None
        project = data.get('project')

        # DAILY VALIDATION
        if report_type == 'daily':
            report_date = data.get('report_date')

            if not report_date:
                raise serializers.ValidationError(
                    "report_date is required for daily reports"
                )

            if user and Report.objects.filter(
                project=project,
                submitted_by=user,
                report_type='daily',
                report_date=report_date
            ).exists():
                raise serializers.ValidationError(
                    "Daily report already submitted"
                )

        # WEEKLY VALIDATION
        if report_type == 'weekly':
            week_start = data.get('week_start')
            week_end = data.get('week_end')

            if not week_start or not week_end:
                raise serializers.ValidationError(
                    "week_start and week_end required for weekly reports"
                )

            if user and Report.objects.filter(
                project=project,
                submitted_by=user,
                report_type='weekly',
                week_start=week_start,
                week_end=week_end
            ).exists():
                raise serializers.ValidationError(
                    "Weekly report already submitted"
                )

        # MONTHLY VALIDATION
        if report_type == 'monthly':
            month = data.get('month')
            year = data.get('year')

            if not month or not year:
                raise serializers.ValidationError(
                    "month and year required for monthly reports"
                )

            if user and Report.objects.filter(
                project=project,
                submitted_by=user,
                report_type='monthly',
                month=month,
                year=year
            ).exists():
                raise serializers.ValidationError(
                    "Monthly report already submitted"
                )

        return data

    # -------------------------
    # CREATE
    # -------------------------
    @transaction.atomic
    def create(self, validated_data):
        tasks = validated_data.pop('tasks', [])
        challenges = validated_data.pop('challenges', [])
        attachments = validated_data.pop('attachments', [])
        links = validated_data.pop('links', [])

        report = Report.objects.create(**validated_data)

        ReportingTask.objects.bulk_create([
            ReportingTask(report=report, **t) for t in tasks
        ])

        ChallengeResolution.objects.bulk_create([
            ChallengeResolution(report=report, **c) for c in challenges
        ])

        ReportAttachment.objects.bulk_create([
            ReportAttachment(report=report, **a) for a in attachments
        ])

        ReportLink.objects.bulk_create([
            ReportLink(report=report, **l) for l in links
        ])

        return report

class ReportUpdateSerializer(serializers.ModelSerializer):
    tasks = ReportingTaskSerializer(many=True, write_only=True, required=False)
    challenges = ChallengeResolutionSerializer(many=True, write_only=True, required=False)
    attachments = ReportAttachmentSerializer(many=True, write_only=True, required=False)
    links = ReportLinkSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Report
        fields = [
            'executive_summary',
            'next_period_plan',
            'report_date',
            'week_start',
            'week_end',
            'month',
            'year',
            'tasks',
            'challenges',
            'attachments',
            'links',
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        tasks = validated_data.pop('tasks', None)
        challenges = validated_data.pop('challenges', None)
        attachments = validated_data.pop('attachments', None)
        links = validated_data.pop('links', None)

        # update main fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # replace nested data
        if tasks is not None:
            instance.tasks.all().delete()
            ReportingTask.objects.bulk_create(
                [ReportingTask(report=instance, **t) for t in tasks]
            )

        if challenges is not None:
            instance.challenges.all().delete()
            ChallengeResolution.objects.bulk_create(
                [ChallengeResolution(report=instance, **c) for c in challenges]
            )

        if attachments is not None:
            instance.attachments.all().delete()
            ReportAttachment.objects.bulk_create(
                [ReportAttachment(report=instance, **a) for a in attachments]
            )

        if links is not None:
            instance.links.all().delete()
            ReportLink.objects.bulk_create(
                [ReportLink(report=instance, **l) for l in links]
            )

        return instance


class ProjectTimelineSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    stack_name = serializers.CharField(source='stack.name', read_only=True)
    # duration = serializers.IntegerField(source='project.duration', read_only=True)

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
            # 'duration',
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
