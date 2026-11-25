from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import EmployeeRegistration, ModulePermission, StaffProfile
from attendance.models import LeaveRequest
from hr_section.models import Enquiry, ErpEnquiry, HRPolicy
from payroll.models import Payroll, PayrollPeriod

User = get_user_model()


class HrPendingDashboardAPITests(APITestCase):
    URL = "/hr/pending-dashboard/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="hr.manager@example.com",
            password="Password123!",
            first_name="HR",
            last_name="Manager",
        )
        ModulePermission.objects.create(user=self.user, module_name="hr_pending")

        self.staff_user = User.objects.create_user(
            email="dev.staff@example.com",
            password="Password123!",
            first_name="Dev",
            last_name="Staff",
        )
        self.staff_profile = StaffProfile.objects.create(user=self.staff_user)

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 401)

    def test_requires_hr_pending_permission(self):
        no_perm_user = User.objects.create_user(
            email="noperm@example.com",
            password="Password123!",
            first_name="No",
            last_name="Perm",
        )
        self.client.force_authenticate(user=no_perm_user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 403)

    def test_modules_all_includes_hr_pending(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/accounts/user/modules/all/")
        self.assertEqual(response.status_code, 200)
        modules = response.json().get("modules", [])
        pending_controls = next((m for m in modules if m["name"] == "pending_controls"), None)
        self.assertIsNotNone(pending_controls)
        self.assertIn("hr_pending", pending_controls["submodules"])

    def test_employee_registration_tab_and_urgency_thresholds(self):
        now = timezone.now()
        reg_recent = EmployeeRegistration.objects.create(
            first_name="Asha",
            last_name="Nair",
            email="asha@example.com",
            phone_number="9876543210",
            status="pending",
            is_converted=False,
        )
        reg_old_pending = EmployeeRegistration.objects.create(
            first_name="Vikram",
            last_name="Rao",
            email="vikram@example.com",
            phone_number="9876543211",
            status="pending",
            is_converted=False,
        )
        EmployeeRegistration.objects.filter(pk=reg_old_pending.pk).update(
            created_at=now - timedelta(days=4)
        )
        reg_reviewed_recent = EmployeeRegistration.objects.create(
            first_name="Rahul",
            last_name="Menon",
            email="rahul@example.com",
            phone_number="9876543212",
            status="reviewed",
            is_converted=False,
        )
        reg_reviewed_old = EmployeeRegistration.objects.create(
            first_name="Sneha",
            last_name="Das",
            email="sneha@example.com",
            phone_number="9876543213",
            status="reviewed",
            is_converted=False,
        )
        EmployeeRegistration.objects.filter(pk=reg_reviewed_old.pk).update(
            created_at=now - timedelta(days=6)
        )
        # Excluded
        EmployeeRegistration.objects.create(
            first_name="Converted",
            last_name="User",
            email="conv@example.com",
            phone_number="9876543214",
            status="converted",
            is_converted=True,
        )
        EmployeeRegistration.objects.create(
            first_name="Rejected",
            last_name="User",
            email="rej@example.com",
            phone_number="9876543215",
            status="rejected",
            is_converted=False,
        )

        self.client.force_authenticate(user=self.user)
        resp = self.client.get(f"{self.URL}?tab=employee_registration")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["tab_counts"]["employee_registration"], 4)

        by_id = {item["record_id"]: item for item in data["items"]}
        self.assertEqual(by_id[reg_recent.id]["urgency"], "medium")
        self.assertEqual(by_id[reg_recent.id]["work_type"], "employee_registration_pending")
        self.assertEqual(by_id[reg_old_pending.id]["urgency"], "high")
        self.assertEqual(by_id[reg_reviewed_recent.id]["urgency"], "medium")
        self.assertEqual(by_id[reg_reviewed_recent.id]["work_type"], "employee_registration_reviewed")
        self.assertEqual(by_id[reg_reviewed_old.id]["urgency"], "high")

    def test_leaves_tab_half_day_and_urgency(self):
        now = timezone.now()
        today = timezone.localdate()

        leave_soon = LeaveRequest.objects.create(
            staff=self.staff_profile,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=1),
            is_half_day=True,
            start_time=time(9, 30),
            end_time=time(13, 30),
            reason="Doctor appointment",
            status="pending",
        )
        leave_future_recent = LeaveRequest.objects.create(
            staff=self.staff_profile,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=12),
            reason="Family function",
            status="pending",
        )
        leave_future_stale = LeaveRequest.objects.create(
            staff=self.staff_profile,
            start_date=today + timedelta(days=15),
            end_date=today + timedelta(days=15),
            reason="Personal work",
            status="pending",
        )
        LeaveRequest.objects.filter(pk=leave_future_stale.pk).update(
            requested_at=now - timedelta(days=3)
        )
        LeaveRequest.objects.create(
            staff=self.staff_profile,
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=2),
            reason="Already approved",
            status="approved",
        )

        self.client.force_authenticate(user=self.user)
        resp = self.client.get(f"{self.URL}?tab=leaves")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["tab_counts"]["leaves"], 3)

        by_id = {item["record_id"]: item for item in data["items"]}
        self.assertEqual(by_id[leave_soon.id]["urgency"], "high")
        self.assertIn("Half-day", by_id[leave_soon.id]["description"])
        self.assertEqual(by_id[leave_soon.id]["due_date"], (today + timedelta(days=1)).isoformat())
        self.assertEqual(by_id[leave_future_recent.id]["urgency"], "medium")
        self.assertEqual(by_id[leave_future_stale.id]["urgency"], "high")

    def test_payroll_tab_periods_and_draft_slips(self):
        now = timezone.now()
        today = timezone.localdate()
        current_month = today.strftime("%Y-%m")
        past_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

        past_open = PayrollPeriod.objects.create(month=past_month, status="open")
        curr_gen = PayrollPeriod.objects.create(month=current_month, status="generated")

        # Current month generated with 0 drafts -> payroll_period_unlocked (medium)
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(f"{self.URL}?tab=payroll")
        self.assertEqual(resp.status_code, 200)
        work_types = {i["item_id"] if "item_id" in i else i["id"]: i for i in resp.json()["items"]}
        self.assertEqual(work_types[f"payroll_period_open_{past_open.id}"]["urgency"], "high")
        self.assertEqual(work_types[f"payroll_period_unlocked_{curr_gen.id}"]["urgency"], "medium")

        # Adding a Draft slip on current month -> slip shows as Draft, unlocked disappears until paid
        slip = Payroll.objects.create(
            staff=self.staff_profile,
            period=curr_gen,
            month=current_month,
            gross_salary=Decimal("40000.00"),
            working_days=22,
            paid_leave_used=0,
            unpaid_leave_days=Decimal("0.00"),
            deduction=Decimal("0.00"),
            net_salary=Decimal("40000.00"),
            status="Draft",
        )
        Payroll.objects.filter(pk=slip.pk).update(created_at=now - timedelta(days=4))

        resp2 = self.client.get(f"{self.URL}?tab=payroll")
        self.assertEqual(resp2.status_code, 200)
        ids2 = {i["id"]: i for i in resp2.json()["items"]}
        self.assertIn(f"payroll_draft_{slip.id}", ids2)
        self.assertEqual(ids2[f"payroll_draft_{slip.id}"]["urgency"], "high")
        self.assertNotIn(f"payroll_period_unlocked_{curr_gen.id}", ids2)

        # Locking past_open and paying slip -> unlocked reappears for curr_gen; locking curr_gen clears all
        past_open.status = "locked"
        past_open.save()
        slip.status = "Paid"
        slip.save()
        curr_gen.status = "locked"
        curr_gen.save()

        resp3 = self.client.get(f"{self.URL}?tab=payroll")
        self.assertEqual(resp3.status_code, 200)
        self.assertEqual(resp3.json()["tab_counts"]["payroll"], 0)

    def test_enquiries_and_policies_tabs_sorting_and_limit(self):
        now = timezone.now()
        today = timezone.localdate()

        enq_new_old = Enquiry.objects.create(
            first_name="Kiran",
            email="kiran@example.com",
            phone="9999999999",
            message="Urgent HR enquiry",
            status="new",
        )
        Enquiry.objects.filter(pk=enq_new_old.pk).update(created_at=now - timedelta(days=3))

        Enquiry.objects.create(
            first_name="Meera",
            email="meera@example.com",
            phone="9999999998",
            message="Reviewed recent",
            status="reviewed",
        )
        ErpEnquiry.objects.create(
            full_name="Arjun",
            work_email="arjun@corp.com",
            company_name="Tech Corp",
            status="new",
            preferred_datetime=now + timedelta(hours=6),
        )
        ErpEnquiry.objects.create(
            full_name="Done",
            work_email="done@corp.com",
            company_name="Done Corp",
            status="responded",
        )

        HRPolicy.objects.create(
            title="Remote Policy",
            policy_code="POL-01",
            status="draft",
            effective_date=today,
        )
        HRPolicy.objects.create(
            title="Future Policy",
            policy_code="POL-02",
            status="draft",
            effective_date=today + timedelta(days=10),
        )
        HRPolicy.objects.create(
            title="Active Policy",
            policy_code="POL-03",
            status="active",
        )

        self.client.force_authenticate(user=self.user)
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["tab_counts"]["enquiries"], 3)
        self.assertEqual(data["tab_counts"]["policies"], 2)

        # Verify strict urgency ordering: high -> medium -> low
        rank = {"high": 0, "medium": 1, "low": 2}
        urgencies = [rank[item["urgency"]] for item in data["items"]]
        self.assertEqual(urgencies, sorted(urgencies))

        # Verify limit & search
        limited = self.client.get(f"{self.URL}?limit=2")
        self.assertEqual(limited.status_code, 200)
        self.assertEqual(limited.json()["items_count"], 2)
        self.assertEqual(len(limited.json()["items"]), 2)

        searched = self.client.get(f"{self.URL}?search=Tech Corp")
        self.assertEqual(searched.status_code, 200)
        self.assertEqual(searched.json()["items_count"], 1)
        self.assertEqual(searched.json()["items"][0]["work_type"], "erp_enquiry_new")
