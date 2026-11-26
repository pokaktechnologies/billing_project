from datetime import date, time, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Department, ModulePermission, StaffProfile
from internship.models import (
    Batch,
    Center,
    Class,
    Course,
    Faculty,
    LiveClass,
    RecordedClass,
    Section,
    SectionDay,
    Student,
    Task,
    TaskAssignment,
    Test,
)

User = get_user_model()


class FacultyPendingDashboardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("faculty-pending-dashboard")

        self.faculty_user = User.objects.create_user(
            email="fac1@example.com",
            password="pass1234",
            first_name="John",
            last_name="Doe",
        )
        self.staff_profile = StaffProfile.objects.create(user=self.faculty_user)
        self.faculty = Faculty.objects.create(user=self.staff_profile)
        ModulePermission.objects.create(user=self.faculty_user, module_name="faculty_pending")

        self.other_user = User.objects.create_user(
            email="fac2@example.com",
            password="pass1234",
            first_name="Jane",
            last_name="Smith",
        )
        self.other_staff = StaffProfile.objects.create(user=self.other_user)
        self.other_faculty = Faculty.objects.create(user=self.other_staff)
        ModulePermission.objects.create(user=self.other_user, module_name="faculty_pending")

        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="pass1234",
            first_name="Admin",
            last_name="User",
        )

        self.center = Center.objects.create(name="Kochi Center")
        self.department = Department.objects.create(name="IT")
        self.course = Course.objects.create(
            title="Python Full Stack",
            description="Desc",
            department=self.department,
            total_fee=10000,
        )
        self.batch = Batch.objects.create(
            batch_number="B-01",
            course=self.course,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
        )
        self.batch.faculties.add(self.faculty)

        self.student_user = User.objects.create_user(
            email="stu1@example.com",
            password="pass1234",
            first_name="Asha",
            last_name="Nair",
        )
        self.student_profile = StaffProfile.objects.create(user=self.student_user)
        self.student = Student.objects.create(
            profile=self.student_profile,
            student_id="STD-001",
            start_date=date.today() - timedelta(days=30),
        )

    def test_requires_authentication(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_faculty_pending_permission(self):
        no_perm_user = User.objects.create_user(
            email="noperm_fac@example.com",
            password="pass1234",
            first_name="No",
            last_name="Perm",
        )
        self.client.force_authenticate(user=no_perm_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_faculty_scoped_pending_items_and_filters(self):
        # 1. Submitted task assignment
        task = Task.objects.create(
            title="Build API",
            description="REST API",
            start_date=date.today() - timedelta(days=5),
            due_date=date.today() - timedelta(days=1),
            course=self.course,
            batch=self.batch,
        )
        TaskAssignment.objects.create(task=task, student=self.student, status="submitted")

        # 2. Draft test
        Test.objects.create(
            name="Module 1 Quiz",
            test_type="mcq",
            course=self.course,
            batch=self.batch,
            duration_minutes=30,
            total_marks=20,
            status="draft",
        )

        # 3. Unpublished recorded class
        RecordedClass.objects.create(
            title="Intro Lecture",
            course=self.course,
            batch=self.batch,
            faculty=self.faculty,
            is_published=False,
        )

        # 4. Overdue live class
        LiveClass.objects.create(
            title="Doubt Clearing",
            course=self.course,
            batch=self.batch,
            faculty=self.faculty,
            room_name="room-doubt-clearing-1",
            scheduled_start_time=timezone.now() - timedelta(hours=2),
            status="scheduled",
        )

        # 5. Today's attendance not marked
        cls = Class.objects.create(name="Room 101", center=self.center)
        sec = Section.objects.create(
            class_obj=cls,
            batch=self.batch,
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        SectionDay.objects.create(section=sec, day=day_map[timezone.localdate().weekday()])

        # Authenticate as faculty
        self.client.force_authenticate(user=self.faculty_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["module"], "faculty")
        self.assertEqual(res.data["tab_counts"]["submissions"], 1)
        self.assertEqual(res.data["tab_counts"]["my_courses"], 2)
        self.assertEqual(res.data["tab_counts"]["schedule"], 1)
        self.assertGreaterEqual(res.data["tab_counts"]["faculty_attendance"], 1)

        # Tab filter
        res_sub = self.client.get(self.url, {"tab": "submissions"})
        self.assertEqual(res_sub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sub.data["items_count"], 1)

        # Search filter
        res_search = self.client.get(self.url, {"search": "Doubt Clearing"})
        self.assertEqual(res_search.data["items_count"], 1)

        # Other faculty sees 0 items
        self.client.force_authenticate(user=self.other_user)
        res_other = self.client.get(self.url)
        self.assertEqual(res_other.status_code, status.HTTP_200_OK)
        self.assertEqual(res_other.data["total_pending_count"], 0)

        # Admin sees all items
        self.client.force_authenticate(user=self.admin_user)
        res_admin = self.client.get(self.url)
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res_admin.data["total_pending_count"], 5)
