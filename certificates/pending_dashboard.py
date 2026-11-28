from rest_framework import serializers

from accounts.models import StaffProfile
from accounts.permissions import HasModulePermission
from accounts.serializers.pending_dashboard import PendingTabSerializer, PendingWorkItemSerializer
from accounts.views.pending_dashboard import _BasePendingDashboardAPIView, _date_to_aware_dt
from certificates.models import CertificateRecord
from internship.models import Student


class CertificatePendingDashboardSerializer(serializers.Serializer):
    """Top-level response serializer for Certificate Pending Controls Dashboard."""

    module = serializers.CharField(default="certificate")
    module_label = serializers.CharField(default="Certificates")
    total_pending_count = serializers.IntegerField()
    tab_counts = serializers.DictField(child=serializers.IntegerField())
    tabs = PendingTabSerializer(many=True)
    active_tab = serializers.CharField(default="all")
    items_count = serializers.IntegerField()
    items = PendingWorkItemSerializer(many=True)


class CertificatePendingDashboardAPIView(_BasePendingDashboardAPIView):
    """
    Certificate Module Pending Controls Dashboard API.

    Returns actionable pending certificate items across:
      - students: Completed students/interns who have not been issued a certificate
      - staff: Exited staff/intern-staff who have not been issued an Experience/Employee/Internship certificate
    """

    permission_classes = [_BasePendingDashboardAPIView.permission_classes[0], HasModulePermission]
    required_module = "certificate_pending"
    module_key = "certificate"
    module_label = "Certificates"
    serializer_class = CertificatePendingDashboardSerializer

    TAB_DEFINITIONS = [
        {"key": "students", "label": "Completed Students"},
        {"key": "staff", "label": "Exited Staff"},
    ]

    STUDENT_CERT_TYPES = [
        CertificateRecord.CertificateType.INTERNSHIP,
        CertificateRecord.CertificateType.JOB_TRAINING,
        CertificateRecord.CertificateType.INTERNSHIP_COLLEGE,
    ]
    STAFF_CERT_TYPES = [
        CertificateRecord.CertificateType.EXPERIENCE,
        CertificateRecord.CertificateType.EMPLOYEE,
    ]
    INTERN_STAFF_CERT_TYPES = [
        CertificateRecord.CertificateType.INTERNSHIP,
        CertificateRecord.CertificateType.EXPERIENCE,
    ]
    EXITED_JOB_STATUSES = ["resigned", "terminated", "inactive"]

    def get(self, request):
        tab_items, tab_categories, add_item = self._init_buckets()

        # ── 1. Completed Students without Certificate ────────────────────────
        certified_student_profile_ids = set(
            CertificateRecord.objects.filter(
                user__isnull=False,
                certificate_type__in=self.STUDENT_CERT_TYPES,
            ).values_list("user_id", flat=True)
        )

        completed_students = (
            Student.objects.filter(status="completed")
            .exclude(profile_id__in=certified_student_profile_ids)
            .select_related("profile__user", "center")
            .prefetch_related("enrollments__course")
        )

        for student in completed_students:
            user = student.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip() or user.email
            courses = [
                enrollment.course.title
                for enrollment in student.enrollments.all()
                if getattr(enrollment, "course", None)
            ]
            course_label = ", ".join(courses) if courses else "Course"
            center_name = student.center.name if student.center else None

            add_item(
                tab_key="students",
                work_type="student_certificate_not_issued",
                work_type_label="Student Certificate Pending",
                title=f"{full_name} ({student.student_id}) - Certificate Not Issued",
                description=(
                    f"Completed {course_label}"
                    + (f" at {center_name}" if center_name else "")
                    + " but no certificate has been issued yet."
                ),
                urgency="high",
                record_id=student.id,
                item_id=f"student_cert_pending_{student.id}",
                created_at=student.created_at or _date_to_aware_dt(student.start_date),
                action_url="/certificate/certificates/",
                meta={
                    "student_id": student.student_id,
                    "profile_id": student.profile_id,
                    "full_name": full_name,
                    "email": user.email,
                    "center": center_name,
                    "courses": courses,
                    "start_date": student.start_date.isoformat() if student.start_date else None,
                    "status": student.status,
                },
            )

        # ── 2. Exited Staff & Intern Staff without Certificate ───────────────
        student_profile_ids = set(Student.objects.values_list("profile_id", flat=True))

        certified_staff_map = {}
        for profile_id, cert_type in CertificateRecord.objects.filter(
            user__isnull=False
        ).values_list("user_id", "certificate_type"):
            certified_staff_map.setdefault(profile_id, set()).add(cert_type)

        exited_staff = (
            StaffProfile.objects.filter(job_detail__status__in=self.EXITED_JOB_STATUSES)
            .exclude(id__in=student_profile_ids)
            .select_related("user", "job_detail__department")
        )

        for staff in exited_staff:
            job = staff.job_detail
            issued_types = certified_staff_map.get(staff.id, set())

            if job.job_type == "internship":
                if any(ct in issued_types for ct in self.INTERN_STAFF_CERT_TYPES):
                    continue
                work_type = "exited_intern_staff_no_certificate"
                work_type_label = "Exited Intern Certificate Pending"
                urgency = "high"
                cert_hint = "Internship or Experience certificate"
            else:
                if any(ct in issued_types for ct in self.STAFF_CERT_TYPES):
                    continue
                work_type = "exited_staff_no_certificate"
                work_type_label = "Exited Staff Certificate Pending"
                urgency = "high" if job.status == "resigned" else "medium"
                cert_hint = "Experience or Employee certificate"

            user = staff.user
            full_name = f"{user.first_name} {user.last_name}".strip() or user.email
            dept_name = job.department.name if job.department else None

            add_item(
                tab_key="staff",
                work_type=work_type,
                work_type_label=work_type_label,
                title=f"{full_name} ({job.employee_id}) - {job.get_status_display()}, No Certificate",
                description=(
                    f"Staff member ({job.role}"
                    + (f", {dept_name}" if dept_name else "")
                    + f") has status '{job.status}' and has not been issued an {cert_hint}."
                ),
                urgency=urgency,
                record_id=staff.id,
                item_id=f"staff_cert_pending_{staff.id}",
                created_at=_date_to_aware_dt(job.start_date),
                action_url="/certificate/certificates/",
                meta={
                    "staff_profile_id": staff.id,
                    "employee_id": job.employee_id,
                    "full_name": full_name,
                    "email": user.email,
                    "department": dept_name,
                    "role": job.role,
                    "job_type": job.job_type,
                    "job_status": job.status,
                    "start_date": job.start_date.isoformat() if job.start_date else None,
                },
            )

        return self._build_response(request, tab_items, tab_categories)
