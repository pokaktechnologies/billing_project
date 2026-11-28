from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import (
    Customer,
    CustomUser,
    InvoiceModel,
    QuotationOrderModel,
    ReceiptModel,
    SalesPerson,
    SalesReturnModel,
    StaffProfile,
    Supplier,
)
from finance.models import (
    Account,
    CreditNote,
    DebitNote,
    FinancialYear,
    JournalEntry,
    JournalLine,
    PaymentVoucher,
)


class AdminDashboardFinanceAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/accounts/dashboard/admin/"
        self.admin = CustomUser.objects.create_superuser(
            email="admin_dash@example.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        self.salesperson = SalesPerson.objects.create(
            first_name="Sales",
            last_name="Rep",
            email="sales_dash@example.com",
            phone="9999911111",
            mobile="9999911112",
            incentive=Decimal("0.00"),
        )
        self.customer = Customer.objects.create(
            company_name="Acme Corp",
            customer_type="business",
            salesperson=self.salesperson,
            mobile="9999911113",
        )
        self.supplier = Supplier.objects.create(
            supplier_number="SU-DASH-1",
            supplier_type="Business",
            company_name="Delta Suppliers",
            contact_person_name="Ramesh",
            contact_person_number="9999911114",
            address="Industrial Area",
            email="delta@example.com",
            date=date(2026, 4, 1),
            phone="0484111111",
            mobile="9999911115",
            currency="INR",
        )
        self.intern_user = CustomUser.objects.create_user(
            email="intern_dash@example.com",
            password="password123",
            first_name="Intern",
            last_name="One",
        )
        self.intern_profile = StaffProfile.objects.create(user=self.intern_user)

    def test_requires_authentication(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_database_returns_zeroed_finance_dashboard(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "1")

        data = res.data["data"]
        self.assertIn("hr_dashboard", data)
        self.assertIn("project_dashboard", data)
        self.assertIn("finance_dashboard", data)

        fin = data["finance_dashboard"]
        self.assertIsNone(fin["financial_year"])
        self.assertEqual(fin["sales_records"]["quotations"]["total_count"], 0)
        self.assertEqual(fin["sales_records"]["invoices"]["outstanding_amount"], "0.00")
        self.assertEqual(fin["sales_records"]["receipts"]["total_amount"], "0.00")
        self.assertEqual(fin["sales_records"]["sales_returns"]["total_count"], 0)
        self.assertEqual(fin["accounting"]["profit_and_loss"]["net_profit"], 0.0)
        self.assertFalse(fin["accounting"]["ledger_health"]["has_active_financial_year"])

    def test_invalid_date_params_return_400(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(self.url, {"from_date": "27-11-2026"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res2 = self.client.get(self.url, {"from_date": "2026-12-01", "to_date": "2026-11-01"})
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_aggregates_accounts_sales_and_finance_records(self):
        self.client.force_authenticate(user=self.admin)
        today = timezone.localdate()

        fy = FinancialYear.objects.create(
            name="FY 2026-27",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
            is_current=True,
            status="open",
        )

        # Chart of Accounts for P&L and PaymentVoucher
        asset_root = Account.objects.create(
            account_number="1.1000", name="Current Assets", type="asset", is_posting=False
        )
        cash_acc = Account.objects.create(
            account_number="1.1001", name="Cash", type="asset", parent_account=asset_root, is_posting=True
        )
        sales_root = Account.objects.create(
            account_number="4.1000", name="Sales", type="sales", is_posting=False
        )
        sales_acc = Account.objects.create(
            account_number="4.1001", name="Service Sales", type="sales", parent_account=sales_root, is_posting=True
        )
        exp_root = Account.objects.create(
            account_number="7.1000", name="General Expenses", type="general_expenses", is_posting=False
        )
        rent_acc = Account.objects.create(
            account_number="7.1001", name="Office Rent", type="general_expenses", parent_account=exp_root, is_posting=True
        )

        # Quotations (1 inside FY, 1 outside FY)
        QuotationOrderModel.objects.create(
            client=self.customer,
            user=self.admin,
            quotation_number="QT-101",
            quotation_date=date(2026, 5, 10),
            grand_total=Decimal("5000.00"),
            status="approved",
        )
        QuotationOrderModel.objects.create(
            client=self.customer,
            user=self.admin,
            quotation_number="QT-OLD",
            quotation_date=date(2025, 5, 10),
            grand_total=Decimal("9000.00"),
            status="draft",
        )

        # Invoices (client + intern)
        inv_client = InvoiceModel.objects.create(
            invoice_type="client",
            user=self.admin,
            client=self.customer,
            invoice_number="INV-201",
            invoice_date=today - timedelta(days=40),
            invoice_grand_total=Decimal("1000.00"),
            is_receipted=False,
        )
        inv_intern = InvoiceModel.objects.create(
            invoice_type="intern",
            user=self.admin,
            intern=self.intern_profile,
            invoice_number="INV-202",
            invoice_date=date(2026, 6, 15),
            invoice_grand_total=Decimal("500.00"),
            is_receipted=True,
        )

        # Receipts (1 linked to inv_client for 400, 1 unlinked client for 150)
        ReceiptModel.objects.create(
            receipt_type="client",
            user=self.admin,
            client=self.customer,
            invoice=inv_client,
            receipt_number="REC-301",
            receipt_date=date(2026, 6, 20),
            cheque_amount=Decimal("400.00"),
            total_amount=Decimal("400.00"),
        )
        ReceiptModel.objects.create(
            receipt_type="client",
            user=self.admin,
            client=self.customer,
            invoice=None,
            receipt_number="REC-302",
            receipt_date=date(2026, 6, 21),
            total_amount=Decimal("150.00"),
        )

        # Sales Return (1 approved linked to inv_client for 100 -> net_pending on inv_client = 1000 - 400 - 100 = 500)
        SalesReturnModel.objects.create(
            user=self.admin,
            client=self.customer,
            invoice=inv_client,
            sales_return_number="SR-401",
            return_date=date(2026, 6, 25),
            reason="Damaged",
            grand_total=Decimal("100.00"),
            status="approved",
        )

        # Journal Entries: 1 balanced for INV-201 (Sales 1000), 1 for rent expense (200) -> Net Profit = 800
        je_inv = JournalEntry.objects.create(
            user=self.admin,
            type="invoice",
            type_number="INV-201",
            date=timezone.make_aware(datetime.combine(date(2026, 6, 1), time(12, 0))),
            narration="Client invoice",
        )
        JournalLine.objects.create(journal=je_inv, account=cash_acc, debit=Decimal("1000.00"))
        JournalLine.objects.create(journal=je_inv, account=sales_acc, credit=Decimal("1000.00"))

        je_exp = JournalEntry.objects.create(
            user=self.admin,
            type="journal_voucher",
            type_number="JV-501",
            date=timezone.make_aware(datetime.combine(date(2026, 6, 5), time(12, 0))),
            narration="Rent",
        )
        JournalLine.objects.create(journal=je_exp, account=rent_acc, debit=Decimal("200.00"))
        JournalLine.objects.create(journal=je_exp, account=cash_acc, credit=Decimal("200.00"))

        # Payment Voucher, Credit Note, Debit Note
        PaymentVoucher.objects.create(
            user=self.admin,
            voucher_number="PV-601",
            date=date(2026, 6, 10),
            payment_method="cash",
            pay_to="Landlord",
            debit_account=rent_acc,
            credit_account=cash_acc,
            amount=Decimal("200.00"),
            status="draft",
        )
        CreditNote.objects.create(
            user=self.admin,
            client=self.customer,
            invoice=inv_client,
            credit_note_number="CN-701",
            date=date(2026, 6, 26),
            grand_total=Decimal("100.00"),
        )
        DebitNote.objects.create(
            user=self.admin,
            supplier=self.supplier,
            debit_note_number="DN-801",
            date=date(2026, 6, 27),
            grand_total=Decimal("300.00"),
        )

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        fin = res.data["data"]["finance_dashboard"]
        self.assertEqual(fin["financial_year"]["id"], fy.id)
        self.assertEqual(fin["financial_year"]["name"], "FY 2026-27")

        # Sales records (scoped to FY 2026-27 so QT-OLD is excluded)
        sales = fin["sales_records"]
        self.assertEqual(sales["quotations"]["total_count"], 1)
        self.assertEqual(sales["quotations"]["total_amount"], "5000.00")
        self.assertEqual(sales["quotations"]["approved"], 1)

        self.assertEqual(sales["invoices"]["total_count"], 2)
        self.assertEqual(sales["invoices"]["total_amount"], "1500.00")
        self.assertEqual(sales["invoices"]["client_count"], 1)
        self.assertEqual(sales["invoices"]["intern_count"], 1)
        # inv_client (1000 - 400 - 100 = 500) + inv_intern (500 - 0 - 0 = 500) = 1000.00
        self.assertEqual(sales["invoices"]["outstanding_amount"], "1000.00")
        self.assertEqual(sales["invoices"]["overdue_count"], 1)

        self.assertEqual(sales["receipts"]["total_count"], 2)
        self.assertEqual(sales["receipts"]["total_amount"], "550.00")
        self.assertEqual(sales["receipts"]["unlinked_count"], 1)

        self.assertEqual(sales["sales_returns"]["total_count"], 1)
        self.assertEqual(sales["sales_returns"]["approved"], 1)
        self.assertEqual(sales["sales_returns"]["pending_settlement_amount"], "100.00")

        # Accounting summary
        acc = fin["accounting"]
        self.assertEqual(acc["profit_and_loss"]["sales_total"], 1000.0)
        self.assertEqual(acc["profit_and_loss"]["general_expenses_total"], 200.0)
        self.assertEqual(acc["profit_and_loss"]["net_profit"], 800.0)
        self.assertEqual(acc["profit_and_loss"]["type"], "Net Profit")

        self.assertEqual(acc["payment_vouchers"]["draft_count"], 1)
        self.assertEqual(acc["payment_vouchers"]["draft_amount"], "200.00")
        self.assertEqual(acc["credit_notes"]["unposted_count"], 1)
        self.assertEqual(acc["debit_notes"]["unposted_count"], 1)

        health = acc["ledger_health"]
        self.assertEqual(health["total_journal_entries"], 2)
        self.assertEqual(health["unbalanced_journal_entries"], 0)
        self.assertEqual(health["invoices_missing_journal"], 1)  # inv_intern
        self.assertEqual(health["receipts_missing_journal"], 2)  # REC-301, REC-302
        self.assertTrue(health["has_active_financial_year"])
