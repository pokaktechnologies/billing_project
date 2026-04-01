from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import CustomUser, Customer, InvoiceModel, ReceiptModel, SalesPerson
from accounts.services.invoice import delete_invoice_with_journal, sync_invoice_journal
from accounts.services.receipt import (
    ClientReceiptUpdater,
    delete_receipt_with_journals,
    sync_receipt_journals,
)
from finance.models import Account, JournalEntry


class InvoiceJournalSyncTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="password123",
        )
        self.salesperson = SalesPerson.objects.create(
            first_name="Sales",
            last_name="Rep",
            email="sales@example.com",
            phone="9999999991",
            mobile="9999999992",
            incentive=Decimal("0.00"),
        )
        self.customer = Customer.objects.create(
            company_name="Acme Corp",
            customer_type="business",
            salesperson=self.salesperson,
            mobile="9999999993",
        )

        asset_root = Account.objects.create(
            name="Current Assets",
            type="asset",
            account_number="1.1000",
            is_posting=False,
            status="active",
            opening_balance=0,
        )
        sales_root = Account.objects.create(
            name="Sales Income",
            type="sales",
            account_number="4.1000",
            is_posting=False,
            status="active",
            opening_balance=0,
        )
        Account.objects.create(
            name="Accounts Receivable",
            type="asset",
            parent_account=asset_root,
            account_number="1.1001",
            is_posting=True,
            status="active",
            opening_balance=0,
        )
        Account.objects.create(
            name="Service Income",
            type="sales",
            parent_account=sales_root,
            account_number="4.1001",
            is_posting=True,
            status="active",
            opening_balance=0,
        )

    def _create_invoice(self):
        invoice = InvoiceModel.objects.create(
            invoice_type="client",
            user=self.user,
            client=self.customer,
            invoice_number="INV-1001",
            invoice_date=date(2026, 3, 1),
            invoice_grand_total=Decimal("1500.00"),
        )
        return invoice

    def test_sync_invoice_journal_updates_existing_entry(self):
        invoice = self._create_invoice()

        first_journal = sync_invoice_journal(invoice, self.user)

        self.assertEqual(first_journal.type, "invoice")
        self.assertEqual(first_journal.type_number, invoice.invoice_number)
        self.assertEqual(first_journal.salesperson, self.salesperson)
        self.assertEqual(first_journal.date.date(), invoice.invoice_date)
        self.assertEqual(first_journal.lines.count(), 2)
        self.assertEqual(
            first_journal.lines.filter(debit=Decimal("1500.00")).count(),
            1,
        )
        self.assertEqual(
            first_journal.lines.filter(credit=Decimal("1500.00")).count(),
            1,
        )

        invoice.invoice_date = date(2026, 3, 5)
        invoice.invoice_grand_total = Decimal("2250.00")
        invoice.save(update_fields=["invoice_date", "invoice_grand_total"])

        updated_journal = sync_invoice_journal(invoice, self.user)

        self.assertEqual(updated_journal.id, first_journal.id)
        self.assertEqual(updated_journal.date.date(), invoice.invoice_date)
        self.assertEqual(updated_journal.lines.count(), 2)
        self.assertEqual(
            updated_journal.lines.filter(debit=Decimal("2250.00")).count(),
            1,
        )
        self.assertEqual(
            updated_journal.lines.filter(credit=Decimal("2250.00")).count(),
            1,
        )

    def test_delete_invoice_with_journal_removes_both(self):
        invoice = self._create_invoice()
        journal = sync_invoice_journal(invoice, self.user)

        delete_invoice_with_journal(invoice)

        self.assertFalse(
            InvoiceModel.objects.filter(invoice_number="INV-1001").exists()
        )
        self.assertFalse(JournalEntry.objects.filter(id=journal.id).exists())

    def test_sync_invoice_journal_accepts_string_invoice_date(self):
        invoice = self._create_invoice()
        invoice.invoice_date = "2026-03-10"

        journal = sync_invoice_journal(invoice, self.user)

        self.assertEqual(journal.date.date(), date(2026, 3, 10))


class ReceiptJournalSyncTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            first_name="Test",
            last_name="User",
            email="receipt@example.com",
            password="password123",
        )
        self.salesperson = SalesPerson.objects.create(
            first_name="Sales",
            last_name="Rep",
            email="receipt-sales@example.com",
            phone="9999999981",
            mobile="9999999982",
            incentive=Decimal("0.00"),
        )
        self.customer = Customer.objects.create(
            first_name="Jane",
            last_name="Client",
            customer_type="individual",
            salesperson=self.salesperson,
            mobile="9999999983",
        )

        asset_root = Account.objects.create(
            name="Current Assets",
            type="asset",
            account_number="1.1000",
            is_posting=False,
            status="active",
            opening_balance=0,
        )
        liability_root = Account.objects.create(
            name="Current Liabilities",
            type="liability",
            account_number="2.1000",
            is_posting=False,
            status="active",
            opening_balance=0,
        )
        Account.objects.create(
            name="Cash",
            type="asset",
            parent_account=asset_root,
            account_number="1.1001",
            is_posting=True,
            status="active",
            opening_balance=0,
        )
        Account.objects.create(
            name="Accounts Receivable",
            type="asset",
            parent_account=asset_root,
            account_number="1.1002",
            is_posting=True,
            status="active",
            opening_balance=0,
        )
        Account.objects.create(
            name="Output Tax Control",
            type="asset",
            parent_account=asset_root,
            account_number="1.1003",
            is_posting=True,
            status="active",
            opening_balance=0,
        )
        Account.objects.create(
            name="Output Tax Payable",
            type="liability",
            parent_account=liability_root,
            account_number="2.1001",
            is_posting=True,
            status="active",
            opening_balance=0,
        )

    def _create_receipt(self):
        return ReceiptModel.objects.create(
            receipt_type="client",
            user=self.user,
            client=self.customer,
            receipt_number="REC-1001",
            receipt_date=date(2026, 3, 1),
            cheque_amount=Decimal("1180.00"),
            total_amount=Decimal("1180.00"),
            tax_rate=Decimal("18.00"),
        )

    def test_receipt_update_syncs_main_and_tax_journals(self):
        receipt = self._create_receipt()
        cash = Account.objects.get(name="Cash")
        receivable = Account.objects.get(name="Accounts Receivable")

        first_journal = sync_receipt_journals(
            receipt,
            self.user,
            data={"debit_id": cash.id, "credit_id": receivable.id},
        )
        first_tax_journal = JournalEntry.objects.get(
            type="tax_payment",
            type_number="REC-1001_TAX",
        )

        updater = ClientReceiptUpdater()
        updater.update(
            receipt,
            {
                "receipt_date": date(2026, 3, 6),
                "cheque_amount": Decimal("2360.00"),
                "total_amount": Decimal("2360.00"),
                "tax_rate": Decimal("18.00"),
            },
            self.user,
        )

        updated_main = JournalEntry.objects.get(type="receipt", type_number="REC-1001")
        updated_tax = JournalEntry.objects.get(type="tax_payment", type_number="REC-1001_TAX")

        self.assertEqual(updated_main.id, first_journal.id)
        self.assertEqual(updated_tax.id, first_tax_journal.id)
        self.assertEqual(updated_main.date.date(), date(2026, 3, 6))
        self.assertEqual(updated_main.lines.filter(account=cash, debit=Decimal("2360.00")).count(), 1)
        self.assertEqual(updated_main.lines.filter(account=receivable, credit=Decimal("2360.00")).count(), 1)
        self.assertEqual(updated_tax.lines.filter(debit=Decimal("360.00")).count(), 1)
        self.assertEqual(updated_tax.lines.filter(credit=Decimal("360.00")).count(), 1)

    def test_delete_receipt_removes_related_journals(self):
        receipt = self._create_receipt()
        cash = Account.objects.get(name="Cash")
        receivable = Account.objects.get(name="Accounts Receivable")

        sync_receipt_journals(
            receipt,
            self.user,
            data={"debit_id": cash.id, "credit_id": receivable.id},
        )

        delete_receipt_with_journals(receipt)

        self.assertFalse(ReceiptModel.objects.filter(receipt_number="REC-1001").exists())
        self.assertFalse(JournalEntry.objects.filter(type="receipt", type_number="REC-1001").exists())
        self.assertFalse(JournalEntry.objects.filter(type="tax_payment", type_number="REC-1001_TAX").exists())
