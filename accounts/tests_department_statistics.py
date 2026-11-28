from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser, Department, JobDetail, StaffProfile


class DepartmentStatisticsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.stats_url = "/accounts/departments/statistics/"
        self.admin = CustomUser.objects.create_superuser(
            email="dept_admin@example.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        self._staff_seq = 0

    def _create_staff(
        self,
        first_name,
        last_name,
        department=None,
        role="Engineer",
        job_status="active",
        job_type="full_day",
        salary="50000.00",
    ):
        self._staff_seq += 1
        user = CustomUser.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=f"staff{self._staff_seq}@example.com",
            password="password123",
            is_staff=True,
        )
        profile = StaffProfile.objects.create(
            user=user,
            phone_number=f"99999000{self._staff_seq:02d}",
            staff_email=user.email,
        )
        job = JobDetail.objects.create(
            staff=profile,
            employee_id=f"EMP{self._staff_seq:04d}",
            department=department,
            job_type=job_type,
            role=role,
            salary=Decimal(salary),
            start_date=date(2025, 1, 15),
            status=job_status,
        )
        return job

    def test_requires_authentication(self):
        response = self.client.get(self.stats_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        dept = Department.objects.create(name="HR")
        staff_res = self.client.get(f"/accounts/departments/{dept.id}/staff/")
        self.assertEqual(staff_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_state(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "1")
        self.assertEqual(response.data["departments"], [])
        self.assertEqual(
            response.data["summary"],
            {
                "total_departments": 0,
                "total_staff": 0,
                "unassigned_staff_count": 0,
                "total_active_staff": 0,
                "total_probation_staff": 0,
                "total_inactive_staff": 0,
                "average_staff_per_department": 0.0,
                "largest_department": None,
                "job_type_breakdown": {
                    "full_day": 0,
                    "part_time": 0,
                    "internship": 0,
                    "contract": 0,
                },
            },
        )

    def test_department_statistics_and_previews(self):
        self.client.force_authenticate(user=self.admin)

        dept_dev = Department.objects.create(name="Development")
        dept_hr = Department.objects.create(name="HR")
        dept_empty = Department.objects.create(name="Legal")

        # 5 staff in Development (preview_limit=3 -> +2)
        self._create_staff("Alice", "One", dept_dev, role="Backend Dev", salary="60000.00")
        self._create_staff("Bob", "Two", dept_dev, role="Frontend Dev", salary="50000.00")
        self._create_staff("Charlie", "Three", dept_dev, role="QA", job_status="probation", job_type="contract", salary="40000.00")
        self._create_staff("David", "Four", dept_dev, role="DevOps", job_status="resigned", job_type="full_day", salary="70000.00")
        self._create_staff("Emma", "Five", dept_dev, role="Intern", job_status="active", job_type="internship", salary="15000.00")

        # 2 staff in HR (<= preview_limit -> no +N)
        self._create_staff("John", "Doe", dept_hr, role="HR Manager", salary="45000.00")
        self._create_staff("Sarah", "Lee", dept_hr, role="Recruiter", job_type="part_time", salary="25000.00")

        # 1 unassigned staff
        self._create_staff("Unassigned", "Person", None, role="Consultant", salary="30000.00")

        response = self.client.get(self.stats_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        summary = response.data["summary"]
        self.assertEqual(summary["total_departments"], 3)
        self.assertEqual(summary["total_staff"], 7)
        self.assertEqual(summary["unassigned_staff_count"], 1)
        self.assertEqual(summary["total_active_staff"], 5)
        self.assertEqual(summary["total_probation_staff"], 1)
        self.assertEqual(summary["total_inactive_staff"], 1)
        self.assertEqual(summary["average_staff_per_department"], 2.33)
        self.assertEqual(
            summary["largest_department"],
            {
                "department_id": dept_dev.id,
                "department_name": "Development",
                "staff_count": 5,
            },
        )
        self.assertEqual(
            summary["job_type_breakdown"],
            {"full_day": 4, "part_time": 1, "internship": 1, "contract": 1},
        )

        # Ordered by department name: Development, HR, Legal
        depts = {d["department_name"]: d for d in response.data["departments"]}
        self.assertEqual(list(depts.keys()), ["Development", "HR", "Legal"])

        dev = depts["Development"]
        self.assertEqual(dev["staff_count"], 5)
        self.assertEqual(dev["staff_percentage"], 71.43)
        self.assertNotIn("staff_preview", dev)
        self.assertNotIn("staff_list", dev)
        self.assertEqual(dev["staff_preview_names"], ["Alice One", "Bob Two", "Charlie Three"])
        self.assertEqual(dev["remaining_staff_count"], 2)
        self.assertEqual(dev["staff_preview_text"], "Alice One, Bob Two, Charlie Three, +2")
        self.assertTrue(dev["has_more_staff"])
        self.assertEqual(dev["full_staff_url"], f"/accounts/departments/{dept_dev.id}/staff/")
        self.assertEqual(dev["total_salary"], "235000.00")
        self.assertEqual(dev["average_salary"], "47000.00")
        self.assertEqual(dev["roles"], ["Backend Dev", "DevOps", "Frontend Dev", "Intern", "QA"])

        hr = depts["HR"]
        self.assertEqual(hr["staff_count"], 2)
        self.assertEqual(hr["remaining_staff_count"], 0)
        self.assertFalse(hr["has_more_staff"])
        self.assertEqual(hr["staff_preview_text"], "John Doe, Sarah Lee")

        legal = depts["Legal"]
        self.assertEqual(legal["staff_count"], 0)
        self.assertEqual(legal["staff_preview_names"], [])
        self.assertEqual(legal["staff_preview_text"], "")
        self.assertEqual(legal["total_salary"], "0.00")
        self.assertEqual(legal["average_salary"], "0.00")

    def test_statistics_query_params(self):
        self.client.force_authenticate(user=self.admin)
        dept_dev = Department.objects.create(name="Development")
        dept_hr = Department.objects.create(name="HR")

        self._create_staff("Alice", "One", dept_dev, job_status="active", job_type="full_day")
        self._create_staff("Bob", "Two", dept_dev, job_status="active", job_type="internship")
        self._create_staff("Charlie", "Three", dept_dev, job_status="resigned", job_type="full_day")
        self._create_staff("John", "Doe", dept_hr, job_status="active", job_type="full_day")

        res = self.client.get(
            self.stats_url,
            {
                "search": "dev",
                "status": "active",
                "preview_limit": "1",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["summary"]["total_departments"], 1)
        self.assertEqual(res.data["summary"]["total_staff"], 2)

        dev = res.data["departments"][0]
        self.assertEqual(dev["department_name"], "Development")
        self.assertEqual(dev["staff_preview_names"], ["Alice One"])
        self.assertEqual(dev["staff_preview_text"], "Alice One, +1")
        self.assertNotIn("staff_preview", dev)
        self.assertNotIn("staff_list", dev)

    def test_department_staff_list_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        dept = Department.objects.create(name="Finance")
        self._create_staff("Robert", "King", dept, role="Accountant", job_status="active", job_type="full_day")
        self._create_staff("James", "Bond", dept, role="Auditor", job_status="probation", job_type="contract")

        url = f"/accounts/departments/{dept.id}/staff/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["department_name"], "Finance")
        self.assertEqual(res.data["data"]["staff_count"], 2)
        self.assertEqual([s["full_name"] for s in res.data["data"]["staff"]], ["James Bond", "Robert King"])

        filtered = self.client.get(url, {"search": "Accountant", "status": "active"})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["data"]["staff_count"], 1)
        self.assertEqual(filtered.data["data"]["staff"][0]["full_name"], "Robert King")

        missing = self.client.get("/accounts/departments/999999/staff/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)
