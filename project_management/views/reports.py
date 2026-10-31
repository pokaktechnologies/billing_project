from calendar import monthrange
from datetime import datetime, date, timedelta
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import CustomUser
from accounts.permissions import HasModulePermission
from activity_logs.base_view import BaseAPIView
from project_management.models.members import Member
from ..models import (
    ChallengeResolution,
    ProjectManagement,
    ProjectMember,
    Report,
    ReportAttachment,
    ReportingTask,
    ReportLink,
    Task,
    TaskAssign,
)
from ..serializers import (
    ReportResponseSerializer,
    ReportSerializer,
    ReportUpdateSerializer,
    StaffReportConsolidatedSerializer,
)
from .pagination import Pagination, ReportPagination

import json

class ReportView(BaseAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request, id=None):
        report_type = request.query_params.get('type')      # daily, weekly, monthly
        project_id = request.query_params.get('project')    # <-- ADD HERE
        date_str = request.query_params.get('date')         # YYYY-MM-DD
        week_str = request.query_params.get('week')         # YYYY-MM-DD
        month_str = request.query_params.get('month')       # YYYY-MM

        user = request.user

        # Get member profile
        member = Member.objects.filter(user=user).first()
        if not member:
            return Response(
                {"status": "0", "message": "User is not a project member"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get projects where user is a member
        project_ids = ProjectMember.objects.filter(
            member=member
        ).values_list('project_id', flat=True)

        # IF ID IS PROVIDED → RETRIEVE SINGLE REPORT
        if id is not None:
            try:
                report = Report.objects.select_related(
                    'submitted_by',
                    'submitted_by__staff_profile',
                    'submitted_by__staff_profile__job_detail'
                ).prefetch_related(
                    'tasks',
                    'challenges'
                ).get(
                    id=id,
                    project_id__in=project_ids,
                    submitted_by=user
                )
            except Report.DoesNotExist:
                return Response(
                    {"status": "0", "message": "Report not found or access denied"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = ReportResponseSerializer(report)
            return Response(
                {"status": "1", "message": "success", "data": serializer.data},
                status=status.HTTP_200_OK
            )

        # Fetch reports only for projects where user is a member
        reports = Report.objects.filter(
            project_id__in=project_ids,
            submitted_by=user
        )

        # Filter by selected project
        if project_id:
            reports = reports.filter(project_id=project_id)

        # Filter by report type
        if report_type:
            reports = reports.filter(report_type=report_type)

        # Daily filter
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()

                start_datetime = timezone.make_aware(
                    datetime.combine(date, datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(date, datetime.max.time())
                )

                reports = reports.filter(
                    submitted_at__range=(start_datetime, end_datetime),
                    report_type='daily'
                )

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Weekly filter
        if week_str:
            try:
                week_date = datetime.strptime(week_str, '%Y-%m-%d').date()
                start_week = week_date - timedelta(days=week_date.weekday())
                end_week = start_week + timedelta(days=6)

                start_datetime = timezone.make_aware(
                    datetime.combine(start_week, datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(end_week, datetime.max.time())
                )

                reports = reports.filter(
                    submitted_at__range=(start_datetime, end_datetime),
                    report_type='weekly'
                )

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid week format (YYYY-MM-DD)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Monthly filter
        if month_str:
            try:
                month_date = datetime.strptime(month_str, '%Y-%m')
                start_month = month_date.replace(day=1)
                end_month = (start_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

                start_datetime = timezone.make_aware(
                    datetime.combine(start_month, datetime.min.time())
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(end_month, datetime.max.time())
                )

                reports = reports.filter(
                    submitted_at__range=(start_datetime, end_datetime),
                    report_type='monthly'
                )

            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid month format (YYYY-MM)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        reports = reports.select_related(
            'submitted_by',
            'submitted_by__staff_profile',
            'submitted_by__staff_profile__job_detail'
        ).prefetch_related(
            'tasks',
            'challenges'
        ).order_by('-submitted_at')

        paginator = Pagination()
        page = paginator.paginate_queryset(reports, request)

        serializer = ReportResponseSerializer(page, many=True)
        print("Requested Project:", project_id)

        return paginator.get_paginated_response(
            {
                "status": "1",
                "message": "success",
                "data": serializer.data
            }
        )
    

    @transaction.atomic
    def post(self, request):

        data = request.data

        # Convert JSON strings
        import json
        try:
            tasks = json.loads(data.get("tasks", "[]"))
            challenges = json.loads(data.get("challenges", "[]"))
            links = json.loads(data.get("links", "[]"))
        except ValueError:
            return Response(
                {"status": "0", "message": "Invalid JSON format"},
                status=400
            )

        serializer = ReportSerializer(
            data=data,
            context={'request': request}
        )

        if serializer.is_valid():

            validated = serializer.validated_data

            # Remove nested data before creating report
            attachments = validated.pop("attachments", [])
            validated.pop("tasks", None)
            validated.pop("challenges", None)
            validated.pop("links", None)

            # Create main report
            report = Report.objects.create(
                **validated,
                submitted_by=request.user
            )

            # Create Tasks
            ReportingTask.objects.bulk_create([
                ReportingTask(report=report, **task)
                for task in tasks
            ])

            # Create Challenges
            ChallengeResolution.objects.bulk_create([
                ChallengeResolution(report=report, **challenge)
                for challenge in challenges
            ])

            # Create Links
            ReportLink.objects.bulk_create([
                ReportLink(report=report, **link)
                for link in links
            ])

            # Create Attachments
            ReportAttachment.objects.bulk_create([
                ReportAttachment(report=report, file=file)
                for file in attachments
            ])

            return Response({
                "status": "1",
                "message": "Report created successfully",
                "report_id": report.id
            }, status=status.HTTP_201_CREATED)

        return Response({
            "status": "0",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


    @transaction.atomic
    def patch(self, request, id):

        try:
            report = Report.objects.get(
                id=id,
                submitted_by=request.user
            )
        except Report.DoesNotExist:
            return Response(
                {"status": "0", "message": "Report not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data

        import json
        from json import JSONDecodeError

        try:
            tasks = json.loads(data.get("tasks", "[]"))
            challenges = json.loads(data.get("challenges", "[]"))
            links = json.loads(data.get("links", "[]"))
        except JSONDecodeError:
            return Response(
                {"status": "0", "message": "Invalid JSON format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReportUpdateSerializer(
            report,
            data=data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():

            validated = serializer.validated_data

            attachments = validated.pop("attachments", None)
            validated.pop("tasks", None)
            validated.pop("challenges", None)
            validated.pop("links", None)

            # update main report fields
            for attr, value in validated.items():
                setattr(report, attr, value)

            report.save()

            # Replace tasks
            if tasks:
                report.tasks.all().delete()
                ReportingTask.objects.bulk_create([
                    ReportingTask(report=report, **task)
                    for task in tasks
                ])

            # Replace challenges
            if challenges:
                report.challenges.all().delete()
                ChallengeResolution.objects.bulk_create([
                    ChallengeResolution(report=report, **c)
                    for c in challenges
                ])

            # Replace links
            if links:
                report.links.all().delete()
                ReportLink.objects.bulk_create([
                    ReportLink(report=report, **l)
                    for l in links
                ])

            # Replace attachments
            if attachments is not None:
                report.attachments.all().delete()
                ReportAttachment.objects.bulk_create([
                    ReportAttachment(report=report, file=file)
                    for file in attachments
                ])

            return Response({
                "status": "1",
                "message": "Report updated successfully"
            }, status=status.HTTP_200_OK)

class ReportPrefillView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        report_type = request.query_params.get('type')  # 'weekly' or 'monthly'
        project_id = request.query_params.get('project')

        if not project_id:
            return Response(
                {"status": "0", "message": "project query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if report_type not in ['weekly', 'monthly']:
            return Response(
                {"status": "0", "message": "type must be 'weekly' or 'monthly'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        # Ensure user is a project member or has access
        member = Member.objects.filter(user=user).first()
        if not member:
            return Response(
                {"status": "0", "message": "User is not a project member"},
                status=status.HTTP_403_FORBIDDEN
            )

        is_member = ProjectMember.objects.filter(
            project_id=project_id,
            member=member
        ).exists()

        if not is_member:
            return Response(
                {"status": "0", "message": "You are not a member of this project"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 1. Determine Date Range
        if report_type == 'weekly':
            week_start_str = request.query_params.get('week_start')
            week_end_str = request.query_params.get('week_end')

            if not week_start_str or not week_end_str:
                return Response(
                    {"status": "0", "message": "week_start and week_end are required for weekly prefill"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                start_date = datetime.strptime(week_start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(week_end_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if start_date > end_date:
                return Response(
                    {"status": "0", "message": "week_start cannot be after week_end"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        else:  # monthly
            month_str = request.query_params.get('month')
            year_str = request.query_params.get('year')

            if not month_str or not year_str:
                return Response(
                    {"status": "0", "message": "month and year are required for monthly prefill"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                month = int(month_str)
                year = int(year_str)
                if not (1 <= month <= 12):
                    raise ValueError
                start_date = date(year, month, 1)
                end_date = date(year, month, monthrange(year, month)[1])
            except (ValueError, TypeError):
                return Response(
                    {"status": "0", "message": "Invalid month (1-12) or year"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. Fetch daily reports in the given date range for this user & project
        daily_reports = Report.objects.filter(
            project_id=project_id,
            submitted_by=user,
            report_type='daily',
            report_date__range=(start_date, end_date)
        ).prefetch_related(
            'tasks',
            'challenges',
            'links'
        ).order_by('report_date', 'submitted_at')

        # 3. Collect each day's tasks separately (no merging, preserving exact details)
        tasks_list = []
        total_hours = 0.0

        for r in daily_reports:
            report_date_str = r.report_date.strftime("%Y-%m-%d") if r.report_date else ""
            day_str = r.report_date.strftime("%a, %d %b") if r.report_date else ""

            for t in r.tasks.all():
                task_hours = float(t.hours)
                total_hours += task_hours
                tasks_list.append({
                    "date": report_date_str,
                    "day": day_str,
                    "task_name": t.task_name,
                    "task_description": t.task_description,
                    "status": t.status,
                    "progress_percentage": t.progress_percentage,
                    "hours": task_hours
                })

        # 4. Collect Challenges across the period
        challenges_list = []
        seen_challenges = set()
        for r in daily_reports:
            for c in r.challenges.all():
                ch_key = (c.issue.strip().lower(), c.impact.strip().lower())
                if ch_key not in seen_challenges:
                    seen_challenges.add(ch_key)
                    challenges_list.append({
                        "issue": c.issue,
                        "impact": c.impact,
                        "resolution": c.resolution
                    })

        # 5. Collect Links across the period
        links_list = []
        seen_urls = set()
        for r in daily_reports:
            for l in r.links.all():
                if l.url not in seen_urls:
                    seen_urls.add(l.url)
                    links_list.append({"url": l.url})

        # 6. Draft Executive Summary
        total_hours_rounded = round(total_hours, 2)
        if report_type == 'weekly':
            period_label = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
            summary_draft = f"Weekly summary for {period_label}: Completed {len(tasks_list)} task entries totaling {total_hours_rounded} worked hours across {daily_reports.count()} daily report(s)."
        else:
            summary_draft = f"Monthly summary for {start_date.strftime('%B %Y')}: Completed {len(tasks_list)} task entries totaling {total_hours_rounded} worked hours across {daily_reports.count()} daily report(s)."

        response_data = {
            "project": int(project_id),
            "report_type": report_type,
            "total_daily_reports": daily_reports.count(),
            "total_worked_hours": total_hours_rounded,
            "executive_summary": summary_draft,
            "next_period_plan": "",
            "tasks": tasks_list,
            "challenges": challenges_list,
            "links": links_list
        }

        if report_type == 'weekly':
            response_data["week_start"] = start_date.strftime("%Y-%m-%d")
            response_data["week_end"] = end_date.strftime("%Y-%m-%d")
        else:
            response_data["month"] = start_date.month
            response_data["year"] = start_date.year

        return Response({
            "status": "1",
            "message": f"{report_type.capitalize()} prefill data generated successfully",
            "data": response_data
        }, status=status.HTTP_200_OK)


class ReportListManagerView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    serializer_class = ReportResponseSerializer
    queryset = Report.objects.all().select_related(
            'submitted_by',
            'submitted_by__staff_profile',
            'submitted_by__staff_profile__job_detail'
        ).prefetch_related(
            'tasks',
            'challenges'
        ).order_by('-submitted_at')
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'project__id', 'submitted_by__id']

class ReportManagerDetailView(generics.RetrieveAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    serializer_class = ReportResponseSerializer
    queryset = Report.objects.all().select_related(
            'submitted_by',
            'submitted_by__staff_profile',
            'submitted_by__staff_profile__job_detail'
        ).prefetch_related(
            'tasks',
            'challenges'
        ).order_by('-submitted_at')
    lookup_field = 'id'


class ManagerWeeklyReportSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        project_id = request.query_params.get("project")
        month_str = request.query_params.get("month")

        if not project_id:
            return Response(
                {"status": "0", "message": "project is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = get_object_or_404(ProjectManagement, id=project_id)

        today = timezone.now().date()

        # -----------------------------
        # MONTH HANDLING
        # -----------------------------
        if not month_str:
            year, month = today.year, today.month
        else:
            try:
                year, month = map(int, month_str.split("-"))
            except:
                return Response(
                    {"status": "0", "message": "Invalid month format YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        last_day = monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        # -----------------------------
        # PROJECT RANGE
        # -----------------------------
        start_date = project.start_date
        end_date = min(project.end_date, today)

        # -----------------------------
        # PRELOAD MEMBERS
        # -----------------------------
        all_members = ProjectMember.objects.filter(
            project=project
        ).select_related(
            "member__user",
            "member__user__staff_profile__job_detail"
        )

        # -----------------------------
        # PRELOAD REPORTS
        # -----------------------------
        reports = Report.objects.filter(
            project=project,
            report_type="weekly"
        )


        weeks = []

        # align start to monday
        current = start_date - timedelta(days=start_date.weekday())

        # -----------------------------
        # LOOP WEEKS
        # -----------------------------
        while current <= end_date:

            week_start = current
            week_end = current + timedelta(days=5)

            # skip weeks outside month
            if week_end < month_start or week_start > month_end:
                current += timedelta(days=7)
                continue

            deadline = timezone.make_aware(
                datetime.combine(week_end, datetime.max.time())
            )

            submitted = 0
            late = 0
            pending = 0
            employees = []

            # filter members who joined before this week
            members = [
                m for m in all_members
                if m.created_at and m.created_at.date() <= week_end
            ]

            for pm in members:

                user = pm.member.user

                report = next(
                   (
                        r for r in reports
                        if r.submitted_by_id == user.id
                        and r.week_start <= week_end
                        and r.week_end >= week_start
                    ),
                    None
                )

                if report:

                    submitted_on = timezone.localtime(
                        report.submitted_at
                    ).date()

                    if report.submitted_at > deadline:
                        status_text = "Late"
                        late += 1
                    else:
                        status_text = "Submitted"
                        submitted += 1

                else:

                    if timezone.now() <= deadline:
                        status_text = "Pending"
                    else:
                        status_text = "Not Submitted"

                    submitted_on = None
                    pending += 1

                role = ""
                if hasattr(user, "staff_profile") and user.staff_profile:
                    jd = getattr(user.staff_profile, "job_detail", None)
                    if jd:
                        role = jd.role

                employees.append({
                    "name": f"{user.first_name} {user.last_name}",
                    "role": role,
                    "submitted_on": submitted_on,
                    "status": status_text,
                    "report_id": report.id if report else None
                })

            weeks.append({
                "week_start": week_start,
                "week": f"{week_start.strftime('%d %b')} – {week_end.strftime('%d %b %Y')}",
                "submitted": submitted,
                "late": late,
                "pending": pending,
                "employees": employees
            })

            current += timedelta(days=7)

        weeks = sorted(weeks, key=lambda x: x["week_start"], reverse=True)

        for w in weeks:
            w.pop("week_start")

        return Response(
            {
                "status": "1",
                "message": "success",
                "month": f"{year}-{str(month).zfill(2)}",
                "weeks": weeks
            },
            status=status.HTTP_200_OK
        )
    
    def delete(self, request):
        report_id = request.query_params.get("report_id")
        project_id = request.query_params.get("project")

        if not report_id:
            return Response(
                {"status": "0", "message": "report_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not project_id:
            return Response(
                {"status": "0", "message": "project required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        report = get_object_or_404(
            Report,
            id=report_id,
            project_id=project_id,
            report_type="weekly",
        )

        report.delete()

        return Response(
            {
                "status": "1",
                "message": "Weekly report deleted successfully"
            },
            status=status.HTTP_200_OK
        )
    
class ManagerMonthlyReportSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        project_id = request.query_params.get("project")
        month_param = request.query_params.get("month")
        year_param = request.query_params.get("year")

        if not project_id:
            return Response(
                {"status": "0", "message": "project required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = get_object_or_404(ProjectManagement, id=project_id)

        today = timezone.now().date()

        # -----------------------------
        # MONTH & YEAR
        # -----------------------------
        month = int(month_param) if month_param else today.month
        year = int(year_param) if year_param else today.year

        last_day = monthrange(year, month)[1]
        month_end = date(year, month, last_day)

        # timezone-safe datetime
        month_end_datetime = timezone.make_aware(
            datetime.combine(month_end, datetime.max.time())
        )

        # -----------------------------
        # MEMBERS (joined before month end)
        # -----------------------------
        members = ProjectMember.objects.filter(
            project=project,
            created_at__lte=month_end_datetime
        ).select_related(
            "member__user",
            "member__user__staff_profile__job_detail"
        )

        # -----------------------------
        # REPORTS
        # -----------------------------
        reports = Report.objects.filter(
            project=project,
            report_type="monthly",
            month=month,
            year=year
        )

        report_map = {r.submitted_by_id: r for r in reports}

        submitted = 0
        late = 0
        pending = 0
        employees = []

        # -----------------------------
        # DEADLINE
        # -----------------------------
        deadline = timezone.make_aware(
            datetime(year, month, last_day, 23, 59, 59)
        )

        # -----------------------------
        # LOOP MEMBERS
        # -----------------------------
        for pm in members:

            user = pm.member.user
            report = report_map.get(user.id)

            if report:

                submitted_on = timezone.localtime(
                    report.submitted_at
                ).date()

                if report.submitted_at > deadline:
                    status_text = "Late"
                    late += 1
                else:
                    status_text = "Submitted"
                    submitted += 1

            else:

                if timezone.now() <= deadline:
                    status_text = "Pending"
                else:
                    status_text = "Not Submitted"

                submitted_on = None
                pending += 1

            role = ""
            if hasattr(user, "staff_profile") and user.staff_profile:
                jd = getattr(user.staff_profile, "job_detail", None)
                if jd:
                    role = jd.role

            employees.append({
                "name": f"{user.first_name} {user.last_name}",
                "role": role,
                "submitted_on": submitted_on,
                "status": status_text,
                "report_id": report.id if report else None
            })

        return Response(
            {
                "status": "1",
                "message": "success",
                "month": f"{year}-{str(month).zfill(2)}",
                "submitted": submitted,
                "late": late,
                "pending": pending,
                "employees": employees
            },
            status=status.HTTP_200_OK
        )


class ManagerDailyReportSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        project_id = request.query_params.get("project")
        date_param = request.query_params.get("date")

        if not project_id:
            return Response(
                {"status": "0", "message": "project required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = get_object_or_404(ProjectManagement, id=project_id)

        # -----------------------------
        # SELECTED DATE
        # -----------------------------
        if date_param:
            try:
                selected_date = datetime.strptime(date_param, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            selected_date = timezone.now().date()

        # End of day (used for member filtering)
        day_end = timezone.make_aware(
            datetime.combine(selected_date, datetime.max.time())
        )
        # Report submission deadline: 6:30 PM
        deadline = timezone.make_aware(
            datetime.combine(
                selected_date,
                datetime.strptime("18:30", "%H:%M").time()
            )
        )
        # -----------------------------
        # MEMBERS (joined before this day)
        # -----------------------------
        members = ProjectMember.objects.filter(
            project=project,
            created_at__lte=day_end
        ).select_related(
            "member__user",
            "member__user__staff_profile__job_detail"
        )

        # -----------------------------
        # REPORTS
        # -----------------------------
        reports = Report.objects.filter(
            project=project,
            report_type="daily",
            report_date=selected_date
        )

        report_map = {r.submitted_by_id: r for r in reports}

        submitted = 0
        late = 0
        pending = 0
        employees = []

        # deadline = day_end

        # -----------------------------
        # LOOP MEMBERS
        # -----------------------------
        for pm in members:

            user = pm.member.user
            report = report_map.get(user.id)

            if report:

                submitted_on = timezone.localtime(
                    report.submitted_at
                ).strftime("%Y-%m-%d %H:%M:%S")

                if report.submitted_at > deadline:
                    status_text = "Late"
                    late += 1
                else:
                    status_text = "Submitted"
                    submitted += 1

            else:

                if timezone.now() <= deadline:
                    status_text = "Pending"
                else:
                    status_text = "Not Submitted"

                submitted_on = None
                pending += 1

            role = ""
            if hasattr(user, "staff_profile") and user.staff_profile:
                jd = getattr(user.staff_profile, "job_detail", None)
                if jd:
                    role = jd.role

            employees.append({
                "name": f"{user.first_name} {user.last_name}",
                "role": role,
                "submitted_on": submitted_on,
                "status": status_text,
                "report_id": report.id if report else None
            })

        return Response(
            {
                "status": "1",
                "message": "success",
                "date": str(selected_date),
                "submitted": submitted,
                "late": late,
                "pending": pending,
                "employees": employees
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request):
        report_id = request.query_params.get("report_id")
        project_id = request.query_params.get("project")

        if not report_id:
            return Response(
                {"status": "0", "message": "report_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not project_id:
            return Response(
                {"status": "0", "message": "project required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        report = get_object_or_404(
            Report,
            id=report_id,
            project_id=project_id,
            report_type="daily"
        )

        report.delete()

        return Response(
            {
                "status": "1",
                "message": "Report deleted successfully"
            },
            status=status.HTTP_200_OK
        )


class ManagerStaffReportsConsolidatedView(APIView):
    """
    Consolidated view returning all staff reports in a single endpoint.
    Aggregates performance metrics, task breakdown counts, total hours,
    and roadblock indicators without requiring task-by-task drilldown.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project")
        report_type = request.query_params.get("type") or request.query_params.get("report_type")  # daily, weekly, monthly, or all
        staff_id = request.query_params.get("staff_id") or request.query_params.get("member_id")
        search = request.query_params.get("search")

        # Period filters
        date_str = request.query_params.get("date")               # YYYY-MM-DD
        week_start_str = request.query_params.get("week_start")   # YYYY-MM-DD
        week_end_str = request.query_params.get("week_end")       # YYYY-MM-DD
        month_param = request.query_params.get("month")           # 1-12 or YYYY-MM
        year_param = request.query_params.get("year")             # YYYY
        start_date_str = request.query_params.get("start_date")   # general date range
        end_date_str = request.query_params.get("end_date")

        reports = Report.objects.all().select_related(
            'project',
            'submitted_by',
            'submitted_by__staff_profile',
            'submitted_by__staff_profile__job_detail'
        ).prefetch_related(
            'tasks'
        ).order_by('-submitted_at')

        if project_id:
            reports = reports.filter(project_id=project_id)

        if report_type and report_type.lower() != 'all':
            reports = reports.filter(report_type=report_type.lower())

        if staff_id:
            reports = reports.filter(submitted_by_id=staff_id)

        # Handle month format "YYYY-MM" or separate month & year
        if month_param:
            if "-" in str(month_param):
                try:
                    m_year, m_month = map(int, month_param.split("-"))
                    reports = reports.filter(
                        Q(month=m_month, year=m_year) |
                        Q(report_date__year=m_year, report_date__month=m_month) |
                        Q(week_start__year=m_year, week_start__month=m_month)
                    )
                except ValueError:
                    pass
            else:
                try:
                    m_val = int(month_param)
                    reports = reports.filter(month=m_val)
                except ValueError:
                    pass

        if year_param:
            try:
                y_val = int(year_param)
                reports = reports.filter(
                    Q(year=y_val) |
                    Q(report_date__year=y_val) |
                    Q(week_start__year=y_val)
                )
            except ValueError:
                pass

        # Handle daily date filter
        if date_str:
            try:
                d_val = datetime.strptime(date_str, "%Y-%m-%d").date()
                reports = reports.filter(
                    Q(report_date=d_val) |
                    Q(submitted_at__date=d_val)
                )
            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid date format YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Handle weekly date range
        if week_start_str and week_end_str:
            try:
                ws_val = datetime.strptime(week_start_str, "%Y-%m-%d").date()
                we_val = datetime.strptime(week_end_str, "%Y-%m-%d").date()
                reports = reports.filter(
                    week_start__lte=we_val,
                    week_end__gte=ws_val
                )
            except ValueError:
                return Response(
                    {"status": "0", "message": "Invalid week_start or week_end format YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # General date range
        if start_date_str:
            try:
                sd_val = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                reports = reports.filter(
                    Q(report_date__gte=sd_val) |
                    Q(week_start__gte=sd_val) |
                    Q(submitted_at__date__gte=sd_val)
                )
            except ValueError:
                pass

        if end_date_str:
            try:
                ed_val = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                reports = reports.filter(
                    Q(report_date__lte=ed_val) |
                    Q(week_end__lte=ed_val) |
                    Q(submitted_at__date__lte=ed_val)
                )
            except ValueError:
                pass

        # Search filter
        if search:
            search = search.strip()
            reports = reports.filter(
                Q(submitted_by__first_name__icontains=search) |
                Q(submitted_by__last_name__icontains=search) |
                Q(submitted_by__email__icontains=search) |
                Q(executive_summary__icontains=search) |
                Q(project__project_name__icontains=search)
            )

        # Compute high-level summary overview
        all_reports_list = list(reports)
        total_reports_count = len(all_reports_list)
        unique_staff_ids = set(r.submitted_by_id for r in all_reports_list if r.submitted_by_id)

        total_tasks = 0
        completed_tasks = 0
        in_progress_tasks = 0

        for r in all_reports_list:
            r_tasks = list(r.tasks.all())
            total_tasks += len(r_tasks)
            completed_tasks += sum(1 for t in r_tasks if t.status == 'completed')
            in_progress_tasks += sum(1 for t in r_tasks if t.status == 'in_progress')

        summary = {
            "total_reports": total_reports_count,
            "total_staff_count": len(unique_staff_ids),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
        }

        # Check pagination
        page_param = request.query_params.get("page")
        page_size_param = request.query_params.get("page_size")

        if page_param or (page_size_param and page_size_param.lower() != 'all'):
            paginator = Pagination()
            page = paginator.paginate_queryset(reports, request)
            serializer = StaffReportConsolidatedSerializer(page, many=True)
            return paginator.get_paginated_response({
                "status": "1",
                "message": "success",
                "summary": summary,
                "data": serializer.data
            })

        serializer = StaffReportConsolidatedSerializer(all_reports_list, many=True)
        return Response({
            "status": "1",
            "message": "success",
            "summary": summary,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


