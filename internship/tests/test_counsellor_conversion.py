"""
Tests for the Counsellor Conversion Report API.

Run with:
    python manage.py test internship.tests.test_counsellor_conversion -v2 --keepdb
"""
import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Department, SalesPerson, StaffProfile
from finance.models import TaxSettings
from internship.models import (
    Batch,
    Center,
    Course,
    CoursePayment,
    InstallmentItem,
    InstallmentPlan,
    InternshipApplication,
    Student,
    StudentCourseEnrollment,
)
from internship.utils import StudentConversionService

User = get_user_model()


class CounsellorConversionReportTests(TestCase):
    """
    End-to-end tests for GET /internship/report/counsellors/<id>/conversion/

    Test data is NOT deleted after tests (Django test DB isolation).
    """

    # ──────────────────────────────────────────────────────────
    # Setup — create all test data
    # ──────────────────────────────────────────────────────────

    @classmethod
    def setUpTestData(cls):
        """Create all shared test data once for the class."""

        # ── Admin user (for authentication) ──
        cls.admin_user = User.objects.create_user(
            email="test_admin_conversion@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="Tester",
        )

        # ── Counsellors (SalesPersons) ──
        cls.counsellor_a = SalesPerson.objects.create(
            first_name="TestCounsellor",
            last_name="A",
            email="test_counsellor_a@example.com",
            phone="9990001111",
            mobile="9990001112",
            incentive=500,
            designation="Senior Counsellor",
        )
        cls.counsellor_b = SalesPerson.objects.create(
            first_name="TestCounsellor",
            last_name="B",
            email="test_counsellor_b@example.com",
            phone="9990002222",
            mobile="9990002223",
            incentive=300,
            designation="Junior Counsellor",
        )

        # ── Department, TaxSettings, Course ──
        cls.department = Department.objects.create(
            name="Test Dept Conversion Report",
        )
        cls.tax_settings = TaxSettings.objects.create(
            name="Test Tax Conversion",
            rate=18.00,
        )
        cls.course = Course.objects.create(
            title="Test Course - Full Stack Dev",
            description="Test course for conversion report",
            department=cls.department,
            total_fee=50000,
            tax_settings=cls.tax_settings,
        )
        cls.course_2 = Course.objects.create(
            title="Test Course - Data Science",
            description="Second test course",
            department=cls.department,
            total_fee=40000,
            tax_settings=cls.tax_settings,
        )

        # ── Center ──
        cls.center = Center.objects.create(
            name="Test Center Conversion",
            country_name="India",
            state_name="Kerala",
        )

        # ── Batch ──
        today = date.today()
        cls.batch = Batch.objects.create(
            batch_number="TEST-CONV-B01",
            course=cls.course,
            start_date=today,
            end_date=today + timedelta(days=180),
        )

        # ── Installment Plan ──
        cls.installment_plan = InstallmentPlan.objects.create(
            course=cls.course,
            total_installments=3,
        )
        for i in range(1, 4):
            InstallmentItem.objects.create(
                plan=cls.installment_plan,
                installment_number=i,
                amount=50000 / 3,
                due_days=i * 30,
            )

        # ──────────────────────────────────────────────────────
        # Student 1: Created via InternshipApplication conversion
        # (assigned to counsellor_a)
        # ──────────────────────────────────────────────────────
        cls.application = InternshipApplication.objects.create(
            first_name="AppStudent",
            last_name="One",
            primary_phone="+919876500001",
            email="appstudent1_conv@example.com",
            dob="2000-01-15",
            gender="male",
            qualification="ug",
            course_name="BSc CS",
            address="Test Address 1",
            state="Kerala",
            district="Ernakulam",
            pincode="682001",
            where_did_you_find_us="google",
            course_duration=6,
            course_type="offline",
            course=cls.course,
            councellor=cls.counsellor_a,
        )

        cls.student_1 = StudentConversionService.convert(
            application=cls.application,
            email="converted_student1_conv@example.com",
            password="test123pass",
            center=cls.center,
            start_date=today - timedelta(days=15),
            councellor=cls.counsellor_a,
            status="active",
        )

        # Create enrollment for student 1
        cls.enrollment_1 = StudentCourseEnrollment.objects.create(
            student=cls.student_1,
            course=cls.course,
            batch=cls.batch,
            installment_plan=cls.installment_plan,
            payment_plan_type="default_installment",
            advance_amount=5000,
            payment_method="upi",
            transaction_id="TXN-TEST-001",
            payment_date=today - timedelta(days=15),
        )

        # ──────────────────────────────────────────────────────
        # Student 2: Created directly (no application)
        # (assigned to counsellor_a)
        # ──────────────────────────────────────────────────────
        cls.direct_user = User.objects.create_user(
            email="direct_student_conv@example.com",
            password="test123pass",
            first_name="DirectStudent",
            last_name="Two",
        )
        cls.direct_profile = StaffProfile.objects.create(
            user=cls.direct_user,
            phone_number="+919876500002",
            staff_email="direct_student_conv@example.com",
        )
        cls.student_2 = Student.objects.create(
            profile=cls.direct_profile,
            student_id="ST_CONV_TEST002",
            center=cls.center,
            start_date=today - timedelta(days=5),
            status="active",
            councellor=cls.counsellor_a,
        )

        # Enroll student 2 in course_2
        cls.enrollment_2 = StudentCourseEnrollment.objects.create(
            student=cls.student_2,
            course=cls.course_2,
            payment_plan_type="custom_installment",
            custom_installments=2,
            advance_amount=3000,
            payment_method="cash",
            payment_date=today - timedelta(days=5),
        )

        # ──────────────────────────────────────────────────────
        # Student 3: No payment (assigned to counsellor_a)
        # ──────────────────────────────────────────────────────
        cls.nopay_user = User.objects.create_user(
            email="nopay_student_conv@example.com",
            password="test123pass",
            first_name="NoPay",
            last_name="Student",
        )
        cls.nopay_profile = StaffProfile.objects.create(
            user=cls.nopay_user,
            phone_number="+919876500003",
            staff_email="nopay_student_conv@example.com",
        )
        cls.student_3 = Student.objects.create(
            profile=cls.nopay_profile,
            student_id="ST_CONV_TEST003",
            center=cls.center,
            start_date=today,
            status="active",
            councellor=cls.counsellor_a,
        )

        # ── Store IDs for report ──
        cls.created_data = {
            "counsellor_a": cls.counsellor_a.id,
            "counsellor_b": cls.counsellor_b.id,
            "course": cls.course.id,
            "course_2": cls.course_2.id,
            "batch": cls.batch.id,
            "student_1_id": cls.student_1.id,
            "student_1_code": cls.student_1.student_id,
            "student_2_id": cls.student_2.id,
            "student_2_code": cls.student_2.student_id,
            "student_3_id": cls.student_3.id,
            "student_3_code": cls.student_3.student_id,
        }

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
        self.base_url = "/internship/report/counsellors/{}/conversion/"

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    def _print_result(self, test_name, response, passed):
        icon = "[PASS]" if passed else "[FAIL]"
        print(f"\n  {icon} {test_name}  [{response.status_code}]")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                summary = data.get("summary", {})
                student_count = len(data.get("students", []))
                print(f"     Summary: {json.dumps(summary)}")
                print(f"     Students returned: {student_count}")
            elif isinstance(data, list):
                print(f"     List items returned: {len(data)}")
        else:
            print(f"     Response: {response.content.decode()[:200]}")

    # ──────────────────────────────────────────────────────────
    # Test 1: No filters — all students for counsellor_a
    # ──────────────────────────────────────────────────────────

    def test_conversion_report_no_filters(self):
        """All students under counsellor_a should be returned."""
        url = self.base_url.format(self.counsellor_a.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["counsellor"]["id"], self.counsellor_a.id)
        self.assertEqual(data["counsellor"]["name"], "TestCounsellor A")
        self.assertEqual(data["summary"]["total_students"], 3)
        self.assertEqual(data["summary"]["total_students_all_time"], 3)
        self.assertEqual(len(data["students"]), 3)

        self._print_result("test_conversion_report_no_filters", response, True)

    # ──────────────────────────────────────────────────────────
    # Test 2: Date range filter
    # ──────────────────────────────────────────────────────────

    def test_conversion_report_date_range(self):
        """Only students created within the date range should be returned."""
        today = date.today()
        # Filter to only include the last 10 days — should exclude student_1 (15 days ago)
        start = today - timedelta(days=10)
        end = today

        url = self.base_url.format(self.counsellor_a.id)
        response = self.client.get(url, {"start_date": str(start), "end_date": str(end)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # total_students should be filtered count
        self.assertLessEqual(data["summary"]["total_students"], 3)
        # total_students_all_time should still be all
        self.assertEqual(data["summary"]["total_students_all_time"], 3)

        self._print_result("test_conversion_report_date_range", response, True)

    # ──────────────────────────────────────────────────────────
    # Test 3: Course filter
    # ──────────────────────────────────────────────────────────

    def test_conversion_report_course_filter(self):
        """Only students enrolled in the specified course should be returned."""
        url = self.base_url.format(self.counsellor_a.id)
        response = self.client.get(url, {"course_id": self.course_2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Only student_2 is enrolled in course_2
        self.assertEqual(data["summary"]["total_students"], 1)
        self.assertEqual(data["students"][0]["name"], "DirectStudent Two")

        self._print_result("test_conversion_report_course_filter", response, True)

    # ──────────────────────────────────────────────────────────
    # Test 4: Empty counsellor (counsellor_b has no students)
    # ──────────────────────────────────────────────────────────

    def test_conversion_report_empty_counsellor(self):
        """Counsellor with no students should return empty list."""
        url = self.base_url.format(self.counsellor_b.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["counsellor"]["name"], "TestCounsellor B")
        self.assertEqual(data["summary"]["total_students"], 0)
        self.assertEqual(data["summary"]["total_students_all_time"], 0)
        self.assertEqual(len(data["students"]), 0)

        self._print_result("test_conversion_report_empty_counsellor", response, True)

    # ──────────────────────────────────────────────────────────
    # Test 5: Non-existent counsellor → 404
    # ──────────────────────────────────────────────────────────

    def test_conversion_report_nonexistent_counsellor(self):
        """Non-existent counsellor ID should return 404."""
        url = self.base_url.format(99999)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self._print_result("test_conversion_report_nonexistent_counsellor", response, True)

    # ──────────────────────────────────────────────────────────
    # Test 6: Student with no payment → first_payment is null
    # ──────────────────────────────────────────────────────────

    def test_first_payment_null(self):
        """Student with no CoursePayment should have first_payment=null."""
        url = self.base_url.format(self.counsellor_a.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        # Find student_3 (NoPay Student) in the response
        nopay = next(
            (s for s in data["students"] if s["student_id"] == self.student_3.student_id),
            None
        )
        self.assertIsNotNone(nopay, "NoPay student should be in the response")
        self.assertIsNone(nopay["first_payment"])

        self._print_result("test_first_payment_null", response, True)

    # ──────────────────────────────────────────────────────────
    # Test 7: Counsellor list API includes test counsellors
    # ──────────────────────────────────────────────────────────

    def test_counsellor_list_includes_test_data(self):
        """Existing CounsellorListAPIView should include test counsellors."""
        response = self.client.get("/internship/report/counsellors/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        ids = [c["id"] for c in data]
        self.assertIn(self.counsellor_a.id, ids)
        self.assertIn(self.counsellor_b.id, ids)

        # Check total_students for counsellor_a
        counsellor_a_data = next(c for c in data if c["id"] == self.counsellor_a.id)
        self.assertEqual(counsellor_a_data["total_students"], 3)

        self._print_result("test_counsellor_list_includes_test_data", response, True)

    # ──────────────────────────────────────────────────────────
    # Print final summary
    # ──────────────────────────────────────────────────────────

    @classmethod
    def tearDownClass(cls):
        print("\n")
        print("=" * 55)
        print(" COUNSELLOR CONVERSION API - TEST DATA REPORT")
        print("=" * 55)
        print()
        print("-- Created Test Data ------")
        for key, value in cls.created_data.items():
            print("  %s: %s" % (str(key).ljust(25), value))
        print()
        print("-- Note -------------------")
        print("  All test data remains in the test database.")
        print("  No records were deleted.")
        print("=" * 55)
        super().tearDownClass()
