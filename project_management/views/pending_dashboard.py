from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from project_management.models import (
    ProjectManagement,
    ClientContract,
    DMContract,
    Task,
    TaskAssign,
    TaskBoard,
    ProjectMember,
    Member,
    Report,
    ProjectNote,
    MeetingAttendance,
)
from project_management.models.testing import (
    BugReport,
    BugStatusHistory,
)
from project_management.serializers.pending_dashboard import (
    ProjectManagementPendingDashboardSerializer,
    DigitalMarketingPendingDashboardSerializer,
    TestingManagementPendingDashboardSerializer,
)


# =============================================================================
# Helper: Standard Pending Work Filtering & Builder
# =============================================================================
def build_pending_dashboard_response(
    module_key,
    module_label,
    tab_definitions,
    tab_items,
    tab_categories,
    active_tab,
    urgency_filter,
    search_query,
    limit_param,
):
    """
    Standard builder for cross-module pending works dashboard response.
    Computes total_pending_count, tab_counts, category summaries, applies filtering,
    and returns a DRF Response.
    """
    try:
        limit = max(1, min(int(limit_param), 500))
    except (ValueError, TypeError):
        limit = 100

    # Calculate counts per tab and overall total
    tab_counts = {}
    total_pending_count = 0
    tabs_data = []

    for tab in tab_definitions:
        t_key = tab["key"]
        items_for_tab = tab_items.get(t_key, [])
        count_tab = len(items_for_tab)
        tab_counts[t_key] = count_tab
        total_pending_count += count_tab

        # Group categories in tab
        cat_map = tab_categories.get(t_key, {})
        categories_list = [
            {"key": cat_key, "label": cat_info["label"], "count": cat_info["count"]}
            for cat_key, cat_info in cat_map.items()
        ]

        tabs_data.append({
            "key": t_key,
            "label": tab["label"],
            "count": count_tab,
            "categories": categories_list,
        })

    # Select items for the active tab (or 'all')
    if active_tab == "all" or active_tab not in tab_counts:
        candidate_items = []
        for tab in tab_definitions:
            candidate_items.extend(tab_items.get(tab["key"], []))
    else:
        candidate_items = list(tab_items.get(active_tab, []))

    # Apply Urgency Filter
    if urgency_filter:
        candidate_items = [i for i in candidate_items if i.get("urgency") == urgency_filter]

    # Apply Search Filter (title, description, work_type_label, meta values)
    if search_query:
        filtered = []
        for item in candidate_items:
            haystack = f"{item.get('title', '')} {item.get('description', '')} {item.get('work_type_label', '')}".lower()
            meta = item.get("meta") or {}
            for v in meta.values():
                if v is not None:
                    haystack += f" {str(v).lower()}"
            if search_query in haystack:
                filtered.append(item)
        candidate_items = filtered

    # Sort: high urgency first, then due_date/created_at
    urgency_weight = {"high": 3, "medium": 2, "low": 1}
    candidate_items.sort(
        key=lambda x: (
            urgency_weight.get(x.get("urgency"), 0),
            str(x.get("due_date") or ""),
            str(x.get("created_at") or "")
        ),
        reverse=True
    )

    items_to_return = candidate_items[:limit]

    return Response(
        data={
            "status": "1",
            "message": "success",
            "data": {
                "module": module_key,
                "module_label": module_label,
                "total_pending_count": total_pending_count,
                "tab_counts": tab_counts,
                "tabs": tabs_data,
                "active_tab": active_tab,
                "items_count": len(items_to_return),
                "items": items_to_return,
            }
        },
        status=status.HTTP_200_OK
    )


