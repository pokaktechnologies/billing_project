"""
Tests for Admissions, Registrations, and Payments Standalone Report APIs.

Run with:
    python manage.py test internship.tests.test_admissions_breakdown_reports -v2 --keepdb
"""
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Department, SalesPerson, StaffProfile
from finance.models import TaxSettings
from internship.models import (
    Batch,
    Course,
    CoursePayment,
    InstallmentItem,
    InstallmentPlan,
    InternshipApplication,
    Student,
    StudentCourseEnrollment,
)

User = get_user_model()


class AdmissionsBreakdownReportsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Admin user
        cls.admin_user = User.objects.create_user(
            email="breakdown_admin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="Tester",
        )

        # Counsellors
        cls.counsellor_1 = SalesPerson.objects.create(
            first_name="Anita",
            last_name="Roy",
            email="anita.roy@example.com",
            phone="9876543210",
            mobile="9876543210",
            incentive=500,
        )
        cls.counsellor_2 = SalesPerson.objects.create(
            first_name="Sunil",
            last_name="Menon",
            email="sunil.menon@example.com",
            phone="9876543211",
            mobile="9876543211",
            incentive=400,
        )

        # Department & Courses
        cls.department = Department.objects.create(name="Tech Dept")
        cls.tax = TaxSettings.objects.create(name="GST 18", rate=18.0)
        cls.course_python = Course.objects.create(
            title="Python Masterclass",
            department=cls.department,
            total_fee=30000,
            tax_settings=cls.tax,
        )
        cls.plan_python = InstallmentPlan.objects.create(
            course=cls.course_python,
            total_installments=2,
        )
        InstallmentItem.objects.create(plan=cls.plan_python, installment_number=1, amount=15000, due_days=30)
        InstallmentItem.objects.create(plan=cls.plan_python, installment_number=2, amount=15000, due_days=60)

        cls.course_java = Course.objects.create(
            title="Java Enterprise",
            department=cls.department,
            total_fee=35000,
            tax_settings=cls.tax,
        )
        cls.plan_java = InstallmentPlan.objects.create(
            course=cls.course_java,
            total_installments=2,
        )
        InstallmentItem.objects.create(plan=cls.plan_java, installment_number=1, amount=17500, due_days=30)
        InstallmentItem.objects.create(plan=cls.plan_java, installment_number=2, amount=17500, due_days=60)

        # Students (Admissions)
        # Student 1: under Counsellor 1, Python Course
        u1 = User.objects.create_user(
            email="rahul.k@example.com",
            password="testpass123",
            first_name="Rahul",
            last_name="K",
        )
        p1 = StaffProfile.objects.create(user=u1, phone_number="9111111111")
        cls.student_1 = Student.objects.create(
            profile=p1,
            student_id="STU-001",
            councellor=cls.counsellor_1,
            start_date=date(2026, 7, 10),
        )
        StudentCourseEnrollment.objects.create(
            student=cls.student_1,
            course=cls.course_python,
            installment_plan=cls.plan_python,
            payment_plan_type="default_installment",
        )
        # CoursePayment for Student 1
        cls.payment_1 = CoursePayment.objects.create(
            student=cls.student_1,
            amount_paid=10000,
            payment_method="gpay",
            transaction_id="TXN-STU-001",
            payment_date=date(2026, 7, 10),
            payment_type="installment",
        )

        # Student 2: under Counsellor 2, Java Course
        u2 = User.objects.create_user(
            email="deepa.m@example.com",
            password="testpass123",
            first_name="Deepa",
            last_name="M",
        )
        p2 = StaffProfile.objects.create(user=u2, phone_number="9222222222")
        cls.student_2 = Student.objects.create(
            profile=p2,
            student_id="STU-002",
            councellor=cls.counsellor_2,
            start_date=date(2026, 7, 20),
        )
        StudentCourseEnrollment.objects.create(
            student=cls.student_2,
            course=cls.course_java,
            installment_plan=cls.plan_java,
            payment_plan_type="default_installment",
        )
        cls.payment_2 = CoursePayment.objects.create(
            student=cls.student_2,
            amount_paid=15000,
            payment_method="upi",
            transaction_id="TXN-STU-002",
            payment_date=date(2026, 7, 20),
            payment_type="advance",
        )

        # Applications (Registrations)
        # Registration 1: under Counsellor 1, Python Course
        cls.app_1 = InternshipApplication.objects.create(
            first_name="Ananya",
            last_name="Nair",
            email="ananya.nair@example.com",
            primary_phone="9333333333",
            dob=date(2000, 1, 1),
            gender="female",
            qualification="ug",
            address="Kochi",
            state="Kerala",
            district="Ernakulam",
            pincode="682001",
            course_duration=6,
            course_type="online",
            course=cls.course_python,
            councellor=cls.counsellor_1,
            is_converted=False,
            slot_amount=3000,
            slot_payment_method="upi",
            slot_transaction_id="TXN-SLOT-001",
            slot_payment_date=date(2026, 7, 12),
        )

        # Registration 2: under Counsellor 2, Java Course
        cls.app_2 = InternshipApplication.objects.create(
            first_name="Vivek",
            last_name="Pillai",
            email="vivek.p@example.com",
            primary_phone="9444444444",
            dob=date(1999, 5, 5),
            gender="male",
            qualification="pg",
            address="Trivandrum",
            state="Kerala",
            district="Thiruvananthapuram",
            pincode="695001",
            course_duration=6,
            course_type="offline",
            course=cls.course_java,
            councellor=cls.counsellor_2,
            is_converted=False,
            slot_amount=2500,
            slot_payment_method="gpay",
            slot_transaction_id="TXN-SLOT-002",
            slot_payment_date=date(2026, 7, 25),
        )

        # Ensure created_at dates for testing date ranges
        Student.objects.filter(id=cls.student_1.id).update(
            created_at=timezone.make_aware(datetime(2026, 7, 10, 10, 0))
        )
        Student.objects.filter(id=cls.student_2.id).update(
            created_at=timezone.make_aware(datetime(2026, 7, 20, 10, 0))
        )
        InternshipApplication.objects.filter(id=cls.app_1.id).update(
            created_at=timezone.make_aware(datetime(2026, 7, 12, 10, 0))
        )
        InternshipApplication.objects.filter(id=cls.app_2.id).update(
            created_at=timezone.make_aware(datetime(2026, 7, 25, 10, 0))
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    # ──────────────────────────────────────────────────────────
    # Admissions Endpoint Tests
    # ──────────────────────────────────────────────────────────

    def test_admissions_returns_pure_list(self):
        url = "/internship/report/admissions/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify it is a pure list (not dict with summary)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 2)
        # Check structure of item
        item = response.data[0]
        self.assertIn("student_id", item)
        self.assertIn("name", item)
        self.assertIn("email", item)
        self.assertIn("phone", item)
        self.assertIn("course", item)
        self.assertIn("counsellor", item)
        self.assertIn("admission_date", item)
        self.assertIn("payment", item)

    def test_admissions_filter_by_counsellor(self):
        url = f"/internship/report/admissions/?counsellor={self.counsellor_1.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for item in response.data:
            self.assertEqual(item["counsellor"]["id"], self.counsellor_1.id)

    def test_admissions_filter_by_course(self):
        url = f"/internship/report/admissions/?course={self.course_python.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for item in response.data:
            self.assertEqual(item["course"]["id"], self.course_python.id)

    def test_admissions_filter_by_date_dd_mm_yyyy(self):
        # Filter with DD-MM-YYYY
        url = "/internship/report/admissions/?start_date=01-07-2026&end_date=15-07-2026"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        # Should return only Student 1 (created 10-07-2026)
        ids = [item["student_id"] for item in response.data]
        self.assertIn("STU-001", ids)

    def test_admissions_search_filter(self):
        url = "/internship/report/admissions/?search=Rahul"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student_id"], "STU-001")

    def test_admissions_conditional_pagination(self):
        # When page is passed, returns paginated dict
        url = "/internship/report/admissions/?page=1&page_size=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    # ──────────────────────────────────────────────────────────
    # Registrations Endpoint Tests
    # ──────────────────────────────────────────────────────────

    def test_registrations_returns_pure_list(self):
        url = "/internship/report/registrations/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 2)
        item = response.data[0]
        self.assertIn("name", item)
        self.assertIn("email", item)
        self.assertIn("phone", item)
        self.assertIn("course", item)
        self.assertIn("counsellor", item)
        self.assertIn("registration_date", item)
        self.assertIn("slot_payment", item)

    def test_registrations_filter_by_counsellor(self):
        url = f"/internship/report/registrations/?counsellor={self.counsellor_2.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for item in response.data:
            self.assertEqual(item["counsellor"]["id"], self.counsellor_2.id)

    def test_registrations_filter_by_date_dd_mm_yyyy(self):
        url = "/internship/report/registrations/?start_date=01-07-2026&end_date=15-07-2026"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        names = [item["name"] for item in response.data]
        self.assertIn("Ananya Nair", names)

    def test_registrations_search_filter(self):
        url = "/internship/report/registrations/?search=Vivek"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("Vivek", response.data[0]["name"])

    # ──────────────────────────────────────────────────────────
    # Payments Endpoint Tests
    # ──────────────────────────────────────────────────────────

    def test_payments_returns_pure_list(self):
        url = "/internship/report/payments/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        # Should have course payments + slot payments
        self.assertGreaterEqual(len(response.data), 4)
        item = response.data[0]
        self.assertIn("payment_category", item)
        self.assertIn("payer_name", item)
        self.assertIn("amount", item)
        self.assertIn("payment_method", item)
        self.assertIn("transaction_id", item)
        self.assertIn("payment_date", item)

    def test_payments_filter_by_counsellor(self):
        url = f"/internship/report/payments/?counsellor={self.counsellor_1.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for item in response.data:
            self.assertEqual(item["counsellor"]["id"], self.counsellor_1.id)

    def test_payments_filter_by_type_slot(self):
        url = "/internship/report/payments/?payment_type=slot"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for item in response.data:
            self.assertEqual(item["payment_category"], "slot_amount")

    def test_payments_filter_by_date_dd_mm_yyyy(self):
        url = "/internship/report/payments/?start_date=10-07-2026&end_date=15-07-2026"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        txns = [p["transaction_id"] for p in response.data]
        self.assertIn("TXN-STU-001", txns)
        self.assertIn("TXN-SLOT-001", txns)

    def test_payments_conditional_pagination(self):
        url = "/internship/report/payments/?page=1&page_size=2"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)

    # ──────────────────────────────────────────────────────────
    # Admissions Summary KPI Endpoint Tests
    # ──────────────────────────────────────────────────────────

    def test_admissions_summary_endpoint(self):
        url = "/internship/report/admissions/summary/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Check KPI cards
        self.assertIn("total_registrations", data)
        self.assertIn("total_admissions", data)
        self.assertIn("total_payments", data)
        self.assertIn("pending_payments", data)
        self.assertIn("total_amount_collected", data)
        self.assertIn("conversion_rate", data)
        self.assertIn("today_registrations", data)
        self.assertIn("today_admissions", data)

        # Check values
        self.assertEqual(data["total_registrations"]["value"], 2)
        self.assertEqual(data["total_admissions"]["value"], 2)
        self.assertEqual(data["total_payments"]["value"], 4)
        self.assertEqual(data["conversion_rate"]["value"], 100.0)
        self.assertEqual(data["total_amount_collected"]["value"], "30500.00")

    def test_admissions_summary_filter_by_counsellor(self):
        url = f"/internship/report/admissions/summary/?counsellor={self.counsellor_1.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["total_registrations"]["value"], 1)
        self.assertEqual(data["total_admissions"]["value"], 1)
        self.assertEqual(data["total_payments"]["value"], 2)
        self.assertEqual(data["total_amount_collected"]["value"], "13000.00")

