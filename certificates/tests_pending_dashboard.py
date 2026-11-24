from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser, Department, JobDetail, StaffProfile
from certificates.models import CertificateRecord
from internship.models import Student


class CertificatePendingDashboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        self.client.force_authenticate(user=self.admin_user)

        self.dept = Department.objects.create(name="Engineering")

        # 1. Completed student without certificate -> should appear
        self.student_user = CustomUser.objects.create_user(
            email="student1@example.com",
            password="password123",
            first_name="Asha",
            last_name="Nair",
        )
        self.student_profile = StaffProfile.objects.create(user=self.student_user)
        self.student = Student.objects.create(
            profile=self.student_profile,
            student_id="STD-101",
            start_date=date(2026, 1, 10),
            status="completed",
        )

        # 2. Resigned staff without certificate -> should appear (high urgency)
        self.resigned_user = CustomUser.objects.create_user(
            email="staff1@example.com",
            password="password123",
            first_name="Rahul",
            last_name="Menon",
        )
        self.resigned_profile = StaffProfile.objects.create(user=self.resigned_user)
        JobDetail.objects.create(
            staff=self.resigned_profile,
            employee_id="EMP-201",
            department=self.dept,
            job_type="full_day",
            role="Developer",
            salary=Decimal("30000.00"),
            start_date=date(2025, 1, 1),
            status="resigned",
        )

        # 3. Terminated intern staff without certificate -> should appear (high urgency)
        self.intern_user = CustomUser.objects.create_user(
            email="intern1@example.com",
            password="password123",
            first_name="Meera",
            last_name="Das",
        )
        self.intern_profile = StaffProfile.objects.create(user=self.intern_user)
        JobDetail.objects.create(
            staff=self.intern_profile,
            employee_id="INT-301",
            department=self.dept,
            job_type="internship",
            role="Backend Intern",
            salary=Decimal("5000.00"),
            start_date=date(2025, 6, 1),
            status="terminated",
        )

        # 4. Active staff -> should NOT appear
        self.active_user = CustomUser.objects.create_user(
            email="active@example.com",
            password="password123",
            first_name="Active",
            last_name="Staff",
        )
        self.active_profile = StaffProfile.objects.create(user=self.active_user)
        JobDetail.objects.create(
            staff=self.active_profile,
            employee_id="EMP-999",
            department=self.dept,
            job_type="full_day",
            role="QA",
            salary=Decimal("25000.00"),
            start_date=date(2025, 3, 1),
            status="active",
        )

    def test_pending_dashboard_returns_students_and_staff(self):
        response = self.client.get("/certificate/pending-dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["module"], "certificate")
        self.assertEqual(response.data["total_pending_count"], 3)
        self.assertEqual(response.data["tab_counts"], {"students": 1, "staff": 2})

        work_types = {item["work_type"] for item in response.data["items"]}
        self.assertEqual(
            work_types,
            {
                "student_certificate_not_issued",
                "exited_staff_no_certificate",
                "exited_intern_staff_no_certificate",
            },
        )

    def test_tab_and_search_filters(self):
        resp_students = self.client.get("/certificate/pending-dashboard/?tab=students")
        self.assertEqual(resp_students.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_students.data["items_count"], 1)
        self.assertEqual(resp_students.data["items"][0]["meta"]["student_id"], "STD-101")

        resp_search = self.client.get("/certificate/pending-dashboard/?search=EMP-201")
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_search.data["items_count"], 1)
        self.assertEqual(resp_search.data["items"][0]["meta"]["employee_id"], "EMP-201")

    def test_items_clear_when_certificates_issued(self):
        CertificateRecord.objects.create(
            user=self.student_profile,
            certificate_type=CertificateRecord.CertificateType.INTERNSHIP,
            full_name="Asha Nair",
        )
        CertificateRecord.objects.create(
            user=self.resigned_profile,
            certificate_type=CertificateRecord.CertificateType.EXPERIENCE,
            full_name="Rahul Menon",
        )

        response = self.client.get("/certificate/pending-dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_pending_count"], 1)
        self.assertEqual(response.data["tab_counts"], {"students": 0, "staff": 1})
        self.assertEqual(
            response.data["items"][0]["work_type"],
            "exited_intern_staff_no_certificate",
        )