# =============================================================================
# 1. Project Management Pending Dashboard API View
# =============================================================================
class ProjectManagementPendingDashboardAPIView(APIView):
    """
    Project Management Module Pending Controls / Works Dashboard API.
    
    Monitors actionable pending tasks across:
      - projects: Overdue projects, projects without members, projects with no task boards, on-hold stalled projects
      - tasks: Overdue active tasks, unassigned tasks, stuck in-progress tasks, tasks due today
      - reports: Daily reports missing for active members, reports without logged hours/tasks
      - meetings: Overdue meetings with no attendance taken, upcoming meetings missing agenda/tasks
      - members: Members with zero active project assignments, project members with no tasks
      - contracts: Client contracts with no linked project, expired contracts with active projects
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "projects", "label": "Projects"},
        {"key": "tasks", "label": "Tasks & Assignments"},
        {"key": "reports", "label": "Reports"},
        {"key": "meetings", "label": "Meetings & Notes"},
        {"key": "members", "label": "Team Members"},
        {"key": "contracts", "label": "Client Contracts"},
    ]

    def get(self, request):
        today = timezone.localdate()
        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()
        project_id_param = request.query_params.get("project_id")

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(tab_key, work_type, work_type_label, title, description, urgency, record_id=None, item_id=None, created_at=None, due_date=None, action_url=None, meta=None):
            if not item_id:
                item_id = f"pm_{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"

            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {"label": work_type_label, "count": 0}
            tab_categories[tab_key][work_type]["count"] += 1

            tab_items[tab_key].append({
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": next((t["label"] for t in self.TAB_DEFINITIONS if t["key"] == tab_key), tab_key),
                "work_type": work_type,
                "work_type_label": work_type_label,
                "title": title,
                "description": description,
                "urgency": urgency,
                "created_at": created_at,
                "due_date": due_date,
                "action_url": action_url,
                "meta": meta or {},
            })

        # Base QuerySets (Dev / All projects if general PM)
        projects_qs = ProjectManagement.objects.all().select_related('user', 'contract', 'dm_contract')
        if project_id_param:
            try:
                projects_qs = projects_qs.filter(id=int(project_id_param))
            except (ValueError, TypeError):
                pass

        # ---------------------------------------------------------------------
        # Tab 1: Projects Pending Controls
        # ---------------------------------------------------------------------
        for proj in projects_qs:
            # Overdue project: status not completed and end_date < today
            if proj.status not in ['completed', 'cancelled'] and proj.end_date and proj.end_date < today:
                overdue_days = (today - proj.end_date).days
                add_item(
                    tab_key="projects",
                    work_type="overdue_project",
                    work_type_label="Overdue Project",
                    title=f"Project Deadline Passed: {proj.project_name}",
                    description=f"Project deadline was {proj.end_date.strftime('%d %b %Y')} ({overdue_days} day(s) overdue). Current status is '{proj.status}'.",
                    urgency="high",
                    record_id=proj.id,
                    due_date=proj.end_date,
                    action_url=f"/project_management/{proj.id}/",
                    meta={
                        "project_id": proj.id,
                        "project_name": proj.project_name,
                        "project_number": proj.project_number,
                        "status": proj.status,
                        "overdue_days": overdue_days,
                    }
                )

            # Project with no team members allocated
            active_members_count = proj.projectmember_set.filter(is_active=True).count()
            if proj.status in ['not_started', 'in_progress'] and active_members_count == 0:
                add_item(
                    tab_key="projects",
                    work_type="project_missing_members",
                    work_type_label="Project Without Team Members",
                    title=f"No Active Team Members: {proj.project_name}",
                    description=f"Project '{proj.project_name}' has 0 active team members allocated to it.",
                    urgency="high",
                    record_id=proj.id,
                    action_url=f"/project_management/{proj.id}/members/",
                    meta={
                        "project_id": proj.id,
                        "project_name": proj.project_name,
                        "status": proj.status,
                    }
                )

            # Active project with no task boards
            boards_count = proj.taskboard_set.count()
            if proj.status == 'in_progress' and boards_count == 0:
                add_item(
                    tab_key="projects",
                    work_type="project_missing_boards",
                    work_type_label="Project Missing Task Board",
                    title=f"No Task Board: {proj.project_name}",
                    description=f"Project is in progress but has no sprint/task board created.",
                    urgency="medium",
                    record_id=proj.id,
                    action_url=f"/project_management/{proj.id}/boards/",
                    meta={
                        "project_id": proj.id,
                        "project_name": proj.project_name,
                    }
                )

            # Project on hold for a long time
            if proj.status == 'on_hold':
                add_item(
                    tab_key="projects",
                    work_type="project_on_hold",
                    work_type_label="Project On Hold",
                    title=f"Project On Hold: {proj.project_name}",
                    description=f"Project is currently placed on hold and requires manager review or client follow-up.",
                    urgency="medium",
                    record_id=proj.id,
                    action_url=f"/project_management/{proj.id}/",
                    meta={
                        "project_id": proj.id,
                        "project_name": proj.project_name,
                    }
                )

        # ---------------------------------------------------------------------
        # Tab 2: Tasks & Assignments Pending Controls
        # ---------------------------------------------------------------------
        tasks_qs = Task.objects.select_related('project', 'board').prefetch_related('assignments__assigned_to__member__user')
        if project_id_param:
            tasks_qs = tasks_qs.filter(project_id=project_id_param)

        for t in tasks_qs:
            # Overdue task
            if t.status not in ['completed', 'cancelled'] and t.end_date and t.end_date < today:
                overdue_days = (today - t.end_date).days
                assignee_names = [
                    a.assigned_to.member.user.get_full_name() or a.assigned_to.member.user.username
                    for a in t.assignments.all() if a.assigned_to and a.assigned_to.member
                ]
                add_item(
                    tab_key="tasks",
                    work_type="overdue_task",
                    work_type_label="Overdue Task",
                    title=f"Task Overdue: {t.task_name}",
                    description=f"Task was due on {t.end_date.strftime('%d %b %Y')} ({overdue_days} day(s) overdue). Assigned to: {', '.join(assignee_names) or 'Unassigned'}.",
                    urgency="high",
                    record_id=t.id,
                    due_date=t.end_date,
                    action_url=f"/project_management/task/{t.id}/",
                    meta={
                        "task_id": t.id,
                        "task_name": t.task_name,
                        "project_name": t.project.project_name if t.project else None,
                        "project_id": t.project_id,
                        "assignees": assignee_names,
                        "status": t.status,
                        "overdue_days": overdue_days,
                    }
                )

            # Unassigned task
            if t.status not in ['completed', 'cancelled'] and t.assignments.count() == 0:
                add_item(
                    tab_key="tasks",
                    work_type="unassigned_task",
                    work_type_label="Unassigned Task",
                    title=f"Unassigned Task: {t.task_name}",
                    description=f"Task '{t.task_name}' in project '{t.project.project_name if t.project else 'General'}' has not been assigned to any team member.",
                    urgency="medium",
                    record_id=t.id,
                    due_date=t.end_date,
                    action_url=f"/project_management/task/{t.id}/",
                    meta={
                        "task_id": t.id,
                        "task_name": t.task_name,
                        "project_name": t.project.project_name if t.project else None,
                    }
                )

            # Task due today
            if t.status not in ['completed', 'cancelled'] and t.end_date == today:
                add_item(
                    tab_key="tasks",
                    work_type="task_due_today",
                    work_type_label="Task Due Today",
                    title=f"Task Due Today: {t.task_name}",
                    description=f"Task deadline is today. Review submission or progress before day end.",
                    urgency="high",
                    record_id=t.id,
                    due_date=today,
                    action_url=f"/project_management/task/{t.id}/",
                    meta={
                        "task_id": t.id,
                        "task_name": t.task_name,
                        "project_name": t.project.project_name if t.project else None,
                    }
                )

        # ---------------------------------------------------------------------
        # Tab 3: Reports Pending Controls
        # ---------------------------------------------------------------------
        # Check active project members who haven't submitted a report today
        active_p_members = ProjectMember.objects.filter(
            is_active=True,
            project__status__in=['in_progress', 'not_started']
        ).select_related('member__user', 'project')
        
        # Reports submitted today
        submitted_today_user_ids = set(
            Report.objects.filter(
                report_type='daily',
                report_date=today
            ).values_list('submitted_by_id', flat=True)
        )

        for pm in active_p_members:
            if pm.member and pm.member.user_id not in submitted_today_user_ids:
                u = pm.member.user
                full_name = u.get_full_name() or u.username
                add_item(
                    tab_key="reports",
                    work_type="missing_daily_report",
                    work_type_label="Missing Daily Work Report",
                    title=f"Daily Report Missing: {full_name}",
                    description=f"Team member '{full_name}' on project '{pm.project.project_name}' has not submitted a daily report for today.",
                    urgency="medium",
                    record_id=pm.id,
                    action_url=f"/project_management/report/",
                    meta={
                        "project_id": pm.project_id,
                        "project_name": pm.project.project_name,
                        "user_id": u.id,
                        "user_name": full_name,
                    }
                )

        # Reports with 0 logged hours
        empty_reports = Report.objects.annotate(task_count=Count('tasks')).filter(task_count=0)[:50]
        for rep in empty_reports:
            add_item(
                tab_key="reports",
                work_type="report_without_task_entries",
                work_type_label="Empty Report Details",
                title=f"Report Missing Task Breakdown: #{rep.id}",
                description=f"Report submitted by {rep.submitted_by.get_full_name() or rep.submitted_by.username} for {rep.project.project_name} has 0 task details/hours logged.",
                urgency="low",
                record_id=rep.id,
                due_date=rep.report_date,
                action_url=f"/project_management/report/{rep.id}/",
                meta={
                    "report_id": rep.id,
                    "project_name": rep.project.project_name,
                    "report_type": rep.report_type,
                }
            )

        # ---------------------------------------------------------------------
        # Tab 4: Meetings & Notes Pending Controls
        # ---------------------------------------------------------------------
        meetings_qs = ProjectNote.objects.filter(meeting_date__isnull=False).select_related('project', 'created_by')
        for m in meetings_qs:
            # Overdue meeting without attendance recorded
            attendance_count = m.attendances.count()
            if m.meeting_date and m.meeting_date < today and attendance_count == 0:
                add_item(
                    tab_key="meetings",
                    work_type="meeting_missing_attendance",
                    work_type_label="Meeting Attendance Not Logged",
                    title=f"Attendance Not Recorded: {m.title}",
                    description=f"Meeting was conducted on {m.meeting_date.strftime('%d %b %Y')}, but attendance has not been recorded.",
                    urgency="medium",
                    record_id=m.id,
                    due_date=m.meeting_date,
                    action_url=f"/project_management/meetings/{m.id}/attendance/",
                    meta={
                        "meeting_id": m.id,
                        "title": m.title,
                        "project_name": m.project.project_name if m.project else None,
                        "meeting_date": str(m.meeting_date),
                    }
                )

            # Meeting without action items / tasks linked
            if m.meeting_date and m.meeting_date <= today and m.meeting_tasks.count() == 0:
                add_item(
                    tab_key="meetings",
                    work_type="meeting_missing_tasks",
                    work_type_label="Meeting Missing Action Items",
                    title=f"No Action Items: {m.title}",
                    description=f"Meeting has no actionable tasks linked to it for team follow-through.",
                    urgency="low",
                    record_id=m.id,
                    action_url=f"/project_management/meetings/{m.id}/tasks/",
                    meta={
                        "meeting_id": m.id,
                        "title": m.title,
                        "project_name": m.project.project_name if m.project else None,
                    }
                )

        # ---------------------------------------------------------------------
        # Tab 5: Team Members Pending Controls
        # ---------------------------------------------------------------------
        # Active Members with 0 active project memberships
        members_without_projects = Member.objects.filter(
            is_active=True
        ).annotate(
            active_p_count=Count('projectmember', filter=Q(projectmember__is_active=True))
        ).filter(active_p_count=0).select_related('user')

        for mem in members_without_projects:
            full_name = mem.user.get_full_name() or mem.user.username
            add_item(
                tab_key="members",
                work_type="unallocated_member",
                work_type_label="Unallocated Team Member",
                title=f"Unallocated Member: {full_name}",
                description=f"Staff member is active in team pool but currently allocated to 0 active projects.",
                urgency="medium",
                record_id=mem.id,
                action_url=f"/project_management/project_members/",
                meta={
                    "member_id": mem.id,
                    "user_id": mem.user.id,
                    "user_name": full_name,
                }
            )

        # ---------------------------------------------------------------------
        # Tab 6: Client Contracts Pending Controls
        # ---------------------------------------------------------------------
        # Contracts without any created project
        contracts_without_projects = ClientContract.objects.annotate(
            proj_count=Count('projectmanagement')
        ).filter(proj_count=0)

        for c in contracts_without_projects:
            add_item(
                tab_key="contracts",
                work_type="contract_missing_project",
                work_type_label="Signed Contract Without Project",
                title=f"No Project Created: {c.contract_name}",
                description=f"Client contract '{c.contract_number or c.contract_name}' signed on {c.contract_date} has no active development/project linked.",
                urgency="high",
                record_id=c.id,
                due_date=c.end_date,
                action_url=f"/project_management/",
                meta={
                    "contract_id": c.id,
                    "contract_name": c.contract_name,
                    "contract_number": c.contract_number,
                    "client_id": c.client_id,
                }
            )

        # Expired contracts
        expired_contracts = ClientContract.objects.filter(end_date__lt=today)
        for c in expired_contracts:
            # Check if project is still in progress
            has_ongoing_proj = ProjectManagement.objects.filter(
                contract=c,
                status__in=['not_started', 'in_progress', 'on_hold']
            ).exists()
            if has_ongoing_proj:
                add_item(
                    tab_key="contracts",
                    work_type="expired_contract_ongoing_project",
                    work_type_label="Contract Expired with Active Project",
                    title=f"Contract Term Expired: {c.contract_name}",
                    description=f"Contract expired on {c.end_date.strftime('%d %b %Y')}, but associated project remains active. Extension or renewal required.",
                    urgency="high",
                    record_id=c.id,
                    due_date=c.end_date,
                    action_url=f"/project_management/client_contract/{c.id}/",
                    meta={
                        "contract_id": c.id,
                        "contract_name": c.contract_name,
                        "end_date": str(c.end_date),
                    }
                )

        return build_pending_dashboard_response(
            module_key="project_management",
            module_label="Project Management",
            tab_definitions=self.TAB_DEFINITIONS,
            tab_items=tab_items,
            tab_categories=tab_categories,
            active_tab=active_tab,
            urgency_filter=urgency_filter,
            search_query=search_query,
            limit_param=limit_param,
        )


# =============================================================================
# 2. Digital Marketing Pending Dashboard API View
# =============================================================================
class DigitalMarketingPendingDashboardAPIView(APIView):
    """
    Digital Marketing Module Pending Controls / Works Dashboard API.
    
    Monitors actionable pending tasks across:
      - contracts: Expiring contracts, overdue contracts, contracts without deliverables/works, contracts without platforms
      - deliverables: Contracts with 0 defined work items or deliverables
      - platforms: Contracts missing digital marketing platform links/handles
      - extensions: Expiring contracts needing extension or renewal review
      - projects: DM projects without linked DM contract or missing team assignments
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "contracts", "label": "Contracts & Expiry"},
        {"key": "deliverables", "label": "Work Deliverables"},
        {"key": "platforms", "label": "Platform Accounts & Links"},
        {"key": "projects", "label": "DM Projects & Execution"},
    ]

    def get(self, request):
        today = timezone.localdate()
        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(tab_key, work_type, work_type_label, title, description, urgency, record_id=None, item_id=None, created_at=None, due_date=None, action_url=None, meta=None):
            if not item_id:
                item_id = f"dm_{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"

            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {"label": work_type_label, "count": 0}
            tab_categories[tab_key][work_type]["count"] += 1

            tab_items[tab_key].append({
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": next((t["label"] for t in self.TAB_DEFINITIONS if t["key"] == tab_key), tab_key),
                "work_type": work_type,
                "work_type_label": work_type_label,
                "title": title,
                "description": description,
                "urgency": urgency,
                "created_at": created_at,
                "due_date": due_date,
                "action_url": action_url,
                "meta": meta or {},
            })

        dm_contracts = DMContract.objects.all().select_related('client', 'user').prefetch_related(
            'contract_works__work_type',
            'contract_platforms__platform',
            'contract_links',
            'extensions',
            'projects'
        )

        for dmc in dm_contracts:
            effective_end = dmc.revised_end_date
            client_name = "Client"
            if dmc.client:
                full_c_name = f"{dmc.client.first_name} {dmc.client.last_name or ''}".strip()
                client_name = full_c_name or dmc.client.company_name or str(dmc.client)

            # -----------------------------------------------------------------
            # Tab 1: Contracts & Expiry
            # -----------------------------------------------------------------
            # Expired contract with active/in_progress work status
            if dmc.work_status in ['pending', 'active', 'in_progress'] and effective_end and effective_end < today:
                overdue_days = (today - effective_end).days
                add_item(
                    tab_key="contracts",
                    work_type="contract_expired_unextended",
                    work_type_label="Contract Term Expired",
                    title=f"DM Contract Expired: {dmc.contract_name}",
                    description=f"Contract for '{client_name}' expired on {effective_end.strftime('%d %b %Y')} ({overdue_days} day(s) ago). Work status is '{dmc.work_status}'. Extension or completion needed.",
                    urgency="high",
                    record_id=dmc.id,
                    due_date=effective_end,
                    action_url=f"/project_management/dm-contracts/{dmc.id}/extensions/",
                    meta={
                        "contract_id": dmc.id,
                        "contract_number": dmc.contract_number,
                        "client_name": client_name,
                        "work_status": dmc.work_status,
                        "effective_end_date": str(effective_end),
                        "overdue_days": overdue_days,
                    }
                )

            # Contract expiring soon (within 7 days)
            elif dmc.work_status in ['active', 'in_progress'] and effective_end and today <= effective_end <= (today + timedelta(days=7)):
                days_left = (effective_end - today).days
                add_item(
                    tab_key="contracts",
                    work_type="contract_expiring_soon",
                    work_type_label="Contract Expiring Soon (7 Days)",
                    title=f"Contract Ending Soon: {dmc.contract_name}",
                    description=f"Contract for '{client_name}' ends on {effective_end.strftime('%d %b %Y')} ({days_left} day(s) remaining). Review deliverables and renewal.",
                    urgency="high" if days_left <= 2 else "medium",
                    record_id=dmc.id,
                    due_date=effective_end,
                    action_url=f"/project_management/dm-contracts/{dmc.id}/",
                    meta={
                        "contract_id": dmc.id,
                        "contract_number": dmc.contract_number,
                        "client_name": client_name,
                        "days_left": days_left,
                    }
                )

            # Contract on hold
            if dmc.work_status == 'on_hold':
                add_item(
                    tab_key="contracts",
                    work_type="contract_on_hold",
                    work_type_label="Contract On Hold",
                    title=f"DM Contract On Hold: {dmc.contract_name}",
                    description=f"Contract work is currently paused/on hold. Review client feedback or pending approvals.",
                    urgency="medium",
                    record_id=dmc.id,
                    action_url=f"/project_management/dm-contracts/{dmc.id}/",
                    meta={
                        "contract_id": dmc.id,
                        "contract_number": dmc.contract_number,
                        "client_name": client_name,
                    }
                )

            # -----------------------------------------------------------------
            # Tab 2: Deliverables Pending Controls
            # -----------------------------------------------------------------
            works_count = dmc.contract_works.count()
            if dmc.work_status in ['pending', 'active', 'in_progress'] and works_count == 0:
                add_item(
                    tab_key="deliverables",
                    work_type="contract_missing_deliverables",
                    work_type_label="Contract Missing Deliverables",
                    title=f"No Deliverables Configured: {dmc.contract_name}",
                    description=f"Contract has 0 work deliverables defined (e.g. posters, reels, SEO, campaigns).",
                    urgency="high",
                    record_id=dmc.id,
                    action_url=f"/project_management/dm-contracts/{dmc.id}/",
                    meta={
                        "contract_id": dmc.id,
                        "contract_number": dmc.contract_number,
                        "client_name": client_name,
                    }
                )

            # -----------------------------------------------------------------
            # Tab 3: Platforms & Social Links Pending Controls
            # -----------------------------------------------------------------
            platforms_count = dmc.contract_platforms.count()
            if dmc.work_status in ['active', 'in_progress'] and platforms_count == 0:
                add_item(
                    tab_key="platforms",
                    work_type="contract_missing_platforms",
                    work_type_label="No Platforms Assigned",
                    title=f"Missing Target Platforms: {dmc.contract_name}",
                    description=f"Active contract has no marketing platforms assigned (Instagram, Facebook, Google, etc.).",
                    urgency="medium",
                    record_id=dmc.id,
                    action_url=f"/project_management/dm-contracts/{dmc.id}/",
                    meta={
                        "contract_id": dmc.id,
                        "contract_number": dmc.contract_number,
                    }
                )

            links_count = dmc.contract_links.count()
            if dmc.work_status in ['active', 'in_progress'] and links_count == 0:
                add_item(
                    tab_key="platforms",
                    work_type="contract_missing_links",
                    work_type_label="No Social Media Links Configured",
                    title=f"No Profile Links: {dmc.contract_name}",
                    description=f"Client social profile handles and website links are not configured on this contract.",
                    urgency="low",
                    record_id=dmc.id,
                    action_url=f"/project_management/dm-contracts/{dmc.id}/",
                    meta={
                        "contract_id": dmc.id,
                        "contract_number": dmc.contract_number,
                    }
                )

            # -----------------------------------------------------------------
            # Tab 4: DM Projects & Execution Pending Controls
            # -----------------------------------------------------------------
            # DM Contract has no associated execution project
            linked_projects = dmc.projects.all()
            if dmc.work_status in ['active', 'in_progress'] and not linked_projects.exists():
                add_item(
                    tab_key="projects",
                    work_type="contract_without_dm_project",
                    work_type_label="Active Contract Without Project",
                    title=f"Execution Project Missing: {dmc.contract_name}",
                    description=f"Contract is active, but no Digital Marketing project has been initialized in Project Management.",
                    urgency="high",
                    record_id=dmc.id,
                    action_url=f"/project_management/",
                    meta={
                        "contract_id": dmc.id,
                        "contract_number": dmc.contract_number,
                        "client_name": client_name,
                    }
                )
            else:
                for p in linked_projects:
                    if p.project_type == 'dm' and p.projectmember_set.filter(is_active=True).count() == 0:
                        add_item(
                            tab_key="projects",
                            work_type="dm_project_missing_team",
                            work_type_label="DM Project Without Team",
                            title=f"No Team Members on DM Project: {p.project_name}",
                            description=f"DM project '{p.project_name}' has no active team members assigned.",
                            urgency="high",
                            record_id=p.id,
                            action_url=f"/project_management/{p.id}/members/",
                            meta={
                                "project_id": p.id,
                                "project_name": p.project_name,
                                "contract_number": dmc.contract_number,
                            }
                        )

        return build_pending_dashboard_response(
            module_key="digital_marketing",
            module_label="Digital Marketing",
            tab_definitions=self.TAB_DEFINITIONS,
            tab_items=tab_items,
            tab_categories=tab_categories,
            active_tab=active_tab,
            urgency_filter=urgency_filter,
            search_query=search_query,
            limit_param=limit_param,
        )


