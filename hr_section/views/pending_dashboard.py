from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers

from accounts.models import EmployeeRegistration
from accounts.permissions import HasModulePermission
from accounts.serializers.pending_dashboard import PendingTabSerializer, PendingWorkItemSerializer
from accounts.views.pending_dashboard import _BasePendingDashboardAPIView, _date_to_aware_dt
from attendance.models import LeaveRequest
from hr_section.models import Enquiry, ErpEnquiry, HRPolicy
from payroll.models import Payroll, PayrollPeriod


class HrPendingDashboardSerializer(serializers.Serializer):
    """Top-level response serializer for HR Pending Controls Dashboard."""

    module = serializers.CharField(default="hr")
    module_label = serializers.CharField(default="HR")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = PendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = PendingWorkItemSerializer(many=True)


class HrPendingDashboardAPIView(_BasePendingDashboardAPIView):
    """
    HR Module Pending Controls Dashboard API.

    Returns actionable pending items across:
      - employee_registration: Pending / reviewed employee registrations not yet converted to staff
      - leaves: Pending staff leave requests awaiting HR approval
      - payroll: Open/unlocked payroll periods and unpaid Draft salary slips
      - enquiries: Unresponded HR enquiries and ERP enquiries
      - policies: Draft HR policies not yet published as active
    """

    permission_classes = [_BasePendingDashboardAPIView.permission_classes[0], HasModulePermission]
    required_module = "hr_pending"
    module_key = "hr"
    module_label = "HR"
    serializer_class = HrPendingDashboardSerializer

    TAB_DEFINITIONS = [
        {"key": "employee_registration", "label": "Employee Registrations"},
        {"key": "leaves", "label": "Leave Requests"},
        {"key": "payroll", "label": "Payroll"},
        {"key": "enquiries", "label": "HR Enquiries"},
        {"key": "policies", "label": "HR Policies"},
    ]

    def get(self, request):
        tab_items, tab_categories, add_item = self._init_buckets()
        now = timezone.now()
        today = timezone.localdate()
        current_month = today.strftime("%Y-%m")

        # ── 1. Employee Registrations (accounts.EmployeeRegistration) ────────
        pending_registrations = EmployeeRegistration.objects.filter(
            is_converted=False,
            status__in=["pending", "reviewed"],
        ).order_by("id")

        for reg in pending_registrations:
            full_name = f"{reg.first_name} {reg.last_name}".strip() or reg.email
            created_at = getattr(reg, "created_at", None)
            days_pending = (now - created_at).days if created_at else 0

            if reg.status == "pending":
                urgency = "high" if days_pending > 3 else "medium"
                add_item(
                    tab_key="employee_registration",
                    work_type="employee_registration_pending",
                    work_type_label="Registration Pending Review",
                    title=f"{full_name} - Registration Pending Review",
                    description=(
                        f"Employee registration for {full_name} ({reg.email}) is pending HR review"
                        + (f" for {days_pending} day(s)." if days_pending > 0 else ".")
                    ),
                    urgency=urgency,
                    record_id=reg.id,
                    item_id=f"emp_reg_pending_{reg.id}",
                    created_at=created_at,
                    action_url=f"/accounts/employee-registration/{reg.id}/",
                    meta={
                        "registration_id": reg.id,
                        "full_name": full_name,
                        "email": reg.email,
                        "phone_number": reg.phone_number,
                        "qualification": reg.qualification,
                        "status": reg.status,
                        "is_converted": reg.is_converted,
                        "days_pending": days_pending,
                    },
                )
            elif reg.status == "reviewed":
                urgency = "high" if days_pending > 5 else "medium"
                add_item(
                    tab_key="employee_registration",
                    work_type="employee_registration_reviewed",
                    work_type_label="Registration Ready to Convert",
                    title=f"{full_name} - Ready to Convert to Staff",
                    description=(
                        f"Employee registration for {full_name} ({reg.email}) has been reviewed "
                        "and is awaiting conversion to a staff profile."
                    ),
                    urgency=urgency,
                    record_id=reg.id,
                    item_id=f"emp_reg_reviewed_{reg.id}",
                    created_at=created_at,
                    action_url=f"/accounts/employee-registration/{reg.id}/convert/",
                    meta={
                        "registration_id": reg.id,
                        "full_name": full_name,
                        "email": reg.email,
                        "phone_number": reg.phone_number,
                        "qualification": reg.qualification,
                        "status": reg.status,
                        "is_converted": reg.is_converted,
                        "days_pending": days_pending,
                    },
                )

        # ── 2. Leave Requests (attendance.LeaveRequest) ──────────────────────
        pending_leaves = (
            LeaveRequest.objects.filter(status="pending")
            .select_related("staff__user")
            .order_by("start_date", "requested_at")
        )

        for leave in pending_leaves:
            user = leave.staff.user
            full_name = f"{user.first_name} {user.last_name}".strip() or user.email
            days_since_request = (now - leave.requested_at).days if leave.requested_at else 0
            starts_soon = leave.start_date <= (today + timedelta(days=2))
            urgency = "high" if (starts_soon or days_since_request > 2) else "medium"

            leave_span = (
                f"Half-day on {leave.start_date.strftime('%d-%b-%Y')}"
                if leave.is_half_day
                else f"{leave.leave_days} day(s) ({leave.start_date.strftime('%d-%b-%Y')} to {leave.end_date.strftime('%d-%b-%Y')})"
            )

            add_item(
                tab_key="leaves",
                work_type="leave_pending_approval",
                work_type_label="Leave Pending Approval",
                title=f"{full_name} - Leave Request ({leave.start_date.strftime('%d-%b-%Y')})",
                description=f"{leave_span}. Reason: {leave.reason[:120]}",
                urgency=urgency,
                record_id=leave.id,
                item_id=f"leave_pending_{leave.id}",
                created_at=leave.requested_at,
                due_date=leave.start_date.isoformat(),
                action_url=f"/attendance/hr/leave-requests/{leave.id}/",
                meta={
                    "leave_id": leave.id,
                    "staff_id": leave.staff_id,
                    "staff_name": full_name,
                    "email": user.email,
                    "start_date": leave.start_date.isoformat(),
                    "end_date": leave.end_date.isoformat(),
                    "is_half_day": leave.is_half_day,
                    "leave_days": leave.leave_days,
                    "status": leave.status,
                    "days_pending": days_since_request,
                },
            )

        # ── 3. Payroll (payroll.PayrollPeriod & payroll.Payroll) ─────────────
        periods = (
            PayrollPeriod.objects.filter(status__in=["open", "generated"])
            .annotate(
                total_slips=Count("payrolls"),
                draft_slips=Count("payrolls", filter=Q(payrolls__status="Draft")),
            )
            .order_by("month")
        )

        for period in periods:
            is_past_month = period.month < current_month

            if period.status == "open":
                urgency = "high" if is_past_month else "medium"
                add_item(
                    tab_key="payroll",
                    work_type="payroll_period_open",
                    work_type_label="Payroll Not Generated",
                    title=f"Payroll Period {period.month} - Open",
                    description=f"Payroll for {period.month} is still open and has not been generated yet.",
                    urgency=urgency,
                    record_id=period.id,
                    item_id=f"payroll_period_open_{period.id}",
                    created_at=period.generated_at,
                    action_url=f"/payroll/periods/{period.id}/",
                    meta={
                        "period_id": period.id,
                        "month": period.month,
                        "status": period.status,
                        "is_past_month": is_past_month,
                    },
                )
            elif period.status == "generated" and (is_past_month or period.draft_slips == 0):
                add_item(
                    tab_key="payroll",
                    work_type="payroll_period_unlocked",
                    work_type_label="Payroll Period Unlocked",
                    title=f"Payroll Period {period.month} - Pending Lock",
                    description=(
                        f"Payroll for {period.month} is generated ({period.total_slips} slip(s), "
                        f"{period.draft_slips} draft) and has not been locked yet."
                    ),
                    urgency="medium",
                    record_id=period.id,
                    item_id=f"payroll_period_unlocked_{period.id}",
                    created_at=period.generated_at,
                    action_url=f"/payroll/periods/{period.id}/",
                    meta={
                        "period_id": period.id,
                        "month": period.month,
                        "status": period.status,
                        "total_slips": period.total_slips,
                        "draft_slips": period.draft_slips,
                        "is_past_month": is_past_month,
                    },
                )

        draft_payrolls = (
            Payroll.objects.filter(status="Draft")
            .select_related("staff__user", "period")
            .order_by("month", "id")
        )

        for slip in draft_payrolls:
            user = slip.staff.user
            full_name = f"{user.first_name} {user.last_name}".strip() or user.email
            slip_month = slip.period.month if slip.period else slip.month
            is_past_month = slip_month < current_month
            days_pending = (now - slip.created_at).days if slip.created_at else 0
            urgency = "high" if (is_past_month or days_pending > 3) else "medium"

            add_item(
                tab_key="payroll",
                work_type="payroll_draft_unpaid",
                work_type_label="Unpaid Draft Payroll",
                title=f"{full_name} ({slip_month}) - Salary Unpaid",
                description=(
                    f"Net salary of ₹{slip.net_salary} for {slip_month} is in Draft status "
                    "and has not been marked Paid."
                ),
                urgency=urgency,
                record_id=slip.id,
                item_id=f"payroll_draft_{slip.id}",
                created_at=slip.created_at,
                action_url=f"/payroll/{slip.id}/",
                meta={
                    "payroll_id": slip.id,
                    "staff_id": slip.staff_id,
                    "staff_name": full_name,
                    "email": user.email,
                    "month": slip_month,
                    "gross_salary": str(slip.gross_salary),
                    "net_salary": str(slip.net_salary),
                    "status": slip.status,
                    "days_pending": days_pending,
                },
            )

        # ── 4. HR Enquiries (hr_section.Enquiry & hr_section.ErpEnquiry) ─────
        pending_enquiries = Enquiry.objects.filter(status__in=["new", "reviewed"]).order_by("created_at")

        for enq in pending_enquiries:
            full_name = f"{enq.first_name} {enq.last_name or ''}".strip() or enq.email
            days_pending = (now - enq.created_at).days if enq.created_at else 0

            if enq.status == "new":
                urgency = "high" if days_pending > 2 else "medium"
                work_type = "hr_enquiry_new"
                work_type_label = "New HR Enquiry"
                title = f"{full_name} - New HR Enquiry"
            else:
                urgency = "medium" if days_pending > 3 else "low"
                work_type = "hr_enquiry_reviewed"
                work_type_label = "Reviewed Enquiry Unresponded"
                title = f"{full_name} - Awaiting Response"

            add_item(
                tab_key="enquiries",
                work_type=work_type,
                work_type_label=work_type_label,
                title=title,
                description=f"Enquiry from {enq.email} ({enq.phone}): {enq.message[:120]}",
                urgency=urgency,
                record_id=enq.id,
                item_id=f"hr_enquiry_{enq.status}_{enq.id}",
                created_at=enq.created_at,
                action_url=f"/hr/enquiry/{enq.id}/status/",
                meta={
                    "enquiry_id": enq.id,
                    "enquiry_source": "client enquiry",
                    "full_name": full_name,
                    "email": enq.email,
                    "phone": enq.phone,
                    "status": enq.status,
                    "days_pending": days_pending,
                },
            )

        pending_erp_enquiries = ErpEnquiry.objects.filter(status__in=["new", "reviewed"]).order_by("created_at")

        for erp in pending_erp_enquiries:
            days_pending = (now - erp.created_at).days if erp.created_at else 0
            preferred_soon = bool(
                erp.preferred_datetime and erp.preferred_datetime <= (now + timedelta(hours=24))
            )

            if erp.status == "new":
                urgency = "high" if (days_pending > 2 or preferred_soon) else "medium"
                work_type = "erp_enquiry_new"
                work_type_label = "New ERP Enquiry"
                title = f"{erp.full_name} ({erp.company_name}) - New ERP Enquiry"
            else:
                urgency = "medium"
                work_type = "erp_enquiry_reviewed"
                work_type_label = "Reviewed ERP Enquiry Unresponded"
                title = f"{erp.full_name} ({erp.company_name}) - Awaiting Response"

            add_item(
                tab_key="enquiries",
                work_type=work_type,
                work_type_label=work_type_label,
                title=title,
                description=(
                    f"ERP enquiry from {erp.company_name} ({erp.work_email}) is in '{erp.status}' status."
                ),
                urgency=urgency,
                record_id=erp.id,
                item_id=f"erp_enquiry_{erp.status}_{erp.id}",
                created_at=erp.created_at,
                due_date=erp.preferred_datetime.date().isoformat() if erp.preferred_datetime else None,
                action_url=f"/hr/erp/enquiry/{erp.id}/status/",
                meta={
                    "enquiry_id": erp.id,
                    "enquiry_source": "product enquiry",
                    "full_name": erp.full_name,
                    "company_name": erp.company_name,
                    "work_email": erp.work_email,
                    "phone_number": erp.phone_number,
                    "status": erp.status,
                    "preferred_datetime": erp.preferred_datetime.isoformat() if erp.preferred_datetime else None,
                    "days_pending": days_pending,
                },
            )

        # ── 5. HR Policies (hr_section.HRPolicy) ─────────────────────────────
        draft_policies = HRPolicy.objects.filter(status="draft").order_by("created_at")

        for policy in draft_policies:
            effective_due = bool(policy.effective_date and policy.effective_date <= today)
            urgency = "medium" if effective_due else "low"

            add_item(
                tab_key="policies",
                work_type="hr_policy_draft",
                work_type_label="Draft HR Policy",
                title=f"{policy.title}" + (f" ({policy.policy_code})" if policy.policy_code else "") + " - Draft",
                description=(
                    f"HR policy '{policy.title}' is still in draft and has not been published as active."
                ),
                urgency=urgency,
                record_id=policy.id,
                item_id=f"hr_policy_draft_{policy.id}",
                created_at=policy.created_at or _date_to_aware_dt(policy.effective_date),
                due_date=policy.effective_date.isoformat() if policy.effective_date else None,
                action_url=f"/hr/policies/{policy.id}/",
                meta={
                    "policy_id": policy.id,
                    "title": policy.title,
                    "policy_code": policy.policy_code,
                    "effective_date": policy.effective_date.isoformat() if policy.effective_date else None,
                    "status": policy.status,
                },
            )

        return self._build_response(request, tab_items, tab_categories)
