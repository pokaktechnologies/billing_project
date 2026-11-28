from decimal import Decimal
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Department, JobDetail


def _parse_preview_limit(value, default=3, min_val=1, max_val=20):
    if value is None or str(value).strip() == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_val, min(max_val, parsed))


def _serialize_job_detail_staff(job_detail, request):
    """Serialize a JobDetail + StaffProfile + CustomUser record for department statistics."""
    staff = job_detail.staff
    user = staff.user
    full_name = user.get_full_name() or user.email
    profile_image = None
    if staff.profile_image:
        profile_image = request.build_absolute_uri(staff.profile_image.url)

    return {
        "staff_id": job_detail.staff_id,
        "user_id": staff.user_id,
        "employee_id": job_detail.employee_id,
        "full_name": full_name,
        "email": staff.staff_email or user.email,
        "phone_number": staff.phone_number,
        "role": job_detail.role,
        "status": job_detail.status,
        "job_type": job_detail.job_type,
        "start_date": job_detail.start_date.isoformat() if job_detail.start_date else None,
        "profile_image": profile_image,
    }


def _apply_job_filters(queryset, status_param, job_type_param):
    if status_param:
        queryset = queryset.filter(status=status_param)
    if job_type_param:
        queryset = queryset.filter(job_type=job_type_param)
    return queryset


class DepartmentStatisticsView(APIView):
    """
    GET -> Department-wise staff statistics, formatted staff previews,
    overall totals, and status/job_type/salary breakdowns.
    """
    permission_classes = [IsAuthenticated]

    STATUS_KEYS = ("active", "probation", "resigned", "terminated", "inactive")
    JOB_TYPE_KEYS = ("full_day", "part_time", "internship", "contract")

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_param = request.query_params.get("status", "").strip()
        job_type_param = request.query_params.get("job_type", "").strip()
        preview_limit = _parse_preview_limit(request.query_params.get("preview_limit"))

        job_qs = JobDetail.objects.select_related("staff__user").order_by(
            "staff__user__first_name", "staff__user__last_name", "id"
        )
        job_qs = _apply_job_filters(job_qs, status_param, job_type_param)

        departments_qs = Department.objects.all().order_by("name")
        if search:
            departments_qs = departments_qs.filter(name__icontains=search)

        departments_qs = departments_qs.prefetch_related(
            Prefetch("jobdetail_set", queryset=job_qs, to_attr="prefetched_job_details")
        )

        unassigned_staff_count = job_qs.filter(department__isnull=True).count()

        departments_data = []
        total_staff = 0
        total_active_staff = 0
        total_probation_staff = 0
        total_inactive_staff = 0
        overall_job_type_breakdown = {key: 0 for key in self.JOB_TYPE_KEYS}
        largest_department = None

        for dept in departments_qs:
            jobs = getattr(dept, "prefetched_job_details", [])
            staff_count = len(jobs)

            preview_jobs = jobs[:preview_limit]
            staff_preview_names = [
                j.staff.user.get_full_name() or j.staff.user.email for j in preview_jobs
            ]
            remaining_staff_count = max(0, staff_count - len(preview_jobs))

            if staff_preview_names:
                staff_preview_text = ", ".join(staff_preview_names)
                if remaining_staff_count > 0:
                    staff_preview_text = f"{staff_preview_text}, +{remaining_staff_count}"
            else:
                staff_preview_text = ""

            status_breakdown = {key: 0 for key in self.STATUS_KEYS}
            job_type_breakdown = {key: 0 for key in self.JOB_TYPE_KEYS}
            roles_set = set()
            total_salary = Decimal("0.00")

            for job in jobs:
                if job.status in status_breakdown:
                    status_breakdown[job.status] += 1
                if job.job_type in job_type_breakdown:
                    job_type_breakdown[job.job_type] += 1
                    overall_job_type_breakdown[job.job_type] += 1
                if job.role:
                    roles_set.add(job.role)
                if job.salary is not None:
                    total_salary += job.salary

            average_salary = (total_salary / staff_count) if staff_count > 0 else Decimal("0.00")

            dept_entry = {
                "department_id": dept.id,
                "department_name": dept.name,
                "staff_count": staff_count,
                "staff_percentage": 0.0,
                "staff_preview_names": staff_preview_names,
                "remaining_staff_count": remaining_staff_count,
                "staff_preview_text": staff_preview_text,
                "has_more_staff": remaining_staff_count > 0,
                "full_staff_url": f"/accounts/departments/{dept.id}/staff/",
                "status_breakdown": status_breakdown,
                "job_type_breakdown": job_type_breakdown,
                "roles": sorted(roles_set),
                "total_salary": f"{total_salary:.2f}",
                "average_salary": f"{average_salary:.2f}",
            }

            departments_data.append(dept_entry)

            total_staff += staff_count
            total_active_staff += status_breakdown["active"]
            total_probation_staff += status_breakdown["probation"]
            total_inactive_staff += (
                status_breakdown["resigned"]
                + status_breakdown["terminated"]
                + status_breakdown["inactive"]
            )

            if largest_department is None or staff_count > largest_department["staff_count"]:
                largest_department = {
                    "department_id": dept.id,
                    "department_name": dept.name,
                    "staff_count": staff_count,
                }

        total_departments = len(departments_data)
        if total_staff > 0:
            for dept_entry in departments_data:
                dept_entry["staff_percentage"] = round(
                    (dept_entry["staff_count"] / total_staff) * 100, 2
                )

        summary = {
            "total_departments": total_departments,
            "total_staff": total_staff,
            "unassigned_staff_count": unassigned_staff_count,
            "total_active_staff": total_active_staff,
            "total_probation_staff": total_probation_staff,
            "total_inactive_staff": total_inactive_staff,
            "average_staff_per_department": (
                round(total_staff / total_departments, 2) if total_departments > 0 else 0.0
            ),
            "largest_department": largest_department,
            "job_type_breakdown": overall_job_type_breakdown,
        }

        return Response(
            {
                "status": "1",
                "message": "Department statistics fetched successfully",
                "summary": summary,
                "departments": departments_data,
            },
            status=status.HTTP_200_OK,
        )


class DepartmentStaffListView(APIView):
    """
    GET -> Full list of staff members belonging to a specific department.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, department_id):
        department = get_object_or_404(Department, id=department_id)
        search = request.query_params.get("search", "").strip()
        status_param = request.query_params.get("status", "").strip()
        job_type_param = request.query_params.get("job_type", "").strip()

        jobs_qs = (
            JobDetail.objects.filter(department=department)
            .select_related("staff__user")
            .order_by("staff__user__first_name", "staff__user__last_name", "id")
        )
        jobs_qs = _apply_job_filters(jobs_qs, status_param, job_type_param)

        if search:
            jobs_qs = jobs_qs.filter(
                Q(staff__user__first_name__icontains=search)
                | Q(staff__user__last_name__icontains=search)
                | Q(staff__user__email__icontains=search)
                | Q(staff__staff_email__icontains=search)
                | Q(employee_id__icontains=search)
                | Q(role__icontains=search)
            )

        staff_list = [_serialize_job_detail_staff(job, request) for job in jobs_qs]

        return Response(
            {
                "status": "1",
                "message": "Department staff fetched successfully",
                "data": {
                    "department_id": department.id,
                    "department_name": department.name,
                    "staff_count": len(staff_list),
                    "staff": staff_list,
                },
            },
            status=status.HTTP_200_OK,
        )
