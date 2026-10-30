from datetime import date
from decimal import Decimal
import shutil
import tempfile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser, Department, StaffProfile
from internship.models import (
    Batch,
    Center,
    Course,
    Faculty,
    Student,
    StudentCourseEnrollment,
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CenterReportsFilterTests(TestCase):
    """
    Automated test suite to verify:
    1. GET /internship/report/center/ summary mode (all centers, distinct counts, no join duplication).
    2. GET /internship/report/center/?view=students (all centers student list).
    3. Status filter: active, inactive, completed.
    4. Course filter: course=<id>.
    5. Faculty filter: faculty=<id> via StudentCourseEnrollment -> Batch -> Faculty.
    6. Enrollment date filter: date_from, date_to, invalid date formats, date_from > date_to.
    7. Combined filters (AND condition).
    8. GET /internship/report/center/<id>/ detail report with filters.
    9. Duplicate student prevention when student has multiple enrollments.
    10. Behavior of students without enrollments.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        # Admin / Auth User
        cls.auth_user = CustomUser.objects.create_user(
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="password123",
        )

        cls.dept = Department.objects.create(name="Tech Dept")

        # Two Centers
        cls.center_a = Center.objects.create(name="Center Alpha", country_name="India", state_name="Kerala")
        cls.center_b = Center.objects.create(name="Center Beta", country_name="India", state_name="Karnataka")

        # Two Courses
        cls.course_1 = Course.objects.create(
            title="Python Full Stack",
            department=cls.dept,
            total_fee=Decimal("20000.00"),
        )
        cls.course_2 = Course.objects.create(
            title="Data Science",
            department=cls.dept,
            total_fee=Decimal("30000.00"),
        )

        # Two Faculties
        cls.fac_user_1 = CustomUser.objects.create_user(
            first_name="Alice",
            last_name="Prof",
            email="alice@test.com",
            password="password123",
        )
        cls.fac_profile_1 = StaffProfile.objects.create(user=cls.fac_user_1)
        cls.faculty_1 = Faculty.objects.create(user=cls.fac_profile_1)

        cls.fac_user_2 = CustomUser.objects.create_user(
            first_name="Bob",
            last_name="Instructor",
            email="bob@test.com",
            password="password123",
        )
        cls.fac_profile_2 = StaffProfile.objects.create(user=cls.fac_user_2)
        cls.faculty_2 = Faculty.objects.create(user=cls.fac_profile_2)

        # Two Batches
        cls.batch_1 = Batch.objects.create(
            batch_number="BATCH-001",
            course=cls.course_1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        cls.batch_1.faculties.add(cls.faculty_1)

        cls.batch_2 = Batch.objects.create(
            batch_number="BATCH-002",
            course=cls.course_2,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 7, 31),
        )
        cls.batch_2.faculties.add(cls.faculty_2)

        # Helper to create student
        def make_student(std_id, fname, lname, email, center, status_val):
            u = CustomUser.objects.create_user(
                first_name=fname,
                last_name=lname,
                email=email,
                password="password123",
            )
            p = StaffProfile.objects.create(user=u)
            return Student.objects.create(
                student_id=std_id,
                profile=p,
                center=center,
                status=status_val,
                start_date=date(2026, 1, 15),
            )

        # Students in Center Alpha:
        # Student 1: Active, Course 1, Batch 1 (Faculty 1), Enrollment date: 2026-02-10
        cls.student_1 = make_student("STD-001", "John", "Doe", "john@test.com", cls.center_a, "active")
        cls.enr_1 = StudentCourseEnrollment.objects.create(
            student=cls.student_1,
            course=cls.course_1,
            batch=cls.batch_1,
            payment_plan_type="custom_installment",
            custom_installments=1,
        )
        StudentCourseEnrollment.objects.filter(pk=cls.enr_1.pk).update(enrollment_date=date(2026, 2, 10))

        # Student 2: Inactive, Course 1, Batch 1 (Faculty 1), Enrollment date: 2026-03-15
        cls.student_2 = make_student("STD-002", "Jane", "Smith", "jane@test.com", cls.center_a, "inactive")
        cls.enr_2 = StudentCourseEnrollment.objects.create(
            student=cls.student_2,
            course=cls.course_1,
            batch=cls.batch_1,
            payment_plan_type="custom_installment",
            custom_installments=1,
        )
        StudentCourseEnrollment.objects.filter(pk=cls.enr_2.pk).update(enrollment_date=date(2026, 3, 15))

        # Student 3: Completed, Course 2, Batch 2 (Faculty 2), Enrollment date: 2026-04-20
        cls.student_3 = make_student("STD-003", "Charlie", "Brown", "charlie@test.com", cls.center_a, "completed")
        cls.enr_3 = StudentCourseEnrollment.objects.create(
            student=cls.student_3,
            course=cls.course_2,
            batch=cls.batch_2,
            payment_plan_type="custom_installment",
            custom_installments=1,
        )
        StudentCourseEnrollment.objects.filter(pk=cls.enr_3.pk).update(enrollment_date=date(2026, 4, 20))

        # Student 4: Active, Multiple enrollments (Course 1 & Course 2), Enrollment dates: 2026-01-05 & 2026-05-01
        cls.student_4 = make_student("STD-004", "Daisy", "Miller", "daisy@test.com", cls.center_a, "active")
        cls.enr_4a = StudentCourseEnrollment.objects.create(
            student=cls.student_4,
            course=cls.course_1,
            batch=cls.batch_1,
            payment_plan_type="custom_installment",
            custom_installments=1,
        )
        StudentCourseEnrollment.objects.filter(pk=cls.enr_4a.pk).update(enrollment_date=date(2026, 1, 5))

        cls.enr_4b = StudentCourseEnrollment.objects.create(
            student=cls.student_4,
            course=cls.course_2,
            batch=cls.batch_2,
            payment_plan_type="custom_installment",
            custom_installments=1,
        )
        StudentCourseEnrollment.objects.filter(pk=cls.enr_4b.pk).update(enrollment_date=date(2026, 5, 1))

        # Student 5: Active, Center Alpha, NO enrollments
        cls.student_5 = make_student("STD-005", "Evan", "Wright", "evan@test.com", cls.center_a, "active")

        # Student 6: Active, Center Beta, Course 2, Batch 2 (Faculty 2), Enrollment date: 2026-06-10
        cls.student_6 = make_student("STD-006", "Fiona", "Gallagher", "fiona@test.com", cls.center_b, "active")
        cls.enr_6 = StudentCourseEnrollment.objects.create(
            student=cls.student_6,
            course=cls.course_2,
            batch=cls.batch_2,
            payment_plan_type="custom_installment",
            custom_installments=1,
        )
        StudentCourseEnrollment.objects.filter(pk=cls.enr_6.pk).update(enrollment_date=date(2026, 6, 10))

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.auth_user)

    def test_01_all_centers_summary(self):
        """GET /internship/report/center/ returns summary counts for all centers."""
        response = self.client.get("/internship/report/center/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Find Center Alpha
        data_a = next(c for c in response.data if c["id"] == self.center_a.id)
        # Center Alpha has 5 students: 3 active (1, 4, 5), 1 inactive (2), 1 completed (3)
        self.assertEqual(data_a["total_students"], 5)
        self.assertEqual(data_a["active_students"], 3)
        self.assertEqual(data_a["inactive_students"], 1)
        self.assertEqual(data_a["completed_students"], 1)
        # Distinct courses enrolled by students in Center Alpha: Course 1 and Course 2 -> 2
        self.assertEqual(data_a["total_courses"], 2)
        # Distinct faculties in Center Alpha: Faculty 1 and Faculty 2 -> 2
        self.assertEqual(data_a["faculties"], 2)

        # Center Beta has 1 active student (6)
        data_b = next(c for c in response.data if c["id"] == self.center_b.id)
        self.assertEqual(data_b["total_students"], 1)
        self.assertEqual(data_b["active_students"], 1)
        self.assertEqual(data_b["inactive_students"], 0)
        self.assertEqual(data_b["completed_students"], 0)
        self.assertEqual(data_b["total_courses"], 1)
        self.assertEqual(data_b["faculties"], 1)

    def test_02_all_centers_view_students_no_duplicates(self):
        """GET /internship/report/center/?view=students returns all students without duplicates."""
        response = self.client.get("/internship/report/center/?view=students")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["view"], "students")
        # Total students across all centers is 6
        self.assertEqual(response.data["count"], 6)
        self.assertEqual(len(response.data["results"]), 6)

        # Check unique IDs in results
        returned_ids = [s["student_id"] for s in response.data["results"]]
        self.assertEqual(len(returned_ids), len(set(returned_ids)))

        # Verify fields in record
        sample = next(s for s in response.data["results"] if s["student_id"] == "STD-001")
        self.assertEqual(sample["name"], "John Doe")
        self.assertEqual(sample["email"], "john@test.com")
        self.assertEqual(sample["center"], "Center Alpha")
        self.assertEqual(sample["course"], "Python Full Stack")
        self.assertEqual(sample["batch"], "BATCH-001")
        self.assertEqual(sample["status"], "active")

    def test_03_status_filters(self):
        """GET /internship/report/center/?view=students&status=... filters by status."""
        # Active: Students 1, 4, 5 in Alpha, 6 in Beta -> 4 active
        resp_active = self.client.get("/internship/report/center/?view=students&status=active")
        self.assertEqual(resp_active.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_active.data["count"], 4)
        for s in resp_active.data["results"]:
            self.assertEqual(s["status"], "active")

        # Inactive: Student 2 -> 1 inactive
        resp_inactive = self.client.get("/internship/report/center/?view=students&status=inactive")
        self.assertEqual(resp_inactive.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_inactive.data["count"], 1)
        self.assertEqual(resp_inactive.data["results"][0]["student_id"], "STD-002")

        # Completed: Student 3 -> 1 completed
        resp_completed = self.client.get("/internship/report/center/?view=students&status=completed")
        self.assertEqual(resp_completed.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_completed.data["count"], 1)
        self.assertEqual(resp_completed.data["results"][0]["student_id"], "STD-003")

    def test_04_course_filter(self):
        """GET /internship/report/center/?view=students&course=<id> filters by enrolled course."""
        # Course 1 has Students 1, 2, 4
        response = self.client.get(f"/internship/report/center/?view=students&course={self.course_1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        returned_ids = {s["student_id"] for s in response.data["results"]}
        self.assertEqual(returned_ids, {"STD-001", "STD-002", "STD-004"})

    def test_05_faculty_filter(self):
        """GET /internship/report/center/?view=students&faculty=<id> filters by faculty via Batch."""
        # Faculty 1 teaches Batch 1 (Students 1, 2, 4)
        resp1 = self.client.get(f"/internship/report/center/?view=students&faculty={self.faculty_1.id}")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp1.data["count"], 3)
        self.assertEqual({s["student_id"] for s in resp1.data["results"]}, {"STD-001", "STD-002", "STD-004"})

        # Faculty 2 teaches Batch 2 (Students 3, 4, 6)
        resp2 = self.client.get(f"/internship/report/center/?view=students&faculty={self.faculty_2.id}")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data["count"], 3)
        self.assertEqual({s["student_id"] for s in resp2.data["results"]}, {"STD-003", "STD-004", "STD-006"})

    def test_06_enrollment_date_filter_range(self):
        """GET /internship/report/center/?view=students&date_from=...&date_to=..."""
        # Enrollments:
        # STD-004: 2026-01-05 & 2026-05-01
        # STD-001: 2026-02-10
        # STD-002: 2026-03-15
        # STD-003: 2026-04-20
        # STD-006: 2026-06-10

        # Range 2026-02-01 to 2026-03-31 -> STD-001 (Feb 10) and STD-002 (Mar 15)
        response = self.client.get("/internship/report/center/?view=students&date_from=2026-02-01&date_to=2026-03-31")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual({s["student_id"] for s in response.data["results"]}, {"STD-001", "STD-002"})

    def test_07_enrollment_date_only_from_and_only_to(self):
        """Test only date_from and only date_to."""
        # Only date_from=2026-04-01 -> STD-003 (Apr 20), STD-004 (May 01), STD-006 (Jun 10) -> 3 students
        resp_from = self.client.get("/internship/report/center/?view=students&date_from=2026-04-01")
        self.assertEqual(resp_from.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_from.data["count"], 3)
        self.assertEqual({s["student_id"] for s in resp_from.data["results"]}, {"STD-003", "STD-004", "STD-006"})

        # Only date_to=2026-02-15 -> STD-004 (Jan 05), STD-001 (Feb 10) -> 2 students
        resp_to = self.client.get("/internship/report/center/?view=students&date_to=2026-02-15")
        self.assertEqual(resp_to.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_to.data["count"], 2)
        self.assertEqual({s["student_id"] for s in resp_to.data["results"]}, {"STD-001", "STD-004"})

    def test_08_date_from_later_than_date_to(self):
        """When date_from > date_to, returns empty results without crashing."""
        response = self.client.get("/internship/report/center/?view=students&date_from=2026-12-01&date_to=2026-01-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_09_invalid_date_formats(self):
        """Invalid date format testing."""
        response = self.client.get("/internship/report/center/?view=students&date_from=invalid-date")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date_from format", response.data["detail"])

        resp_to = self.client.get("/internship/report/center/?view=students&date_to=not-a-date")
        self.assertEqual(resp_to.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date_to format", resp_to.data["detail"])

    def test_10_combined_filters(self):
        """Combined filters: status=active&course=1&faculty=1&date_from=2026-01-01&date_to=2026-02-28"""
        # Active students enrolled in Course 1, Faculty 1, between 2026-01-01 and 2026-02-28:
        # Candidates:
        # STD-001: active, Course 1, Faculty 1, date 2026-02-10 -> Matches
        # STD-002: inactive -> Excluded by status
        # STD-004: active, Course 1, Faculty 1, date 2026-01-05 -> Matches
        url = (
            f"/internship/report/center/?view=students&status=active&course={self.course_1.id}"
            f"&faculty={self.faculty_1.id}&date_from=2026-01-01&date_to=2026-02-28"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual({s["student_id"] for s in response.data["results"]}, {"STD-001", "STD-004"})

    def test_11_specific_center_report_unfiltered(self):
        """GET /internship/report/center/<id>/ returns center details and categorized students."""
        response = self.client.get(f"/internship/report/center/{self.center_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.center_a.id)
        self.assertEqual(response.data["name"], "Center Alpha")

        # Active students in Center A: STD-001, STD-004, STD-005
        active_ids = {s["student_id"] for s in response.data["active_students"]}
        self.assertEqual(active_ids, {"STD-001", "STD-004", "STD-005"})

        # Inactive students in Center A: STD-002
        inactive_ids = {s["student_id"] for s in response.data["inactive_students"]}
        self.assertEqual(inactive_ids, {"STD-002"})

        # Completed students in Center A: STD-003
        completed_ids = {s["student_id"] for s in response.data["completed_students"]}
        self.assertEqual(completed_ids, {"STD-003"})

        # Courses in Center A: Course 1 & Course 2
        course_titles = {c["title"] for c in response.data["courses"]}
        self.assertEqual(course_titles, {"Python Full Stack", "Data Science"})

        # Faculties in Center A: Faculty 1 & Faculty 2
        fac_names = {f["name"] for f in response.data["faculties"]}
        self.assertEqual(fac_names, {"Alice Prof", "Bob Instructor"})

    def test_12_specific_center_report_with_filters(self):
        """GET /internship/report/center/<id>/?status=active and other filters."""
        # status=active
        resp1 = self.client.get(f"/internship/report/center/{self.center_a.id}/?status=active")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp1.data["active_students"]), 3)
        self.assertEqual(len(resp1.data["inactive_students"]), 0)
        self.assertEqual(len(resp1.data["completed_students"]), 0)

        # status=completed&course=2
        resp2 = self.client.get(f"/internship/report/center/{self.center_a.id}/?status=completed&course={self.course_2.id}")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp2.data["completed_students"]), 1)
        self.assertEqual(resp2.data["completed_students"][0]["student_id"], "STD-003")

        # faculty=1&date_from=2026-01-01&date_to=2026-10-30
        resp3 = self.client.get(
            f"/internship/report/center/{self.center_a.id}/?faculty={self.faculty_1.id}&date_from=2026-01-01&date_to=2026-10-30"
        )
        self.assertEqual(resp3.status_code, status.HTTP_200_OK)
        # Active: STD-001, STD-004 (both in faculty 1)
        self.assertEqual({s["student_id"] for s in resp3.data["active_students"]}, {"STD-001", "STD-004"})
        # Inactive: STD-002 (in faculty 1)
        self.assertEqual({s["student_id"] for s in resp3.data["inactive_students"]}, {"STD-002"})
        # Completed: empty (STD-003 is in faculty 2)
        self.assertEqual(len(resp3.data["completed_students"]), 0)

    def test_13_student_without_enrollments_behavior(self):
        """Ensure students without enrollments have null course and batch and do not crash."""
        response = self.client.get("/internship/report/center/?view=students&status=active")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        evan = next(s for s in response.data["results"] if s["student_id"] == "STD-005")
        self.assertEqual(evan["name"], "Evan Wright")
        self.assertIsNone(evan["course"])
        self.assertIsNone(evan["batch"])

    def test_14_center_filter_view_students(self):
        """GET /internship/report/center/?view=students&center=<id> filters by center."""
        response = self.client.get(f"/internship/report/center/?view=students&center={self.center_b.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["student_id"], "STD-006")

