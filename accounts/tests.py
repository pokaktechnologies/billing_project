from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import CustomUser, Customer, InvoiceModel, SalesPerson
from accounts.services.invoice import delete_invoice_with_journal, sync_invoice_journal
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
