from datetime import date, datetime
from calendar import monthrange
from django.utils import timezone
from rest_framework import serializers
from ..models import (
    Report,
    ReportingTask,
    ChallengeResolution,
    ReportAttachment,
    ReportLink,
    ProjectMember,
)


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


class ReportSerializer(serializers.ModelSerializer):
    tasks = serializers.ListField(write_only=True)
    challenges = serializers.ListField(write_only=True, required=False, allow_empty=True)
    links = serializers.ListField(write_only=True, required=False, allow_empty=True)

    attachments = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Report
        fields = [
            'project',
            'report_type',
            'executive_summary',
            'next_period_plan',
            'remark',
            'report_date',
            'week_start',
            'week_end',
            'month',
            'year',
            'tasks',
            'challenges',
            'links',
            'attachments'
        ]

    def validate(self, data):
        report_type = data.get('report_type')
        request = self.context.get('request')
        user = request.user if request else None
        project = data.get('project')

        if report_type == 'daily':
            if not data.get('report_date'):
                raise serializers.ValidationError(
                    "report_date is required for daily reports"
                )

            if Report.objects.filter(
                project=project,
                submitted_by=user,
                report_type='daily',
                report_date=data['report_date']
            ).exists():
                raise serializers.ValidationError(
                    "Daily report already submitted"
                )

        if report_type == 'weekly':
            if not data.get('week_start') or not data.get('week_end'):
                raise serializers.ValidationError(
                    "week_start and week_end required"
                )

            if Report.objects.filter(
                project=project,
                submitted_by=user,
                report_type='weekly',
                week_start=data['week_start'],
                week_end=data['week_end']
            ).exists():
                raise serializers.ValidationError(
                    "Weekly report already submitted"
                )

        if report_type == 'monthly':
            if not data.get('month') or not data.get('year'):
                raise serializers.ValidationError(
                    "month and year required"
                )

            if Report.objects.filter(
                project=project,
                submitted_by=user,
                report_type='monthly',
                month=data['month'],
                year=data['year']
            ).exists():
                raise serializers.ValidationError(
                    "Monthly report already submitted"
                )

        if not data.get("tasks"):
            raise serializers.ValidationError({"tasks": "Tasks cannot be empty."})

        return data


class ReportUpdateSerializer(serializers.ModelSerializer):
    tasks = serializers.ListField(write_only=True, required=False)
    challenges = serializers.ListField(write_only=True, required=False)
    links = serializers.ListField(write_only=True, required=False)

    attachments = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Report
        fields = [
            'executive_summary',
            'next_period_plan',
            'remark',
            'report_date',
            'week_start',
            'week_end',
            'month',
            'year',
            'tasks',
            'challenges',
            'links',
            'attachments'
        ]

    def validate(self, data):
        report_type = self.instance.report_type
        request = self.context.get("request")
        user = request.user if request else None

        if report_type == "daily":
            if data.get("report_date"):
                if Report.objects.filter(
                    project=self.instance.project,
                    submitted_by=user,
                    report_type="daily",
                    report_date=data["report_date"]
                ).exclude(id=self.instance.id).exists():
                    raise serializers.ValidationError(
                        "Daily report already submitted"
                    )

        if not data.get("tasks"):
            raise serializers.ValidationError({"tasks": "Tasks cannot be empty."})
        return data


class ReportResponseSerializer(serializers.ModelSerializer):
    tasks = ReportingTaskSerializer(many=True, read_only=True)
    challenges = ChallengeResolutionSerializer(many=True, read_only=True)
    attachments = ReportAttachmentSerializer(many=True, read_only=True)
    links = ReportLinkSerializer(many=True, read_only=True)

    total_worked_hours = serializers.SerializerMethodField()
    submitted_by = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    staff_email = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id',
            'project',
            'report_type',
            'executive_summary',
            'next_period_plan',
            'remark',
            'report_date',
            'week_start',
            'week_end',
            'month',
            'year',
            'submitted_by',
            'job_title',
            'staff_email',
            'submitted_at',
            'tasks',
            'challenges',
            'attachments',
            'links',
            'total_worked_hours',
        ]

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


class StaffReportConsolidatedSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    staff_email = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    period_label = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()
    submission_status = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id',
            'project',
            'project_name',
            'staff_name',
            'staff_email',
            'role',
            'report_type',
            'period_label',
            'executive_summary',
            'submitted_at',
            'submission_status',
            'metrics',
        ]

    def get_staff_name(self, obj):
        if obj.submitted_by:
            name = f"{obj.submitted_by.first_name} {obj.submitted_by.last_name}".strip()
            return name if name else obj.submitted_by.email
        return ""

    def get_staff_email(self, obj):
        user = obj.submitted_by
        if not user:
            return None
        staff_profile = getattr(user, 'staff_profile', None)
        return staff_profile.staff_email if (staff_profile and staff_profile.staff_email) else user.email

    def get_role(self, obj):
        user = obj.submitted_by
        if not user:
            return ""
        staff_profile = getattr(user, 'staff_profile', None)
        job_detail = getattr(staff_profile, 'job_detail', None) if staff_profile else None
        if job_detail and job_detail.role:
            return job_detail.role
        try:
            pm = ProjectMember.objects.filter(project=obj.project, member__user=user).select_related('stack').first()
            if pm and pm.stack:
                return pm.stack.name
        except Exception:
            pass
        return ""

    def get_period_label(self, obj):
        if obj.report_type == 'daily':
            if obj.report_date:
                return obj.report_date.strftime("%d %b %Y")
            elif obj.submitted_at:
                return timezone.localtime(obj.submitted_at).strftime("%d %b %Y")
            return "Daily"
        elif obj.report_type == 'weekly':
            if obj.week_start and obj.week_end:
                return f"{obj.week_start.strftime('%d %b')} - {obj.week_end.strftime('%d %b %Y')}"
            return "Weekly"
        elif obj.report_type == 'monthly':
            if obj.month and obj.year:
                try:
                    return date(obj.year, obj.month, 1).strftime("%B %Y")
                except ValueError:
                    return f"{obj.month}/{obj.year}"
            return "Monthly"
        return ""

    def get_submitted_at(self, obj):
        if obj.submitted_at:
            return timezone.localtime(obj.submitted_at).strftime("%Y-%m-%d %H:%M:%S")
        return None

    def get_submission_status(self, obj):
        if not obj.submitted_at:
            return "Pending"

        try:
            if obj.report_type == 'daily' and obj.report_date:
                deadline = timezone.make_aware(
                    datetime.combine(obj.report_date, datetime.strptime("18:30", "%H:%M").time())
                )
                return "Late" if obj.submitted_at > deadline else "Submitted"
            elif obj.report_type == 'weekly' and obj.week_end:
                deadline = timezone.make_aware(
                    datetime.combine(obj.week_end, datetime.max.time())
                )
                return "Late" if obj.submitted_at > deadline else "Submitted"
            elif obj.report_type == 'monthly' and obj.month and obj.year:
                last_day = monthrange(obj.year, obj.month)[1]
                deadline = timezone.make_aware(
                    datetime(obj.year, obj.month, last_day, 23, 59, 59)
                )
                return "Late" if obj.submitted_at > deadline else "Submitted"
        except Exception:
            pass

        return "Submitted"

    def get_metrics(self, obj):
        tasks = list(obj.tasks.all())
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == 'completed')
        in_progress_tasks = sum(1 for t in tasks if t.status == 'in_progress')
        pending_tasks = sum(1 for t in tasks if t.status in ('not_started', 'on_hold', 'cancelled'))

        avg_progress = (
            round(sum(t.progress_percentage for t in tasks) / total_tasks, 1)
            if total_tasks > 0 else 0.0
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate_percentage": avg_progress,
        }
