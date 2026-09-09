from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from accounts.models import StaffProfile, JobDetail, Department, EmployeeRegistration, ModulePermission
from attendance.models import DailyAttendance, AttendanceSession, LeaveRequest, Holiday
from payroll.models import PayrollPeriod, Payroll
from hr_section.models import Designation, JobPosting, JobApplication, OfferLetter

User = get_user_model()


class HrDashboardAPITests(APITestCase):
    def setUp(self):
        # 1. Superuser
        self.admin_user = User.objects.create_superuser(
            email="hr_admin@example.com",
            password="adminpassword123",
            first_name="Admin",
            last_name="HR"
        )

        # 2. Regular staff user with hr_dashboard module permission
        self.hr_user = User.objects.create_user(
            email="hr_staff@example.com",
            password="staffpassword123",
            first_name="Jane",
            last_name="HR"
        )
        ModulePermission.objects.create(user=self.hr_user, module_name="hr_dashboard")

        # 3. Department & Designation
        self.dept = Department.objects.create(name="Human Resources")
        self.designation = Designation.objects.create(name="HR Specialist")

        # 4. Staff Profile & Job Detail
        self.staff_profile = StaffProfile.objects.create(
            user=self.hr_user,
            phone_number="1234567890",
            date_of_birth=timezone.localdate().replace(day=15)
        )
        self.job_detail = JobDetail.objects.create(
            staff=self.staff_profile,
            employee_id="HR-001",
            department=self.dept,
            job_type="full_day",
            role="HR Executive",
            salary=50000.00,
            start_date=timezone.localdate() - timedelta(days=365),
            status="active"
        )

        # 5. Daily Attendance
        self.attendance = DailyAttendance.objects.create(
            staff=self.staff_profile,
            date=timezone.localdate(),
            total_working_hours=8.0,
            status="full_day"
        )
        AttendanceSession.objects.create(
            daily_attendance=self.attendance,
            session="session1",
            status="present",
            login_time=timezone.now() - timedelta(hours=8),
            logout_time=timezone.now()
        )

        # 6. Leave Request
        self.leave = LeaveRequest.objects.create(
            staff=self.staff_profile,
            start_date=timezone.localdate() + timedelta(days=2),
            end_date=timezone.localdate() + timedelta(days=4),
            reason="Personal vacation",
            status="pending"
        )

        # 7. Holiday
        self.holiday = Holiday.objects.create(
            name="New Year",
            date=timezone.localdate() + timedelta(days=10),
            is_paid=True
        )

        # 8. Recruitment (JobPosting & Application)
        self.job = JobPosting.objects.create(
            job_title="Django Developer",
            job_type="full_time",
            work_mode="remote",
            designation=self.designation,
            job_description="Backend developer",
            status="active",
            experience_required="2+ years",
            salery_range="6-8 LPA"
        )
        self.application = JobApplication.objects.create(
            first_name="Candidate",
            last_name="One",
            email="candidate@example.com",
            phone="9876543210",
            job=self.job,
            experience=3,
            status="under_review"
        )

        # 9. Offer Letter
        self.offer = OfferLetter.objects.create(
            candidate_name="Offer Candidate",
            job_title="Software Engineer",
            monthly_salary=60000,
            joining_date=timezone.localdate() + timedelta(days=14),
            company_name="Pokak Inc",
            status="draft"
        )

        # 10. Payroll
        current_month = timezone.localdate().strftime("%Y-%m")
        self.payroll_period = PayrollPeriod.objects.create(month=current_month, status="open")
        self.payroll = Payroll.objects.create(
            staff=self.staff_profile,
            period=self.payroll_period,
            month=current_month,
            gross_salary=50000,
            working_days=22,
            total_working_hours=176,
            paid_leave_used=0,
            unpaid_leave_days=0,
            deduction=2000,
            net_salary=48000,
            status="Draft"
        )

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/hr/dashboard/metrics/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_hr_dashboard_metrics(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/metrics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("employee_summary", response.data)
        self.assertIn("today_attendance", response.data)
        self.assertIn("recruitment_summary", response.data)
        self.assertIn("payroll_status", response.data)
        self.assertEqual(response.data["employee_summary"]["total_employees"], 1)
        self.assertEqual(response.data["today_attendance"]["present_count"], 1)

    def test_hr_dashboard_action_items(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/action-items/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["pending_leave_requests_count"], 1)
        self.assertGreaterEqual(response.data["pending_offers_count"], 1)
        self.assertTrue(len(response.data["action_items"]) > 0)

    def test_hr_dashboard_attendance_live(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/attendance-live/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["staff_name"], "Jane HR")

    def test_hr_dashboard_leaves_active_upcoming(self):
        self.client.force_authenticate(user=self.hr_user)
        # Change leave to approved for test
        self.leave.status = "approved"
        self.leave.save()

        response = self.client.get("/hr/dashboard/leaves/active-upcoming/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("upcoming_leaves", response.data)
        self.assertEqual(len(response.data["upcoming_leaves"]), 1)

    def test_hr_dashboard_holidays_upcoming(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/holidays/upcoming/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        self.assertEqual(response.data[0]["name"], "New Year")

    def test_hr_dashboard_departments_summary(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/departments-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        self.assertEqual(response.data[0]["department_name"], "Human Resources")

    def test_hr_dashboard_milestones(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/employee-milestones/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("birthdays", response.data)
        self.assertIn("work_anniversaries", response.data)

    def test_hr_dashboard_recruitment_jobs_summary(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/recruitment/jobs-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        self.assertEqual(response.data[0]["job_title"], "Django Developer")
        self.assertEqual(response.data[0]["total_applications"], 1)

    def test_hr_dashboard_recent_applications(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/recruitment/recent-applications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        self.assertEqual(response.data[0]["candidate_name"], "Candidate One")

    def test_hr_dashboard_payroll_status(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/hr/dashboard/payroll/current-status/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_records"], 1)
        self.assertEqual(response.data["draft_records"], 1)