# =============================================================================
# 3. Testing Management Pending Dashboard API View
# =============================================================================
class TestingManagementPendingDashboardAPIView(APIView):
    """
    Testing Management Module Pending Controls / Works Dashboard API.
    
    Monitors actionable pending tasks across:
      - open_bugs: Unresolved blocker, critical, major, minor, trivial bugs
      - verification: Fixed bugs awaiting QA verification and closure
      - reopens: Reopened bugs requiring developer attention
      - unassigned: Bugs without an assigned developer / fixer
      - suggestions: Pending feature suggestions and enhancements awaiting review
      - project_coverage: Active projects without bug tracking or zero test reports
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "open_bugs", "label": "Open Bugs"},
        {"key": "verification", "label": "Pending Verification"},
        {"key": "reopens", "label": "Reopened Bugs"},
        {"key": "unassigned", "label": "Unassigned Fixer"},
        {"key": "suggestions", "label": "Suggestions & Enhancements"},
        {"key": "coverage", "label": "Project Test Coverage"},
    ]

    def get(self, request):
        today = timezone.localdate()
        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()
        project_id_param = request.query_params.get("project_id")

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(tab_key, work_type, work_type_label, title, description, urgency, record_id=None, item_id=None, created_at=None, due_date=None, action_url=None, meta=None):
            if not item_id:
                item_id = f"test_{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"

            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {"label": work_type_label, "count": 0}
            tab_categories[tab_key][work_type]["count"] += 1

            tab_items[tab_key].append({
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": next((t["label"] for t in self.TAB_DEFINITIONS if t["key"] == tab_key), tab_key),
                "work_type": work_type,
                "work_type_label": work_type_label,
                "title": title,
                "description": description,
                "urgency": urgency,
                "created_at": created_at,
                "due_date": due_date,
                "action_url": action_url,
                "meta": meta or {},
            })

        bugs_qs = BugReport.objects.all().select_related('project', 'reported_by', 'fixed_by')
        if project_id_param:
            try:
                bugs_qs = bugs_qs.filter(project_id=int(project_id_param))
            except (ValueError, TypeError):
                pass

        for bug in bugs_qs:
            reporter_name = bug.reported_by.get_full_name() or bug.reported_by.username if bug.reported_by else "QA"
            fixer_name = bug.fixed_by.get_full_name() or bug.fixed_by.username if bug.fixed_by else "Unassigned"
            proj_name = bug.project.project_name if bug.project else "Project"

            # Severity-based urgency mapping
            if bug.severity in ['blocker', 'critical']:
                bug_urgency = "high"
            elif bug.severity in ['major', 'minor']:
                bug_urgency = "medium"
            else:
                bug_urgency = "low"

            # -----------------------------------------------------------------
            # Tab 1: Open Bugs
            # -----------------------------------------------------------------
            if bug.status in ['open', 'pending']:
                add_item(
                    tab_key="open_bugs",
                    work_type=f"open_{bug.severity}_bug",
                    work_type_label=f"Open {bug.get_severity_display()} Bug",
                    title=f"[{bug.bug_id}] {bug.title}",
                    description=f"{bug.get_severity_display()} bug in module '{bug.module}' of project '{proj_name}'. Status is '{bug.status}'. Reported by {reporter_name}.",
                    urgency=bug_urgency,
                    record_id=bug.id,
                    created_at=bug.created_at,
                    action_url=f"/project_management/bug-sheet/{bug.id}/",
                    meta={
                        "bug_id": bug.bug_id,
                        "title": bug.title,
                        "severity": bug.severity,
                        "status": bug.status,
                        "module": bug.module,
                        "project_id": bug.project_id,
                        "project_name": proj_name,
                        "reported_by": reporter_name,
                        "fixed_by": fixer_name,
                    }
                )

            # -----------------------------------------------------------------
            # Tab 2: Pending Verification (Status: fixed)
            # -----------------------------------------------------------------
            if bug.status == 'fixed':
                add_item(
                    tab_key="verification",
                    work_type="fixed_awaiting_verification",
                    work_type_label="Fixed Awaiting QA Verification",
                    title=f"Verify Fix: [{bug.bug_id}] {bug.title}",
                    description=f"Bug was marked fixed by {fixer_name}. Awaiting QA re-testing to close or reopen.",
                    urgency="high" if bug.severity in ['blocker', 'critical'] else "medium",
                    record_id=bug.id,
                    created_at=bug.fixed_at or bug.updated_at,
                    action_url=f"/project_management/bug-sheet/{bug.id}/status/",
                    meta={
                        "bug_id": bug.bug_id,
                        "title": bug.title,
                        "module": bug.module,
                        "fixed_by": fixer_name,
                        "project_name": proj_name,
                    }
                )

            # -----------------------------------------------------------------
            # Tab 3: Reopened Bugs
            # -----------------------------------------------------------------
            if bug.status == 'reopen':
                add_item(
                    tab_key="reopens",
                    work_type="reopened_bug",
                    work_type_label="Reopened Bug Needs Fix",
                    title=f"Reopened: [{bug.bug_id}] {bug.title}",
                    description=f"Bug was re-tested and failed verification. Requires developer immediate attention.",
                    urgency="high",
                    record_id=bug.id,
                    created_at=bug.updated_at,
                    action_url=f"/project_management/bug-sheet/{bug.id}/",
                    meta={
                        "bug_id": bug.bug_id,
                        "title": bug.title,
                        "module": bug.module,
                        "severity": bug.severity,
                        "project_name": proj_name,
                    }
                )

            # -----------------------------------------------------------------
            # Tab 4: Unassigned Fixer
            # -----------------------------------------------------------------
            if bug.status in ['open', 'pending', 'reopen'] and not bug.fixed_by:
                add_item(
                    tab_key="unassigned",
                    work_type="bug_missing_fixer",
                    work_type_label="Bug Without Assigned Fixer",
                    title=f"Unassigned Bug: [{bug.bug_id}] {bug.title}",
                    description=f"Bug has no assigned developer to investigate and fix.",
                    urgency="high" if bug.severity in ['blocker', 'critical'] else "medium",
                    record_id=bug.id,
                    created_at=bug.created_at,
                    action_url=f"/project_management/bug-sheet/{bug.id}/",
                    meta={
                        "bug_id": bug.bug_id,
                        "title": bug.title,
                        "severity": bug.severity,
                        "project_name": proj_name,
                    }
                )

            # -----------------------------------------------------------------
            # Tab 5: Suggestions & Enhancements
            # -----------------------------------------------------------------
            if bug.status == 'suggestion' or bug.severity == 'enhancement':
                add_item(
                    tab_key="suggestions",
                    work_type="pending_suggestion_review",
                    work_type_label="Feature Suggestion Review",
                    title=f"Suggestion: {bug.title}",
                    description=f"Feature/enhancement suggested for module '{bug.module}' in project '{proj_name}'. Awaiting product review.",
                    urgency="low",
                    record_id=bug.id,
                    created_at=bug.created_at,
                    action_url=f"/project_management/bug-sheet/{bug.id}/",
                    meta={
                        "bug_id": bug.bug_id,
                        "title": bug.title,
                        "module": bug.module,
                        "project_name": proj_name,
                    }
                )

        # ---------------------------------------------------------------------
        # Tab 6: Project Coverage Pending Controls
        # ---------------------------------------------------------------------
        active_projects = ProjectManagement.objects.filter(
            status__in=['not_started', 'in_progress']
        ).annotate(bug_count=Count('bug_reports'))

        for p in active_projects:
            if p.bug_count == 0:
                add_item(
                    tab_key="coverage",
                    work_type="project_zero_bugs_logged",
                    work_type_label="Project Without Bug Reports",
                    title=f"No QA Testing Logged: {p.project_name}",
                    description=f"Active project '{p.project_name}' has 0 bug reports or testing sheets submitted by QA.",
                    urgency="medium",
                    record_id=p.id,
                    action_url=f"/project_management/bug-sheet/",
                    meta={
                        "project_id": p.id,
                        "project_name": p.project_name,
                        "status": p.status,
                        "project_type": p.project_type,
                    }
                )

        return build_pending_dashboard_response(
            module_key="testing_management",
            module_label="Testing Management",
            tab_definitions=self.TAB_DEFINITIONS,
            tab_items=tab_items,
            tab_categories=tab_categories,
            active_tab=active_tab,
            urgency_filter=urgency_filter,
            search_query=search_query,
            limit_param=limit_param,
        )
