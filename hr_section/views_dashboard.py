from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasModulePermission
from accounts.models import StaffProfile, JobDetail, Department, EmployeeRegistration
from attendance.models import DailyAttendance, AttendanceSession, LeaveRequest, Holiday
from payroll.models import PayrollPeriod, Payroll
from .models import JobPosting, JobApplication, OfferLetter


class BaseHrDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_module = "hr_dashboard"


# ---------------------------------------------------------------------------
# 1. Master Key Metrics Summary
# ---------------------------------------------------------------------------
class HrDashboardMetricsAPIView(BaseHrDashboardAPIView):
    """
    GET -> Single aggregation payload powering all top-level HR dashboard metric cards.
    """
    def get(self, request):
        today = timezone.localdate()
        current_month_str = today.strftime("%Y-%m")
        first_day_of_month = today.replace(day=1)

        # 1. Employee stats
        total_staff = StaffProfile.objects.filter(job_detail__isnull=False).count()
        active_staff = StaffProfile.objects.filter(job_detail__status="active").count()
        probation_staff = StaffProfile.objects.filter(job_detail__status="probation").count()
        new_joiners_this_month = StaffProfile.objects.filter(
            job_detail__start_date__gte=first_day_of_month,
            job_detail__start_date__lte=today
        ).count()

        # 2. Today's Attendance stats
        today_attendance_qs = DailyAttendance.objects.filter(date=today)
        present_count = today_attendance_qs.filter(status="full_day").count()
        half_day_count = today_attendance_qs.filter(status="half_day").count()
        on_leave_count = today_attendance_qs.filter(status="leave").count()
        absent_count = today_attendance_qs.filter(status="absent").count()

        late_count = today_attendance_qs.filter(
            sessions__status="late"
        ).distinct().count()

        # 3. Recruitment stats
        active_jobs_count = JobPosting.objects.filter(status="active").count()
        applications_this_month = JobApplication.objects.filter(
            applied_at__date__gte=first_day_of_month,
            applied_at__date__lte=today
        ).count()
        interviews_scheduled = JobApplication.objects.filter(status="interview_scheduled").count()
        pending_offers = OfferLetter.objects.filter(status__in=["draft", "sent"]).count()

        # 4. Payroll stats
        current_period = PayrollPeriod.objects.filter(month=current_month_str).first()
        period_status = current_period.status if current_period else "not_generated"
        
        payroll_qs = Payroll.objects.filter(month=current_month_str)
        payroll_agg = payroll_qs.aggregate(
            total_net=Sum("net_salary"),
            paid_count=Count("id", filter=Q(status="Paid")),
            draft_count=Count("id", filter=Q(status="Draft"))
        )

        return Response({
            "employee_summary": {
                "total_employees": total_staff,
                "active_employees": active_staff,
                "on_probation": probation_staff,
                "new_joiners_this_month": new_joiners_this_month,
            },
            "today_attendance": {
                "total_expected": total_staff,
                "present_count": present_count,
                "late_count": late_count,
                "half_day_count": half_day_count,
                "on_approved_leave": on_leave_count,
                "unaccounted_absent": absent_count,
            },
            "recruitment_summary": {
                "active_job_postings": active_jobs_count,
                "total_applications_this_month": applications_this_month,
                "interviews_scheduled": interviews_scheduled,
                "pending_offers": pending_offers,
            },
            "payroll_status": {
                "current_period": current_month_str,
                "period_status": period_status,
                "paid_records": payroll_agg["paid_count"] or 0,
                "pending_payouts_count": payroll_agg["draft_count"] or 0,
                "total_net_payroll": str(payroll_agg["total_net"] or "0.00"),
            }
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 2. Action Center / Pending Tasks
# ---------------------------------------------------------------------------
class HrDashboardActionItemsAPIView(BaseHrDashboardAPIView):
    """
    GET -> Aggregated action items and pending tasks requiring HR action.
    """
    def get(self, request):
        today = timezone.localdate()

        # 1. Pending Leaves
        pending_leaves = LeaveRequest.objects.filter(status="pending").select_related("staff__user")
        pending_leaves_count = pending_leaves.count()

        # 2. Pending Employee Registrations
        pending_registrations = EmployeeRegistration.objects.filter(is_converted=False)
        pending_registrations_count = pending_registrations.count()

        # 3. Pending Offer Letters
        pending_offers = OfferLetter.objects.filter(status="draft")
        pending_offers_count = pending_offers.count()

        # 4. Approaching Probation End (e.g. 90-day threshold, within next 15 days)
        # Using 75 to 90 days from start_date
        probation_threshold_min = today - timedelta(days=90)
        probation_threshold_max = today - timedelta(days=75)
        upcoming_probation = JobDetail.objects.filter(
            status="probation",
            start_date__gte=probation_threshold_min,
            start_date__lte=probation_threshold_max
        ).select_related("staff__user", "department")
        upcoming_probation_count = upcoming_probation.count()

        action_items = []

        for leave in pending_leaves[:5]:
            action_items.append({
                "type": "leave_request",
                "reference_id": leave.id,
                "title": f"Leave Approval: {leave.staff.get_full_name()}",
                "description": f"{leave.leave_days} day(s) from {leave.start_date} to {leave.end_date}. Reason: {leave.reason[:80]}",
                "created_at": leave.requested_at,
                "urgency": "high"
            })

        for reg in pending_registrations[:5]:
            action_items.append({
                "type": "employee_registration",
                "reference_id": reg.id,
                "title": f"Onboarding Registration: {reg.first_name} {reg.last_name or ''}".strip(),
                "description": f"Applied for role: {reg.designation or 'Not specified'}. Ready for staff conversion.",
                "created_at": reg.created_at,
                "urgency": "medium"
            })

        for offer in pending_offers[:5]:
            action_items.append({
                "type": "offer_letter",
                "reference_id": offer.id,
                "title": f"Draft Offer Letter: {offer.candidate_name}",
                "description": f"Position: {offer.job_title}, Joining: {offer.joining_date}",
                "created_at": offer.created_at,
                "urgency": "medium"
            })

        for jd in upcoming_probation[:5]:
            days_served = (today - jd.start_date).days
            action_items.append({
                "type": "probation_review",
                "reference_id": jd.id,
                "title": f"Probation Review: {jd.staff.get_full_name()}",
                "description": f"Department: {jd.department.name if jd.department else 'N/A'}. Days in probation: {days_served}/90.",
                "created_at": jd.start_date,
                "urgency": "low"
            })

        return Response({
            "pending_leave_requests_count": pending_leaves_count,
            "pending_employee_registrations_count": pending_registrations_count,
            "pending_offers_count": pending_offers_count,
            "upcoming_probation_reviews_count": upcoming_probation_count,
            "total_pending_actions": (
                pending_leaves_count + pending_registrations_count + pending_offers_count + upcoming_probation_count
            ),
            "action_items": action_items
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 3. Today's Staff Live Attendance Feed
# ---------------------------------------------------------------------------
class HrDashboardLiveAttendanceAPIView(BaseHrDashboardAPIView):
    """
    GET -> Real-time attendance feed of staff today with status and punch-in details.
    Query params:
      - status: full_day, half_day, leave, absent, late
      - department: department_id
      - limit: int (default: 15)
    """
    def get(self, request):
        today = timezone.localdate()
        status_filter = request.query_params.get("status")
        dept_filter = request.query_params.get("department")
        limit = int(request.query_params.get("limit", 15))

        attendance_qs = DailyAttendance.objects.filter(date=today).select_related(
            "staff__user", "staff__job_detail__department"
        ).prefetch_related("sessions")

        if dept_filter and dept_filter.isdigit():
            attendance_qs = attendance_qs.filter(staff__job_detail__department_id=int(dept_filter))

        if status_filter:
            if status_filter == "late":
                attendance_qs = attendance_qs.filter(sessions__status="late").distinct()
            else:
                attendance_qs = attendance_qs.filter(status=status_filter)

        summary = {
            "total_recorded": attendance_qs.count(),
            "full_day": attendance_qs.filter(status="full_day").count(),
            "half_day": attendance_qs.filter(status="half_day").count(),
            "leave": attendance_qs.filter(status="leave").count(),
            "absent": attendance_qs.filter(status="absent").count(),
        }

        results = []
        for att in attendance_qs[:limit]:
            sessions = list(att.sessions.all())
            login_times = [s.login_time for s in sessions if s.login_time]
            logout_times = [s.logout_time for s in sessions if s.logout_time]
            is_late = any(s.status == "late" for s in sessions)

            job_detail = getattr(att.staff, "job_detail", None)
            dept = getattr(job_detail, "department", None) if job_detail else None

            results.append({
                "id": att.id,
                "staff_id": att.staff_id,
                "employee_id": job_detail.employee_id if job_detail else None,
                "staff_name": att.staff.get_full_name(),
                "email": att.staff.user.email,
                "department": dept.name if dept else None,
                "status": att.status,
                "is_late": is_late,
                "first_check_in": min(login_times).strftime("%H:%M:%S") if login_times else None,
                "last_check_out": max(logout_times).strftime("%H:%M:%S") if logout_times else None,
                "total_working_hours": str(att.total_working_hours),
            })

        return Response({
            "date": str(today),
            "summary": summary,
            "results": results
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 4. Active & Upcoming Staff On Leave
# ---------------------------------------------------------------------------
class HrDashboardLeavesActiveUpcomingAPIView(BaseHrDashboardAPIView):
    """
    GET -> Employees currently on approved leave today and scheduled upcoming leaves.
    Query params:
      - days_ahead: int (default: 7)
    """
    def get(self, request):
        today = timezone.localdate()
        days_ahead = int(request.query_params.get("days_ahead", 7))
        future_cutoff = today + timedelta(days=days_ahead)

        # On leave today
        today_leaves = LeaveRequest.objects.filter(
            status="approved",
            start_date__lte=today,
            end_date__gte=today
        ).select_related("staff__user", "staff__job_detail__department").order_by("end_date")

        # Upcoming leaves starting after today
        upcoming_leaves = LeaveRequest.objects.filter(
            status="approved",
            start_date__gt=today,
            start_date__lte=future_cutoff
        ).select_related("staff__user", "staff__job_detail__department").order_by("start_date")

        def serialize_leave(leave):
            job_detail = getattr(leave.staff, "job_detail", None)
            dept = getattr(job_detail, "department", None) if job_detail else None
            return {
                "leave_id": leave.id,
                "staff_id": leave.staff_id,
                "staff_name": leave.staff.get_full_name(),
                "department": dept.name if dept else None,
                "start_date": str(leave.start_date),
                "end_date": str(leave.end_date),
                "leave_days": leave.leave_days,
                "reason": leave.reason,
            }

        return Response({
            "on_leave_today": [serialize_leave(l) for l in today_leaves],
            "upcoming_leaves": [serialize_leave(l) for l in upcoming_leaves],
            "days_ahead": days_ahead
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 5. Upcoming Company Holidays Widget
# ---------------------------------------------------------------------------
class HrDashboardUpcomingHolidaysAPIView(BaseHrDashboardAPIView):
    """
    GET -> Upcoming holidays with day countdown.
    Query params:
      - limit: int (default: 5)
    """
    def get(self, request):
        today = timezone.localdate()
        limit = int(request.query_params.get("limit", 5))

        holidays = Holiday.objects.filter(date__gte=today).order_by("date")[:limit]

        results = []
        for h in holidays:
            days_left = (h.date - today).days
            results.append({
                "id": h.id,
                "name": h.name,
                "date": str(h.date),
                "day_of_week": h.date.strftime("%A"),
                "is_paid": h.is_paid,
                "days_remaining": days_left
            })

        return Response(results, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 6. Department Headcount & Daily Presence
# ---------------------------------------------------------------------------
class HrDashboardDepartmentsSummaryAPIView(BaseHrDashboardAPIView):
    """
    GET -> Department-wise roster with headcount and today's presence.
    """
    def get(self, request):
        today = timezone.localdate()

        departments = Department.objects.annotate(
            total_staff=Count("jobdetail", distinct=True),
            active_staff=Count("jobdetail", filter=Q(jobdetail__status="active"), distinct=True)
        ).order_by("name")

        results = []
        for dept in departments:
            # Query attendance for staff in this department today
            dept_staff_ids = JobDetail.objects.filter(department=dept).values_list("staff_id", flat=True)
            present_today = DailyAttendance.objects.filter(
                staff_id__in=dept_staff_ids,
                date=today,
                status="full_day"
            ).count()
            on_leave_today = DailyAttendance.objects.filter(
                staff_id__in=dept_staff_ids,
                date=today,
                status="leave"
            ).count()

            results.append({
                "department_id": dept.id,
                "department_name": dept.name,
                "total_staff": dept.total_staff,
                "active_staff": dept.active_staff,
                "present_today": present_today,
                "on_leave_today": on_leave_today
            })

        return Response(results, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 7. Employee Milestones (Birthdays & Anniversaries)
# ---------------------------------------------------------------------------
class HrDashboardMilestonesAPIView(BaseHrDashboardAPIView):
    """
    GET -> Birthdays and work anniversaries in the current month.
    """
    def get(self, request):
        today = timezone.localdate()
        current_month = today.month

        # Birthdays in current month
        birthdays_qs = StaffProfile.objects.filter(
            date_of_birth__month=current_month
        ).select_related("user", "job_detail__department").order_by("date_of_birth__day")

        birthdays = []
        for profile in birthdays_qs:
            dept = profile.job_detail.department.name if getattr(profile, "job_detail", None) and profile.job_detail.department else None
            birthdays.append({
                "staff_id": profile.id,
                "name": profile.get_full_name(),
                "date_of_birth": str(profile.date_of_birth),
                "day_and_month": profile.date_of_birth.strftime("%d %b"),
                "department": dept
            })

        # Work anniversaries in current month
        anniversaries_qs = JobDetail.objects.filter(
            start_date__month=current_month,
            start_date__lt=today.replace(day=1)  # Only prior years
        ).select_related("staff__user", "department").order_by("start_date__day")

        anniversaries = []
        for jd in anniversaries_qs:
            years = today.year - jd.start_date.year
            anniversaries.append({
                "staff_id": jd.staff_id,
                "name": jd.staff.get_full_name(),
                "start_date": str(jd.start_date),
                "day_and_month": jd.start_date.strftime("%d %b"),
                "years_completed": years,
                "department": jd.department.name if jd.department else None
            })

        return Response({
            "current_month": today.strftime("%B"),
            "birthdays": birthdays,
            "work_anniversaries": anniversaries
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 8. Active Job Openings & Recruitment Pipeline Summary
# ---------------------------------------------------------------------------
class HrDashboardRecruitmentJobsSummaryAPIView(BaseHrDashboardAPIView):
    """
    GET -> Active job postings with candidate breakdown per hiring stage.
    """
    def get(self, request):
        jobs = JobPosting.objects.filter(status="active").annotate(
            total_apps=Count("applications", distinct=True),
            applied_count=Count("applications", filter=Q(applications__status="applied"), distinct=True),
            under_review_count=Count("applications", filter=Q(applications__status="under_review"), distinct=True),
            shortlisted_count=Count("applications", filter=Q(applications__status="shortlisted"), distinct=True),
            interview_count=Count("applications", filter=Q(applications__status="interview_scheduled"), distinct=True),
            hired_count=Count("applications", filter=Q(applications__status="hired"), distinct=True),
        ).select_related("designation").order_by("-created_at")

        results = []
        for job in jobs:
            results.append({
                "job_id": job.id,
                "job_title": job.job_title,
                "designation": job.designation.name if job.designation else None,
                "job_type": job.job_type,
                "work_mode": job.work_mode,
                "experience_required": job.experience_required,
                "salary_range": job.salery_range,
                "total_applications": job.total_apps,
                "stage_breakdown": {
                    "applied": job.applied_count,
                    "under_review": job.under_review_count,
                    "shortlisted": job.shortlisted_count,
                    "interview_scheduled": job.interview_count,
                    "hired": job.hired_count
                },
                "created_at": job.created_at.strftime("%Y-%m-%d")
            })

        return Response(results, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 9. Recent Job Applications Feed
# ---------------------------------------------------------------------------
class HrDashboardRecentApplicationsAPIView(BaseHrDashboardAPIView):
    """
    GET -> Latest job applications submitted for fast recruiter review.
    Query params:
      - limit: int (default: 8)
      - status: filter by application status
    """
    def get(self, request):
        limit = int(request.query_params.get("limit", 8))
        status_filter = request.query_params.get("status")

        apps_qs = JobApplication.objects.select_related("job", "designation").order_by("-applied_at")
        if status_filter:
            apps_qs = apps_qs.filter(status=status_filter)

        results = []
        for app in apps_qs[:limit]:
            results.append({
                "application_id": app.id,
                "candidate_name": f"{app.first_name} {app.last_name or ''}".strip(),
                "email": app.email,
                "phone": app.phone,
                "job_title": app.job.job_title if app.job else "Direct Application",
                "designation": app.designation.name if app.designation else None,
                "experience_years": app.experience,
                "status": app.status,
                "applied_at": app.applied_at,
                "resume_url": app.resume.url if app.resume else None
            })

        return Response(results, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 10. Current Payroll Processing Snapshot
# ---------------------------------------------------------------------------
class HrDashboardPayrollStatusAPIView(BaseHrDashboardAPIView):
    """
    GET -> Monthly payroll progress card for finance/HR compliance.
    Query params:
      - period_month: YYYY-MM (default: current month)
    """
    def get(self, request):
        today = timezone.localdate()
        period_month = request.query_params.get("period_month", today.strftime("%Y-%m"))

        period = PayrollPeriod.objects.filter(month=period_month).first()
        payroll_qs = Payroll.objects.filter(month=period_month)

        agg = payroll_qs.aggregate(
            total_records=Count("id"),
            paid_count=Count("id", filter=Q(status="Paid")),
            draft_count=Count("id", filter=Q(status="Draft")),
            total_gross=Sum("gross_salary"),
            total_net=Sum("net_salary"),
            total_deductions=Sum("deduction")
        )

        return Response({
            "period": period_month,
            "period_status": period.status if period else "not_generated",
            "generated_at": period.generated_at if period else None,
            "total_records": agg["total_records"] or 0,
            "paid_records": agg["paid_count"] or 0,
            "draft_records": agg["draft_count"] or 0,
            "total_gross_payable": str(agg["total_gross"] or "0.00"),
            "total_net_payable": str(agg["total_net"] or "0.00"),
            "total_deductions": str(agg["total_deductions"] or "0.00"),
        }, status=status.HTTP_200_OK)
