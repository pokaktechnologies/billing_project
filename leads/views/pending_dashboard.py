from datetime import date, timedelta, datetime, time
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from accounts.models import CustomUser, StaffProfile, SalesPerson
from leads.models import (
    Lead,
    FollowUp,
    Meeting,
    Reminders,
    MarketingReport,
    CommunicationLog,
    CallDetail,
    Location,
    Source,
    Category,
)
from leads.serializers.pending_dashboard import (
    MarketingPendingDashboardSerializer,
    LeadManagementPendingDashboardSerializer,
)


def get_user_salesperson(user):
    """
    Attempts to identify the SalesPerson record for the authenticated user.
    Returns SalesPerson instance or None.
    """
    if not user or not user.is_authenticated:
        return None

    # 1. via assigned_staff on StaffProfile
    try:
        staff = StaffProfile.objects.filter(user=user).first()
        if staff:
            sp = SalesPerson.objects.filter(assigned_staff=staff).first()
            if sp:
                return sp
    except Exception:
        pass

    # 2. via matching email address
    try:
        if getattr(user, 'email', None):
            sp = SalesPerson.objects.filter(email=user.email).first()
            if sp:
                return sp
    except Exception:
        pass

    return None


class MarketingPendingDashboardAPIView(APIView):
    """
    Marketing Module (Staff & Admin) Pending Works Dashboard API.
    
    Returns all actionable pending tasks across Marketing submodules:
      - daily_activity: Missing daily marketing reports, today's overdue activities
      - leads: Uncontacted new leads, follow-up status without schedule, stalled hot prospects, idle in-progress leads
      - follow_ups: Overdue follow-ups, pending follow-ups today, completed follow-ups missing outcome notes
      - meetings: Overdue meetings, today's scheduled meetings, meetings missing venue/link
      - reminders: Overdue reminders, reminders due today
      - communication: Calls requiring follow-up, open/initiated communications awaiting summary
      - marketing_data: Locations without leads, sources without categories, categories without leads
    
    Query Parameters:
      - tab: Filter by specific tab ('daily_activity', 'leads', 'follow_ups', 'meetings', 'reminders', 'communication', 'marketing_data', or 'all'). Default: 'all'.
      - urgency: Filter by urgency level ('high', 'medium', 'low').
      - search: Search text across item titles, descriptions, lead names, and metadata.
      - limit: Maximum items to return in the items array (default: 100).
      - salesperson: (Admin only) Filter pending items by a specific SalesPerson ID.
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "daily_activity", "label": "Daily Activity"},
        {"key": "leads", "label": "Leads"},
        {"key": "follow_ups", "label": "Follow-ups"},
        {"key": "meetings", "label": "Meetings"},
        {"key": "reminders", "label": "Reminders"},
        {"key": "communication", "label": "Communication"},
        {"key": "marketing_data", "label": "Marketing Data"},
    ]

    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()
        current_time = timezone.localtime().time()

        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()

        # ---------------------------------------------------------------------
        # 1. Resolve Staff / SalesPerson Scope
        # ---------------------------------------------------------------------
        salesperson = get_user_salesperson(request.user)
        salesperson_filter_id = request.query_params.get("salesperson")

        # Admin override if explicitly passed
        if (request.user.is_superuser or request.user.is_staff) and salesperson_filter_id:
            try:
                target_sp = SalesPerson.objects.filter(pk=int(salesperson_filter_id)).first()
                if target_sp:
                    salesperson = target_sp
            except (ValueError, TypeError):
                pass

        salesperson_info = None
        if salesperson:
            full_name = f"{salesperson.first_name} {salesperson.last_name or ''}".strip()
            salesperson_info = {
                "id": salesperson.id,
                "name": full_name or salesperson.email,
                "email": salesperson.email,
                "phone": salesperson.phone or salesperson.mobile
            }

        # ---------------------------------------------------------------------
        # 2. Scoped QuerySets
        # ---------------------------------------------------------------------
        leads_qs = Lead.objects.all()
        followups_qs = FollowUp.objects.select_related('lead')
        meetings_qs = Meeting.objects.select_related('lead')
        reminders_qs = Reminders.objects.select_related('lead')
        communications_qs = CommunicationLog.objects.select_related('lead')

        if salesperson:
            leads_qs = leads_qs.filter(salesperson=salesperson)
            followups_qs = followups_qs.filter(lead__salesperson=salesperson)
            meetings_qs = meetings_qs.filter(lead__salesperson=salesperson)
            reminders_qs = reminders_qs.filter(lead__salesperson=salesperson)
            communications_qs = communications_qs.filter(lead__salesperson=salesperson)

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(tab_key, work_type, work_type_label, title, description, urgency, record_id=None, item_id=None, created_at=None, due_date=None, action_url=None, meta=None):
            if not item_id:
                item_id = f"{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"

            # Update category counter
            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {
                    "key": work_type,
                    "label": work_type_label,
                    "count": 0
                }
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

        # =====================================================================
        # TAB 1: DAILY ACTIVITY & REPORTS
        # =====================================================================
        # A. Missing Daily Marketing Report for today
        if salesperson:
            has_report_today = MarketingReport.objects.filter(salesperson=salesperson, date=today).exists()
            if not has_report_today:
                add_item(
                    tab_key="daily_activity",
                    work_type="missing_daily_report",
                    work_type_label="Missing Daily Marketing Report",
                    title="Daily Marketing Report Pending Submission",
                    description=f"Your marketing activity report for today ({today}) has not been submitted yet. Please log your daily calls and leads summary.",
                    urgency="high",
                    due_date=today,
                    action_url="/leads/marketing-report/",
                    meta={"salesperson": salesperson_info}
                )
        else:
            # For admin overview: check active salespersons missing today's report
            all_sp = SalesPerson.objects.all()
            for sp in all_sp[:25]:
                if not MarketingReport.objects.filter(salesperson=sp, date=today).exists():
                    sp_name = f"{sp.first_name} {sp.last_name or ''}".strip()
                    add_item(
                        tab_key="daily_activity",
                        work_type="missing_daily_report",
                        work_type_label="Missing Daily Marketing Report",
                        title=f"Missing Daily Report: {sp_name}",
                        description=f"Salesperson {sp_name} ({sp.email}) has not submitted today's marketing activity report.",
                        urgency="medium",
                        record_id=sp.id,
                        due_date=today,
                        action_url=f"/leads/marketing-report/?salesperson={sp.id}",
                        meta={"salesperson_id": sp.id, "salesperson_name": sp_name}
                    )

        # B. Overdue Activities Today (Follow-ups & Meetings past scheduled time today)
        today_overdue_fu = followups_qs.filter(status='new', date=today, time__lt=current_time)
        for fu in today_overdue_fu[:20]:
            add_item(
                tab_key="daily_activity",
                work_type="overdue_activity_today",
                work_type_label="Overdue Activity Today",
                title=f"Overdue Call/Follow-up: {fu.title} with {fu.lead.name}",
                description=f"Follow-up with {fu.lead.name} was scheduled for today at {fu.time.strftime('%I:%M %p')}. Action is now overdue.",
                urgency="high",
                record_id=fu.id,
                due_date=today,
                action_url=f"/leads/staff/followups/{fu.id}/",
                meta={"lead_id": fu.lead.id, "lead_name": fu.lead.name, "phone": fu.lead.phone, "scheduled_time": str(fu.time)}
            )

        # =====================================================================
        # TAB 2: LEADS
        # =====================================================================
        # A. Uncontacted New Leads (> 24 hours old with 0 calls/follow-ups)
        one_day_ago = now - timedelta(hours=24)
        uncontacted_leads = leads_qs.filter(
            lead_status='new',
            created_at__lte=one_day_ago
        ).annotate(
            fu_count=Count('follow_ups'),
            mt_count=Count('meetings'),
            comm_count=Count('communications')
        ).filter(fu_count=0, mt_count=0, comm_count=0)[:35]

        for lead in uncontacted_leads:
            age_days = (now - lead.created_at).days
            add_item(
                tab_key="leads",
                work_type="uncontacted_new_lead",
                work_type_label="Uncontacted New Lead",
                title=f"New Lead Uncontacted: {lead.name}",
                description=f"Lead was assigned {age_days} day(s) ago ({lead.created_at.strftime('%Y-%m-%d')}) with status 'New', but no call, follow-up, or meeting has been logged.",
                urgency="high",
                record_id=lead.id,
                created_at=lead.created_at,
                action_url=f"/leads/staff/{lead.id}/",
                meta={"lead_number": lead.lead_number, "phone": lead.phone, "email": lead.email, "category": lead.lead_category}
            )

        # B. Lead Status Marked as 'follow_up' But No Follow-up Scheduled
        leads_without_fu = leads_qs.filter(
            lead_status='follow_up'
        ).exclude(
            follow_ups__status='new'
        ).exclude(
            meetings__status='scheduled'
        ).distinct()[:25]

        for lead in leads_without_fu:
            add_item(
                tab_key="leads",
                work_type="followup_status_without_schedule",
                work_type_label="Follow-up Missing Schedule",
                title=f"Follow-up Status Without Schedule: {lead.name}",
                description=f"Lead status is marked as 'Follow Up', but currently has no open or future follow-up or meeting scheduled.",
                urgency="high",
                record_id=lead.id,
                action_url=f"/leads/staff/{lead.id}/followup/",
                meta={"lead_number": lead.lead_number, "phone": lead.phone, "lead_status": lead.lead_status}
            )

        # C. Hot / Warm Prospects Stalled (No follow-up in 5+ days)
        stalled_prospects = leads_qs.filter(
            priority_status__in=['hot', 'warm']
        ).exclude(
            lead_status__in=['converted', 'lost']
        ).filter(
            Q(follow_ups__date__lt=today - timedelta(days=5)) | Q(follow_ups__isnull=True)
        ).distinct()[:20]

        for lead in stalled_prospects:
            p_label = "Hot" if lead.priority_status == 'hot' else "Warm"
            add_item(
                tab_key="leads",
                work_type="hot_prospect_stalled",
                work_type_label="Stalled Prospect",
                title=f"Stalled {p_label} Prospect: {lead.name}",
                description=f"High-priority ({p_label}) lead has not had any follow-up or contact activity in the last 5+ days.",
                urgency="high" if lead.priority_status == 'hot' else "medium",
                record_id=lead.id,
                action_url=f"/leads/staff/{lead.id}/",
                meta={"priority": lead.priority_status, "phone": lead.phone, "lead_number": lead.lead_number}
            )

        # D. Converted Lead Awaiting Admission / Registration Conversion
        converted_leads = leads_qs.filter(
            lead_status__in=['converted', 'registration']
        )[:20]
        for lead in converted_leads:
            add_item(
                tab_key="leads",
                work_type="converted_lead_admission_pending",
                work_type_label="Converted Lead Admission Pending",
                title=f"Converted Lead Pending Student Admission: {lead.name}",
                description=f"Lead is marked '{lead.get_lead_status_display()}', verify student profile registration and enrollment conversion in Academy module.",
                urgency="medium",
                record_id=lead.id,
                action_url=f"/leads/staff/{lead.id}/",
                meta={"lead_number": lead.lead_number, "phone": lead.phone, "course": lead.course.title if lead.course else None}
            )

        # =====================================================================
        # TAB 3: FOLLOW-UPS
        # =====================================================================
        # A. Overdue Follow-ups (date < today and status='new')
        overdue_fus = followups_qs.filter(
            status='new',
            date__lt=today
        ).order_by('date', 'time')[:35]

        for fu in overdue_fus:
            overdue_days = (today - fu.date).days
            add_item(
                tab_key="follow_ups",
                work_type="overdue_followup",
                work_type_label="Overdue Follow-up",
                title=f"Overdue Follow-up: {fu.title} ({fu.lead.name})",
                description=f"Scheduled for {fu.date} at {fu.time.strftime('%I:%M %p')} (overdue by {overdue_days} day(s)). Lead: {fu.lead.name} ({fu.lead.phone or 'No phone'}).",
                urgency="high",
                record_id=fu.id,
                due_date=fu.date,
                action_url=f"/leads/staff/followups/{fu.id}/",
                meta={"lead_id": fu.lead.id, "lead_name": fu.lead.name, "phone": fu.lead.phone, "overdue_days": overdue_days}
            )

        # B. Pending Follow-ups Scheduled for Today
        today_fus = followups_qs.filter(
            status='new',
            date=today
        ).order_by('time')[:30]

        for fu in today_fus:
            is_past = fu.time < current_time
            add_item(
                tab_key="follow_ups",
                work_type="pending_followup_today",
                work_type_label="Today's Pending Follow-up",
                title=f"Follow-up Due Today: {fu.title} ({fu.lead.name})",
                description=f"Scheduled for today at {fu.time.strftime('%I:%M %p')}. Lead: {fu.lead.name} ({fu.lead.phone or 'No phone'}).",
                urgency="high" if is_past else "medium",
                record_id=fu.id,
                due_date=today,
                action_url=f"/leads/staff/followups/{fu.id}/",
                meta={"lead_id": fu.lead.id, "lead_name": fu.lead.name, "phone": fu.lead.phone, "scheduled_time": str(fu.time)}
            )

        # C. Completed Follow-ups Missing Outcome Notes
        missing_notes_fu = followups_qs.filter(
            status='completed'
        ).filter(
            Q(notes__isnull=True) | Q(notes__exact='')
        ).filter(
            Q(additional_notes__isnull=True) | Q(additional_notes__exact='')
        )[:20]

        for fu in missing_notes_fu:
            add_item(
                tab_key="follow_ups",
                work_type="followup_missing_notes",
                work_type_label="Follow-up Missing Notes",
                title=f"Completed Follow-up Missing Notes: {fu.title}",
                description=f"Follow-up for {fu.lead.name} was marked completed without logging any discussion remarks or outcome notes.",
                urgency="low",
                record_id=fu.id,
                action_url=f"/leads/staff/followups/{fu.id}/",
                meta={"lead_id": fu.lead.id, "lead_name": fu.lead.name}
            )

        # =====================================================================
        # TAB 4: MEETINGS
        # =====================================================================
        # A. Overdue Meetings (date < today and status='scheduled')
        overdue_meetings = meetings_qs.filter(
            status='scheduled',
            date__lt=today
        ).order_by('date')[:25]

        for mt in overdue_meetings:
            overdue_days = (today - mt.date).days
            add_item(
                tab_key="meetings",
                work_type="overdue_meeting",
                work_type_label="Overdue Meeting",
                title=f"Overdue Meeting: {mt.title or 'Meeting'} with {mt.lead.name}",
                description=f"Meeting scheduled on {mt.date} ({overdue_days} day(s) ago) has not been marked as completed or cancelled.",
                urgency="high",
                record_id=mt.id,
                due_date=mt.date,
                action_url=f"/leads/staff/meeting/{mt.id}/",
                meta={"lead_id": mt.lead.id, "lead_name": mt.lead.name, "phone": mt.lead.phone, "meeting_type": mt.meeting_type}
            )

        # B. Meetings Scheduled for Today
        today_meetings = meetings_qs.filter(
            status='scheduled',
            date=today
        ).order_by('time')[:20]

        for mt in today_meetings:
            add_item(
                tab_key="meetings",
                work_type="meeting_scheduled_today",
                work_type_label="Meeting Scheduled Today",
                title=f"Meeting Today: {mt.title or 'Meeting'} with {mt.lead.name}",
                description=f"Type: {mt.get_meeting_type_display()} at {mt.time.strftime('%I:%M %p')}. Place: {mt.meeting_place or 'Not specified'}.",
                urgency="high",
                record_id=mt.id,
                due_date=today,
                action_url=f"/leads/staff/meeting/{mt.id}/",
                meta={"lead_id": mt.lead.id, "lead_name": mt.lead.name, "meeting_type": mt.meeting_type, "place": mt.meeting_place}
            )

        # C. Scheduled Meetings Missing Location / Link
        missing_place_meetings = meetings_qs.filter(
            status='scheduled',
            date__gte=today
        ).filter(
            Q(meeting_place__isnull=True) | Q(meeting_place__exact='')
        )[:20]

        for mt in missing_place_meetings:
            add_item(
                tab_key="meetings",
                work_type="meeting_missing_place",
                work_type_label="Meeting Missing Venue/Link",
                title=f"Meeting Venue / Link Missing: {mt.title or 'Meeting'}",
                description=f"Scheduled meeting with {mt.lead.name} on {mt.date} does not have an address or video meeting URL configured.",
                urgency="medium",
                record_id=mt.id,
                due_date=mt.date,
                action_url=f"/leads/staff/meeting/{mt.id}/",
                meta={"lead_id": mt.lead.id, "lead_name": mt.lead.name}
            )

        # =====================================================================
        # TAB 5: REMINDERS
        # =====================================================================
        # A. Overdue Reminders
        overdue_reminders = reminders_qs.filter(
            status='scheduled',
            date__lt=today
        ).order_by('date')[:25]

        for rem in overdue_reminders:
            overdue_days = (today - rem.date).days
            add_item(
                tab_key="reminders",
                work_type="overdue_reminder",
                work_type_label="Overdue Reminder",
                title=f"Overdue Reminder: {rem.title} ({rem.lead.name})",
                description=f"Reminder ({rem.type.upper()}) was due on {rem.date} ({overdue_days} day(s) ago). Lead: {rem.lead.name}.",
                urgency="high",
                record_id=rem.id,
                due_date=rem.date,
                action_url=f"/leads/staff/reminders/{rem.id}/",
                meta={"lead_id": rem.lead.id, "lead_name": rem.lead.name, "type": rem.type}
            )

        # B. Reminders Due Today
        today_reminders = reminders_qs.filter(
            status='scheduled',
            date=today
        ).order_by('time')[:20]

        for rem in today_reminders:
            add_item(
                tab_key="reminders",
                work_type="reminder_due_today",
                work_type_label="Reminder Due Today",
                title=f"Reminder Due Today: {rem.title} ({rem.lead.name})",
                description=f"Reminder ({rem.type.upper()}) scheduled for {rem.time.strftime('%I:%M %p')} today for {rem.lead.name}.",
                urgency="medium",
                record_id=rem.id,
                due_date=today,
                action_url=f"/leads/staff/reminders/{rem.id}/",
                meta={"lead_id": rem.lead.id, "lead_name": rem.lead.name, "type": rem.type, "time": str(rem.time)}
            )

        # =====================================================================
        # TAB 6: COMMUNICATION
        # =====================================================================
        # A. Calls Marked 'Follow-up Required' But No Follow-up Created
        call_details = CallDetail.objects.filter(
            follow_up_required=True
        ).select_related('communication__lead')

        if salesperson:
            call_details = call_details.filter(communication__lead__salesperson=salesperson)

        pending_call_fu = call_details.filter(
            Q(communication__lead__follow_ups__status='new') | Q(follow_up_date__isnull=True)
        ).distinct()[:20]

        for cd in pending_call_fu:
            lead = cd.communication.lead
            add_item(
                tab_key="communication",
                work_type="call_followup_pending",
                work_type_label="Call Follow-up Pending",
                title=f"Call Logged Follow-up Required: {lead.name}",
                description=f"Call to {cd.phone_number} flagged follow-up required, but no subsequent follow-up activity has been closed.",
                urgency="high",
                record_id=cd.communication.id,
                action_url=f"/leads/staff/{lead.id}/followup/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "phone": cd.phone_number, "call_status": cd.call_status}
            )

        # B. Initiated Communications Awaiting Outcome Summary
        two_hours_ago = now - timedelta(hours=2)
        open_comms = communications_qs.filter(
            status='initiated',
            created_at__lte=two_hours_ago
        )[:20]

        for comm in open_comms:
            add_item(
                tab_key="communication",
                work_type="communication_summary_pending",
                work_type_label="Communication Summary Pending",
                title=f"Open {comm.communication_type.title()} Summary Pending: {comm.lead.name}",
                description=f"Communication was initiated on {comm.created_at.strftime('%Y-%m-%d %I:%M %p')}, but call summary/outcome was never submitted.",
                urgency="medium",
                record_id=comm.id,
                action_url=f"/leads/call-summary/{comm.id}/",
                meta={"lead_id": comm.lead.id, "lead_name": comm.lead.name, "type": comm.communication_type}
            )

        # =====================================================================
        # TAB 7: MARKETING DATA
        # =====================================================================
        # A. Locations with Zero Leads
        unused_locations = Location.objects.annotate(
            lead_count=Count('lead')
        ).filter(lead_count=0)[:15]

        for loc in unused_locations:
            add_item(
                tab_key="marketing_data",
                work_type="location_without_leads",
                work_type_label="Unused Lead Location",
                title=f"Location With Zero Leads: {loc.name}",
                description=f"Location '{loc.name}' is configured in marketing data, but has no recorded leads.",
                urgency="low",
                record_id=loc.id,
                action_url=f"/leads/location/{loc.id}/",
                meta={"location_name": loc.name}
            )

        # B. Sources with Zero Sub-Categories
        sources_without_cats = Source.objects.annotate(
            cat_count=Count('categories')
        ).filter(cat_count=0)[:15]

        for src in sources_without_cats:
            add_item(
                tab_key="marketing_data",
                work_type="source_without_categories",
                work_type_label="Source Without Categories",
                title=f"Source Without Sub-Categories: {src.name}",
                description=f"Marketing lead source '{src.name}' has no sub-categories configured for attribution.",
                urgency="low",
                record_id=src.id,
                action_url=f"/leads/source/{src.id}/",
                meta={"source_name": src.name}
            )

        # C. Categories with Zero Recorded Reports
        categories_without_reports = Category.objects.annotate(
            report_count=Count('marketingreport')
        ).filter(report_count=0)[:15]

        for cat in categories_without_reports:
            add_item(
                tab_key="marketing_data",
                work_type="category_without_reports",
                work_type_label="Category Without Activity",
                title=f"Category With Zero Activity: {cat.name}",
                description=f"Category '{cat.name}' under source '{cat.source.name}' has no marketing reports or activity logged.",
                urgency="low",
                record_id=cat.id,
                action_url=f"/leads/category/{cat.id}/",
                meta={"category_name": cat.name, "source_name": cat.source.name}
            )

        # =====================================================================
        # 3. Compile Tabs, Counters, and Filters
        # =====================================================================
        tab_counts = {t["key"]: len(tab_items[t["key"]]) for t in self.TAB_DEFINITIONS}
        total_pending_count = sum(tab_counts.values())

        tabs_data = []
        for tab_def in self.TAB_DEFINITIONS:
            k = tab_def["key"]
            tabs_data.append({
                "key": k,
                "label": tab_def["label"],
                "count": tab_counts[k],
                "categories": list(tab_categories[k].values())
            })

        # Filter items based on active tab
        if active_tab == "all":
            all_items = []
            for t in self.TAB_DEFINITIONS:
                all_items.extend(tab_items[t["key"]])
            selected_items = all_items
        elif active_tab in tab_items:
            selected_items = tab_items[active_tab]
        else:
            selected_items = []

        # Filter by urgency
        if urgency_filter in ["high", "medium", "low"]:
            selected_items = [item for item in selected_items if item["urgency"] == urgency_filter]

        # Filter by search
        if search_query:
            selected_items = [
                item for item in selected_items
                if search_query in item["title"].lower()
                or search_query in item["description"].lower()
                or search_query in str(item.get("meta", {})).lower()
            ]

        # Apply limit
        try:
            limit = int(limit_param)
            if limit > 0:
                selected_items = selected_items[:limit]
        except (ValueError, TypeError):
            selected_items = selected_items[:100]

        response_data = {
            "module": "marketing",
            "module_label": "Marketing",
            "salesperson_info": salesperson_info,
            "total_pending_count": total_pending_count,
            "tab_counts": tab_counts,
            "tabs": tabs_data,
            "active_tab": active_tab,
            "items_count": len(selected_items),
            "items": selected_items,
        }

        serializer = MarketingPendingDashboardSerializer(response_data)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


class LeadManagementPendingDashboardAPIView(APIView):
    """
    Lead Management (Admin & Manager) Pending Works Dashboard API.

    Returns all actionable pending tasks across Lead Management submodules:
      - unassigned: Missing salesperson, missing lead source, missing location
      - uncontacted: New leads uncontacted >24h, idle assigned leads (7+ days stalled)
      - follow_ups: Follow-up status without active schedule, overdue follow-ups
      - priority: Contacted leads missing priority status (hot/warm/cold), hot prospects neglected (3+ days)
      - data_quality: Missing phone numbers, intern leads without target course, client leads without requirements, duplicate phones
      - conversion: Converted leads pending Academy registration, RNR/busy leads due for re-engagement (5+ days)

    Query Parameters:
      - tab: Filter by specific tab ('unassigned', 'uncontacted', 'follow_ups', 'priority', 'data_quality', 'conversion', or 'all'). Default: 'all'.
      - urgency: Filter by urgency level ('high', 'medium', 'low').
      - search: Search text across item titles, descriptions, lead names, phone, email, and metadata.
      - limit: Maximum items to return in the items array (default: 100).
      - salesperson: Filter pending items by a specific SalesPerson ID.
      - lead_category: Filter by lead category ('client', 'intern', 'other').
    """
    permission_classes = [IsAuthenticated]

    TAB_DEFINITIONS = [
        {"key": "unassigned", "label": "Unassigned Leads"},
        {"key": "uncontacted", "label": "Uncontacted Leads"},
        {"key": "follow_ups", "label": "Follow-ups"},
        {"key": "priority", "label": "Priority & Status"},
        {"key": "data_quality", "label": "Data Quality"},
        {"key": "conversion", "label": "Conversions & RNR"},
    ]

    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()

        active_tab = request.query_params.get("tab", "all").strip().lower()
        urgency_filter = request.query_params.get("urgency", "").strip().lower()
        search_query = request.query_params.get("search", "").strip().lower()
        limit_param = request.query_params.get("limit", "100").strip()
        salesperson_filter_id = request.query_params.get("salesperson")
        category_filter = request.query_params.get("lead_category")

        # ---------------------------------------------------------------------
        # 1. Scoping QuerySet
        # ---------------------------------------------------------------------
        leads_qs = Lead.objects.all().select_related(
            "salesperson", "lead_source", "location", "course", "CustomUser"
        )

        salesperson_info = None
        if salesperson_filter_id:
            try:
                sp = SalesPerson.objects.filter(pk=int(salesperson_filter_id)).first()
                if sp:
                    leads_qs = leads_qs.filter(salesperson=sp)
                    full_name = f"{sp.first_name} {sp.last_name or ''}".strip()
                    salesperson_info = {
                        "id": sp.id,
                        "name": full_name or sp.email,
                        "email": sp.email,
                        "phone": sp.phone or sp.mobile,
                    }
            except (ValueError, TypeError):
                pass

        if category_filter:
            leads_qs = leads_qs.filter(lead_category=category_filter)

        tab_items = {tab["key"]: [] for tab in self.TAB_DEFINITIONS}
        tab_categories = {tab["key"]: {} for tab in self.TAB_DEFINITIONS}

        def add_item(tab_key, work_type, work_type_label, title, description, urgency, record_id=None, item_id=None, created_at=None, due_date=None, action_url=None, meta=None):
            if not item_id:
                item_id = f"leadmgmt_{tab_key}_{work_type}_{record_id or len(tab_items[tab_key]) + 1}"

            if work_type not in tab_categories[tab_key]:
                tab_categories[tab_key][work_type] = {
                    "key": work_type,
                    "label": work_type_label,
                    "count": 0
                }
            tab_categories[tab_key][work_type]["count"] += 1

            tab_items[tab_key].append({
                "id": item_id,
                "record_id": record_id,
                "tab": tab_key,
                "tab_label": next(t["label"] for t in self.TAB_DEFINITIONS if t["key"] == tab_key),
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

        # ---------------------------------------------------------------------
        # TAB 1: UNASSIGNED LEADS
        # ---------------------------------------------------------------------
        # A. Missing Salesperson (HIGH)
        unassigned_salesperson_leads = leads_qs.filter(salesperson__isnull=True).order_by("-created_at")[:50]
        for lead in unassigned_salesperson_leads:
            add_item(
                tab_key="unassigned",
                work_type="missing_salesperson",
                work_type_label="Missing Salesperson",
                title=f"Unassigned Lead: {lead.name} ({lead.lead_number or 'No Number'})",
                description=f"Lead was received on {lead.created_at.strftime('%Y-%m-%d') if lead.created_at else 'N/A'} but has no assigned salesperson.",
                urgency="high",
                record_id=lead.id,
                created_at=lead.created_at,
                action_url="/leads/admin/assign/",
                meta={
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "lead_number": lead.lead_number,
                    "phone": lead.phone,
                    "email": lead.email,
                    "lead_category": lead.lead_category,
                    "source": lead.lead_source.name if lead.lead_source else None,
                    "course": lead.course.title if lead.course else None,
                }
            )

        # B. Missing Source (MEDIUM)
        missing_source_leads = leads_qs.filter(lead_source__isnull=True).order_by("-created_at")[:25]
        for lead in missing_source_leads:
            add_item(
                tab_key="unassigned",
                work_type="unassigned_source",
                work_type_label="Missing Lead Source",
                title=f"Missing Source: {lead.name}",
                description=f"Lead # {lead.lead_number or lead.id} is missing an acquisition source attribution.",
                urgency="medium",
                record_id=lead.id,
                created_at=lead.created_at,
                action_url=f"/leads/admin/{lead.id}/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "phone": lead.phone}
            )

        # C. Missing Location (LOW)
        missing_location_leads = leads_qs.filter(location__isnull=True).order_by("-created_at")[:25]
        for lead in missing_location_leads:
            add_item(
                tab_key="unassigned",
                work_type="unassigned_location",
                work_type_label="Missing Location",
                title=f"Missing Location: {lead.name}",
                description=f"Lead # {lead.lead_number or lead.id} has no branch or marketing location assigned.",
                urgency="low",
                record_id=lead.id,
                created_at=lead.created_at,
                action_url=f"/leads/admin/{lead.id}/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "phone": lead.phone}
            )

        # ---------------------------------------------------------------------
        # TAB 2: UNCONTACTED & STALLED LEADS
        # ---------------------------------------------------------------------
        # A. New leads uncontacted >24h (HIGH)
        uncontacted_cutoff = now - timedelta(hours=24)
        new_uncontacted = leads_qs.filter(
            lead_status__in=["new", "created"],
            created_at__lte=uncontacted_cutoff
        ).annotate(
            fu_count=Count("follow_ups", distinct=True),
            mt_count=Count("meetings", distinct=True),
            comm_count=Count("communications", distinct=True)
        ).filter(
            fu_count=0,
            mt_count=0,
            comm_count=0
        ).order_by("created_at")[:30]

        for lead in new_uncontacted:
            hours_elapsed = int((now - lead.created_at).total_seconds() // 3600) if lead.created_at else 24
            add_item(
                tab_key="uncontacted",
                work_type="new_lead_uncontacted",
                work_type_label="New Lead Uncontacted >24h",
                title=f"Uncontacted Lead ({hours_elapsed}h ago): {lead.name}",
                description=f"Lead was received {hours_elapsed} hours ago and no calls, meetings, or follow-ups have been logged.",
                urgency="high",
                record_id=lead.id,
                created_at=lead.created_at,
                action_url=f"/leads/admin/{lead.id}/",
                meta={
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "phone": lead.phone,
                    "salesperson": lead.salesperson.first_name if lead.salesperson else "Unassigned",
                    "hours_elapsed": hours_elapsed
                }
            )

        # B. Idle Stalled Leads (7+ days no touchpoint) (MEDIUM)
        idle_cutoff_dt = now - timedelta(days=7)
        stalled_leads = leads_qs.filter(
            salesperson__isnull=False
        ).exclude(
            lead_status__in=["converted", "lost"]
        ).annotate(
            active_fu=Count("follow_ups", filter=Q(follow_ups__date__gte=today)),
            active_mt=Count("meetings", filter=Q(meetings__date__gte=today))
        ).filter(
            active_fu=0,
            active_mt=0,
            created_at__lte=idle_cutoff_dt
        ).order_by("-created_at")[:25]

        for lead in stalled_leads:
            add_item(
                tab_key="uncontacted",
                work_type="idle_lead_stalled",
                work_type_label="Stalled Lead (7+ Days Idle)",
                title=f"Stalled Assigned Lead: {lead.name}",
                description=f"Assigned to {lead.salesperson.first_name if lead.salesperson else 'staff'}, but has had zero scheduled activity for over 7 days.",
                urgency="medium",
                record_id=lead.id,
                created_at=lead.created_at,
                action_url=f"/leads/admin/{lead.id}/",
                meta={
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "salesperson": lead.salesperson.first_name if lead.salesperson else None
                }
            )

        # ---------------------------------------------------------------------
        # TAB 3: FOLLOW-UPS
        # ---------------------------------------------------------------------
        # A. Lead marked 'follow_up' with no active schedule (HIGH)
        followup_status_leads = leads_qs.filter(
            lead_status="follow_up"
        ).annotate(
            active_future_fu=Count("follow_ups", filter=Q(follow_ups__status="new", follow_ups__date__gte=today))
        ).filter(
            active_future_fu=0
        )[:30]

        for lead in followup_status_leads:
            add_item(
                tab_key="follow_ups",
                work_type="followup_status_without_schedule",
                work_type_label="Follow-up Status Without Schedule",
                title=f"Follow-up Status Without Future Schedule: {lead.name}",
                description="Lead status is marked 'Follow Up', but there is no upcoming pending follow-up scheduled.",
                urgency="high",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "phone": lead.phone,
                    "salesperson": lead.salesperson.first_name if lead.salesperson else "Unassigned"
                }
            )

        # B. Overdue Follow-ups (HIGH)
        overdue_fu = FollowUp.objects.filter(
            status="new",
            date__lt=today
        ).select_related("lead", "lead__salesperson").order_by("date")[:30]

        if salesperson_filter_id:
            overdue_fu = overdue_fu.filter(lead__salesperson_id=salesperson_filter_id)

        for fu in overdue_fu:
            lead = fu.lead
            days_overdue = (today - fu.date).days
            add_item(
                tab_key="follow_ups",
                work_type="overdue_followup",
                work_type_label="Overdue Follow-up",
                title=f"Overdue Follow-up ({days_overdue}d late): {fu.title} ({lead.name})",
                description=f"Follow-up was scheduled for {fu.date} at {fu.time} ({days_overdue} days ago) and is still pending completion.",
                urgency="high",
                record_id=fu.id,
                due_date=fu.date,
                action_url=f"/leads/staff/followups/{fu.id}/",
                meta={
                    "followup_id": fu.id,
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "phone": lead.phone,
                    "salesperson": lead.salesperson.first_name if lead.salesperson else None,
                    "days_overdue": days_overdue
                }
            )

        # ---------------------------------------------------------------------
        # TAB 4: PRIORITY & STATUS
        # ---------------------------------------------------------------------
        # A. Contacted Leads Missing Priority (MEDIUM)
        missing_priority_leads = leads_qs.filter(
            priority_status__isnull=True
        ).filter(
            Q(lead_contact=True) | ~Q(lead_status__in=["new", "created", "lost", "converted"])
        ).order_by("-created_at")[:25]

        for lead in missing_priority_leads:
            add_item(
                tab_key="priority",
                work_type="missing_priority",
                work_type_label="Missing Priority",
                title=f"Priority Not Set: {lead.name}",
                description=f"Lead has been contacted (Status: {lead.get_lead_status_display()}), but priority (Hot/Warm/Cold) has not been categorized.",
                urgency="medium",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "phone": lead.phone, "status": lead.lead_status}
            )

        # B. Hot Prospects Neglected (HIGH)
        neglected_cutoff = today - timedelta(days=3)
        hot_neglected = leads_qs.filter(
            priority_status="hot"
        ).exclude(
            lead_status__in=["converted", "lost"]
        ).annotate(
            recent_fu=Count("follow_ups", filter=Q(follow_ups__date__gte=neglected_cutoff))
        ).filter(
            recent_fu=0
        )[:20]

        for lead in hot_neglected:
            add_item(
                tab_key="priority",
                work_type="hot_lead_neglected",
                work_type_label="Hot Prospect Neglected",
                title=f"Hot Prospect Neglected (3+ days): {lead.name}",
                description="High priority 'Hot' lead has had no touchpoint or follow-up recorded in the last 3 days.",
                urgency="high",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "phone": lead.phone,
                    "salesperson": lead.salesperson.first_name if lead.salesperson else "Unassigned"
                }
            )

        # ---------------------------------------------------------------------
        # TAB 5: DATA QUALITY & DUPLICATES
        # ---------------------------------------------------------------------
        # A. Missing Phone (HIGH)
        missing_phone_leads = leads_qs.filter(
            Q(phone__isnull=True) | Q(phone="") | Q(phone="None")
        ).order_by("-created_at")[:20]

        for lead in missing_phone_leads:
            add_item(
                tab_key="data_quality",
                work_type="missing_phone",
                work_type_label="Missing Phone",
                title=f"Missing Phone Number: {lead.name}",
                description=f"Lead # {lead.lead_number or lead.id} has no valid mobile phone recorded.",
                urgency="high",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "email": lead.email}
            )

        # B. Intern Lead Missing Target Course (MEDIUM)
        intern_no_course = leads_qs.filter(
            lead_category="intern",
            course__isnull=True
        ).order_by("-created_at")[:20]

        for lead in intern_no_course:
            add_item(
                tab_key="data_quality",
                work_type="intern_missing_course",
                work_type_label="Intern Lead Missing Course",
                title=f"Intern Lead with No Target Course: {lead.name}",
                description="Lead is categorized as 'Intern' but has no course linked in the system.",
                urgency="medium",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "phone": lead.phone}
            )

        # C. Client Lead Missing Project Requirement (MEDIUM)
        client_no_req = leads_qs.filter(
            lead_category="client"
        ).filter(
            Q(project_requirement__isnull=True) | Q(project_requirement="")
        ).order_by("-created_at")[:20]

        for lead in client_no_req:
            add_item(
                tab_key="data_quality",
                work_type="client_missing_requirement",
                work_type_label="Client Lead Missing Requirements",
                title=f"Client Lead Missing Requirements: {lead.name}",
                description="B2B Client lead does not have any project requirement or scope details recorded.",
                urgency="medium",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "company": lead.company}
            )

        # D. Potential Duplicates by Phone (MEDIUM)
        duplicate_phones = list(
            leads_qs.exclude(Q(phone__isnull=True) | Q(phone=""))
            .values("phone")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
            .values_list("phone", flat=True)[:10]
        )
        if duplicate_phones:
            dup_leads = leads_qs.filter(phone__in=duplicate_phones).order_by("phone")[:20]
            for lead in dup_leads:
                add_item(
                    tab_key="data_quality",
                    work_type="potential_duplicate",
                    work_type_label="Potential Duplicate",
                    title=f"Duplicate Phone ({lead.phone}): {lead.name}",
                    description=f"Multiple lead records share phone number {lead.phone}. Check for duplicate entries.",
                    urgency="medium",
                    record_id=lead.id,
                    action_url=f"/leads/admin/{lead.id}/",
                    meta={"lead_id": lead.id, "lead_name": lead.name, "phone": lead.phone}
                )

        # ---------------------------------------------------------------------
        # TAB 6: CONVERSIONS & RNR
        # ---------------------------------------------------------------------
        # A. Converted Intern Leads Awaiting Academy Enrollment (MEDIUM)
        converted_interns = leads_qs.filter(
            lead_category="intern",
            lead_status__in=["converted", "registration"]
        ).order_by("-created_at")[:20]

        for lead in converted_interns:
            add_item(
                tab_key="conversion",
                work_type="converted_unregistered",
                work_type_label="Converted Lead Pending Enrollment",
                title=f"Converted Lead Pending Academy Enrollment: {lead.name}",
                description=f"Lead is marked '{lead.get_lead_status_display()}'. Verify student registration and batch allocation in Academy module.",
                urgency="medium",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "course": lead.course.title if lead.course else None,
                    "salesperson": lead.salesperson.first_name if lead.salesperson else None
                }
            )

        # B. RNR / Busy Leads Revisit Due (LOW)
        rnr_cutoff = today - timedelta(days=5)
        rnr_leads = leads_qs.filter(
            lead_status__in=["rnr", "busy", "number_not_valid"]
        ).annotate(
            recent_fu=Count("follow_ups", filter=Q(follow_ups__date__gte=rnr_cutoff))
        ).filter(
            recent_fu=0
        ).order_by("-created_at")[:20]

        for lead in rnr_leads:
            add_item(
                tab_key="conversion",
                work_type="rnr_revisit_due",
                work_type_label="RNR Re-engagement Due",
                title=f"RNR Re-engagement Due: {lead.name}",
                description=f"Lead marked as '{lead.get_lead_status_display()}' over 5 days ago. Ready for a re-call attempt or reassignment.",
                urgency="low",
                record_id=lead.id,
                action_url=f"/leads/admin/{lead.id}/",
                meta={"lead_id": lead.id, "lead_name": lead.name, "status": lead.lead_status, "phone": lead.phone}
            )

        # ---------------------------------------------------------------------
        # 3. Assemble Response
        # ---------------------------------------------------------------------
        tab_counts = {tab["key"]: len(tab_items[tab["key"]]) for tab in self.TAB_DEFINITIONS}
        total_pending_count = sum(tab_counts.values())

        tabs_data = []
        for tab in self.TAB_DEFINITIONS:
            t_key = tab["key"]
            cat_list = list(tab_categories[t_key].values())
            tabs_data.append({
                "key": t_key,
                "label": tab["label"],
                "count": tab_counts[t_key],
                "categories": cat_list,
            })

        # Selected tab items
        if active_tab == "all":
            selected_items = [item for t in self.TAB_DEFINITIONS for item in tab_items[t["key"]]]
        elif active_tab in tab_items:
            selected_items = tab_items[active_tab]
        else:
            selected_items = []

        # Apply urgency filter
        if urgency_filter in ["high", "medium", "low"]:
            selected_items = [i for i in selected_items if i["urgency"] == urgency_filter]

        # Apply search filter
        if search_query:
            selected_items = [
                i for i in selected_items
                if search_query in i["title"].lower()
                or search_query in i["description"].lower()
                or search_query in str(i.get("meta", {})).lower()
            ]

        # Apply limit
        try:
            limit = int(limit_param)
            if limit > 0:
                selected_items = selected_items[:limit]
        except (ValueError, TypeError):
            selected_items = selected_items[:100]

        response_data = {
            "module": "lead_management",
            "module_label": "Lead Management",
            "salesperson_info": salesperson_info,
            "total_pending_count": total_pending_count,
            "tab_counts": tab_counts,
            "tabs": tabs_data,
            "active_tab": active_tab,
            "items_count": len(selected_items),
            "items": selected_items,
        }

        serializer = LeadManagementPendingDashboardSerializer(response_data)
        return Response(
            {"status": "1", "message": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )
