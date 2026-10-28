from datetime import date, time
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Department, StaffProfile
from internship.models import (
    Center,
    Class,
    Course,
    Batch,
    Faculty,
    Section,
    Student,
    StudentCourseEnrollment,
    InstallmentPlan,
    InstallmentItem,
    ClassAttendanceSession,
    StudentAttendanceRecord,
)

User = get_user_model()


class AttendanceAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Department
        cls.department = Department.objects.create(name="Computer Science")

        # 2. Faculty User & Profile
        cls.faculty_user = User.objects.create_user(
            email="instructor@example.com",
            password="testpassword123",
            first_name="John",
            last_name="Doe",
        )
        cls.faculty_profile = StaffProfile.objects.create(
            user=cls.faculty_user,
            phone_number="9998887770",
        )
        cls.faculty = Faculty.objects.create(
            user=cls.faculty_profile,
            department=cls.department,
        )

        # 3. Academic Structure: Center -> Class -> Course -> Batch -> Section
        cls.center = Center.objects.create(name="Calicut Center")
        cls.class_obj = Class.objects.create(name="Room 101", center=cls.center)
        cls.course = Course.objects.create(
            title="Django Web Development",
            department=cls.department,
            total_fee=25000.00,
        )
        cls.plan = InstallmentPlan.objects.create(
            course=cls.course,
            total_installments=1,
        )
        InstallmentItem.objects.create(
            plan=cls.plan,
            installment_number=1,
            amount=25000,
            due_days=30,
        )

        cls.batch = Batch.objects.create(
            batch_number="B-2026-01",
            course=cls.course,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        cls.batch.faculties.add(cls.faculty)

        cls.section = Section.objects.create(
            class_obj=cls.class_obj,
            batch=cls.batch,
            start_time=time(9, 30),
            end_time=time(11, 30),
        )

        # 4. Students & Enrollments
        cls.student_user_1 = User.objects.create_user(
            email="student1@example.com",
            password="testpassword123",
            first_name="Alice",
            last_name="Smith",
        )
        cls.student_profile_1 = StaffProfile.objects.create(
            user=cls.student_user_1,
            phone_number="9111111111",
        )
        cls.student_1 = Student.objects.create(
            profile=cls.student_profile_1,
            student_id="STU20260001",
            start_date=date(2026, 1, 1),
        )
        StudentCourseEnrollment.objects.create(
            student=cls.student_1,
            course=cls.course,
            batch=cls.batch,
            installment_plan=cls.plan,
            payment_plan_type="default_installment",
        )

        cls.student_user_2 = User.objects.create_user(
            email="student2@example.com",
            password="testpassword123",
            first_name="Bob",
            last_name="Jones",
        )
        cls.student_profile_2 = StaffProfile.objects.create(
            user=cls.student_user_2,
            phone_number="9222222222",
        )
        cls.student_2 = Student.objects.create(
            profile=cls.student_profile_2,
            student_id="STU20260002",
            start_date=date(2026, 1, 1),
        )
        StudentCourseEnrollment.objects.create(
            student=cls.student_2,
            course=cls.course,
            batch=cls.batch,
            installment_plan=cls.plan,
            payment_plan_type="default_installment",
        )

        # Unenrolled Student (for validation test)
        cls.unenrolled_user = User.objects.create_user(
            email="outsider@example.com",
            password="testpassword123",
            first_name="Charlie",
            last_name="Brown",
        )
        cls.unenrolled_profile = StaffProfile.objects.create(
            user=cls.unenrolled_user,
            phone_number="9333333333",
        )
        cls.unenrolled_student = Student.objects.create(
            profile=cls.unenrolled_profile,
            student_id="STU20269999",
            start_date=date(2026, 1, 1),
        )

    def setUp(self):
        self.client = APIClient()

    def test_get_attendance_roster_as_faculty(self):
        """Faculty can fetch the student roster for their scheduled section."""
        self.client.force_authenticate(user=self.faculty_user)
        url = f"/internship/instructor/sections/{self.section.id}/attendance/?date=2026-10-28"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["section_id"], self.section.id)
        self.assertEqual(data["class_name"], "Room 101")
        self.assertEqual(data["batch_number"], "B-2026-01")
        self.assertFalse(data["is_marked"])
        self.assertEqual(data["total_enrolled"], 2)

        # Verify students list
        students = data["students"]
        self.assertEqual(len(students), 2)
        student_ids = [s["student_id"] for s in students]
        self.assertIn(self.student_1.id, student_ids)
        self.assertIn(self.student_2.id, student_ids)
        # Default status should be present
        for s in students:
            self.assertEqual(s["status"], "present")

    def test_submit_attendance_bulk(self):
        """Faculty can submit bulk attendance for their section."""
        self.client.force_authenticate(user=self.faculty_user)
        url = f"/internship/instructor/sections/{self.section.id}/attendance/"
        payload = {
            "date": "2026-10-28",
            "topic_covered": "Django REST Framework Views",
            "notes": "Good participation from the class",
            "records": [
                {"student_id": self.student_1.id, "status": "present", "remarks": ""},
                {"student_id": self.student_2.id, "status": "absent", "remarks": "Sick"},
            ],
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["total"], 2)
        self.assertEqual(response.data["summary"]["present"], 1)
        self.assertEqual(response.data["summary"]["absent"], 1)

        # Verify DB records
        session = ClassAttendanceSession.objects.get(section=self.section, date="2026-10-28")
        self.assertEqual(session.topic_covered, "Django REST Framework Views")
        self.assertEqual(session.records.count(), 2)

        rec1 = session.records.get(student=self.student_1)
        self.assertEqual(rec1.status, "present")

        rec2 = session.records.get(student=self.student_2)
        self.assertEqual(rec2.status, "absent")
        self.assertEqual(rec2.remarks, "Sick")

    def test_submit_attendance_with_invalid_student_rejected(self):
        """Submitting an unenrolled student ID must be rejected."""
        self.client.force_authenticate(user=self.faculty_user)
        url = f"/internship/instructor/sections/{self.section.id}/attendance/"
        payload = {
            "date": "2026-10-28",
            "records": [
                {"student_id": self.unenrolled_student.id, "status": "present"},
            ],
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("records", response.data)

    def test_update_existing_attendance(self):
        """Re-submitting attendance for the same section & date updates records cleanly."""
        self.client.force_authenticate(user=self.faculty_user)
        url = f"/internship/instructor/sections/{self.section.id}/attendance/"

        # First submission: both present
        payload1 = {
            "date": "2026-10-28",
            "records": [
                {"student_id": self.student_1.id, "status": "present"},
                {"student_id": self.student_2.id, "status": "present"},
            ],
        }
        self.client.post(url, payload1, format="json")

        # Second submission: mark student_2 as late
        payload2 = {
            "date": "2026-10-28",
            "topic_covered": "Updated Topic",
            "records": [
                {"student_id": self.student_1.id, "status": "present"},
                {"student_id": self.student_2.id, "status": "late", "remarks": "Bus delayed"},
            ],
        }
        response = self.client.post(url, payload2, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["late"], 1)

        # Check in DB
        session = ClassAttendanceSession.objects.get(section=self.section, date="2026-10-28")
        self.assertEqual(session.topic_covered, "Updated Topic")
        rec2 = session.records.get(student=self.student_2)
        self.assertEqual(rec2.status, "late")
        self.assertEqual(rec2.remarks, "Bus delayed")

    def test_section_attendance_history(self):
        """Faculty can view attendance history for a section."""
        # Create a session directly
        session = ClassAttendanceSession.objects.create(
            section=self.section,
            faculty=self.faculty,
            date=date(2026, 10, 27),
            topic_covered="Models and Migrations",
        )
        StudentAttendanceRecord.objects.create(session=session, student=self.student_1, status="present")
        StudentAttendanceRecord.objects.create(session=session, student=self.student_2, status="present")

        self.client.force_authenticate(user=self.faculty_user)
        url = f"/internship/instructor/sections/{self.section.id}/attendance-history/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["topic_covered"], "Models and Migrations")
        self.assertEqual(item["total_students"], 2)
        self.assertEqual(item["present_count"], 2)
        self.assertEqual(item["attendance_rate"], 100.0)

    def test_student_my_attendance_view(self):
        """Enrolled student can view their personal attendance record and percentage."""
        # Create sessions
        s1 = ClassAttendanceSession.objects.create(
            section=self.section,
            faculty=self.faculty,
            date=date(2026, 10, 25),
        )
        StudentAttendanceRecord.objects.create(session=s1, student=self.student_1, status="present")

        s2 = ClassAttendanceSession.objects.create(
            section=self.section,
            faculty=self.faculty,
            date=date(2026, 10, 26),
        )
        StudentAttendanceRecord.objects.create(session=s2, student=self.student_1, status="absent")

        # Authenticate as student 1
        self.client.force_authenticate(user=self.student_user_1)
        url = "/internship/intern/my-attendance/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        summary = response.data["summary"]
        self.assertEqual(summary["total_sessions"], 2)
        self.assertEqual(summary["present"], 1)
        self.assertEqual(summary["absent"], 1)
        self.assertEqual(summary["attendance_percentage"], 50.0)
        self.assertEqual(len(response.data["records"]), 2)
