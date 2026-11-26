from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import StaffProfile
from finance.models import Account, FinancialYear, PaymentVoucher, TaxSettings
from payroll.models import Payroll

User = get_user_model()


class FinancePendingDashboardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("finance-pending-dashboard")
        self.user = User.objects.create_user(
            email="fin@example.com",
            password="pass1234",
            first_name="Finance",
            last_name="User",
        )
        self.staff = StaffProfile.objects.create(user=self.user)

    def test_requires_authentication(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_finance_pending_dashboard_items_and_filters(self):
        root_asset = Account.objects.create(
            account_number="1.1000",
            name="Current Assets",
            type="asset",
            is_posting=False,
        )
        cash_acc = Account.objects.create(
            account_number="1.1001",
            name="Cash",
            type="asset",
            parent_account=root_asset,
            is_posting=True,
        )
        root_exp = Account.objects.create(
            account_number="7.1000",
            name="Operating Expenses",
            type="general_expenses",
            is_posting=False,
        )
        exp_acc = Account.objects.create(
            account_number="7.1001",
            name="Office Expense",
            type="general_expenses",
            parent_account=root_exp,
            is_posting=True,
        )

        PaymentVoucher.objects.create(
            voucher_number="PV-001",
            date=date.today() - timedelta(days=5),
            payment_method="cash",
            pay_to="Vendor A",
            debit_account=exp_acc,
            credit_account=cash_acc,
            amount=Decimal("1500.00"),
            status="draft",
        )

        FinancialYear.objects.create(
            name="FY 2025-26",
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=10),
            status="open",
            is_current=False,
        )

        Payroll.objects.create(
            staff=self.staff,
            month="2025-01",
            gross_salary=Decimal("30000.00"),
            working_days=22,
            paid_leave_used=0,
            unpaid_leave_days=Decimal("0.00"),
            deduction=Decimal("0.00"),
            net_salary=Decimal("30000.00"),
            status="Draft",
        )

        self.client.force_authenticate(user=self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["module"], "finance")
        self.assertEqual(res.data["tab_counts"]["payment_voucher"], 1)
        self.assertEqual(res.data["tab_counts"]["payroll"], 1)
        self.assertGreaterEqual(res.data["tab_counts"]["financial_year"], 2)

        res_pv = self.client.get(self.url, {"tab": "payment_voucher"})
        self.assertEqual(res_pv.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pv.data["items_count"], 1)

        res_search = self.client.get(self.url, {"search": "PV-001"})
        self.assertEqual(res_search.data["items_count"], 1)
