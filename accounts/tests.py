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


from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import (
    EmployeeRegistration,
    EmployeeRegistrationDocument,
    Department,
    JobDetail,
    StaffProfile,
    StaffDocument,
    StaffEarning,
    StaffDeduction,
)

class EmployeeRegistrationConvertAPITests(APITestCase):

    def setUp(self):
        self.department = Department.objects.create(name="Engineering")
        self.photo = SimpleUploadedFile("test_photo.jpg", b"photo content", content_type="image/jpeg")
        self.registration = EmployeeRegistration.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="janedoe@example.com",
            phone_number="9876543210",
            qualification="B.Tech Computer Science",
            gender="female",
            emergency_contact="9876543211",
            country="India",
            date_of_birth=date(1999, 4, 12),
            address="456 Elm Street, City",
            profile_photo=self.photo,
        )
        # Add a document
        self.doc_file = SimpleUploadedFile("resume.pdf", b"pdf document content", content_type="application/pdf")
        EmployeeRegistrationDocument.objects.create(
            registration=self.registration,
            document_type="Resume",
            document_file=self.doc_file
        )

        self.convert_url = f"/accounts/employee-registration/{self.registration.id}/convert/"

        self.valid_payload = {
            "employee_id": "EMP-9001",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "role": "Backend Engineer",
            "salary": "45000.00",
            "start_date": "2026-10-01",
            "department": self.department.id,
            "job_type": "full_day",
            "status": "active",
            "modules": ["dashboard", "hr_staff_management", "hr_attendance"],
            "earnings": [
                {"earning_type": "Dearness Allowance", "amount": 3000.00}
            ],
            "deductions": [
                {"deduction_type": "Provident Fund", "amount": 1800.00}
            ]
        }

    def test_successful_conversion(self):
        """Outcome 1: Successful conversion with complete entities generated."""
        response = self.client.post(self.convert_url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "1")
        self.assertEqual(response.data["employee_id"], "EMP-9001")

        # Verify Registration is marked converted
        self.registration.refresh_from_db()
        self.assertTrue(self.registration.is_converted)
        self.assertEqual(self.registration.status, "converted")
        self.assertIsNotNone(self.registration.converted_staff)

        # Verify CustomUser
        user = CustomUser.objects.get(email="janedoe@example.com")
        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.gender, "female")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("Password@123"))

        # Verify Permissions
        perms = list(user.module_permissions.values_list("module_name", flat=True))
        self.assertCountEqual(perms, ["dashboard", "hr_staff_management", "hr_attendance"])

        # Verify StaffProfile
        staff_profile = StaffProfile.objects.get(user=user)
        self.assertEqual(staff_profile.phone_number, "9876543210")
        self.assertEqual(staff_profile.qulification, "B.Tech Computer Science")
        self.assertEqual(staff_profile.date_of_birth, date(1999, 4, 12))

        # Verify JobDetail
        job_detail = JobDetail.objects.get(staff=staff_profile)
        self.assertEqual(job_detail.employee_id, "EMP-9001")
        self.assertEqual(job_detail.department, self.department)
        self.assertEqual(job_detail.role, "Backend Engineer")
        self.assertEqual(Decimal(str(job_detail.salary)), Decimal("45000.00"))
        self.assertEqual(job_detail.status, "active")

        # Verify Documents Cloned
        self.assertEqual(StaffDocument.objects.filter(staff=staff_profile).count(), 1)
        self.assertEqual(StaffDocument.objects.filter(staff=staff_profile).first().doc_type, "Resume")

        # Verify Earnings and Deductions
        self.assertEqual(StaffEarning.objects.filter(job_detail=job_detail).count(), 1)
        self.assertEqual(StaffDeduction.objects.filter(job_detail=job_detail).count(), 1)

    def test_already_converted_error(self):
        """Outcome 2: Error when attempting to convert an already-converted registration."""
        self.registration.is_converted = True
        self.registration.save()

        response = self.client.post(self.convert_url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "0")
        self.assertIn("already been converted", response.data["message"])

    def test_duplicate_email_error(self):
        """Outcome 3: Error when user email already exists in CustomUser."""
        CustomUser.objects.create_user(
            first_name="Existing",
            last_name="User",
            email="janedoe@example.com",
            password="pass"
        )
        response = self.client.post(self.convert_url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "0")
        self.assertIn("already exists", response.data["message"])

    def test_duplicate_employee_id_error(self):
        """Outcome 4: Error when employee_id is already assigned to another JobDetail."""
        other_user = CustomUser.objects.create_user(first_name="A", last_name="B", email="ab@example.com", password="pwd")
        other_staff = StaffProfile.objects.create(user=other_user)
        JobDetail.objects.create(
            staff=other_staff,
            employee_id="EMP-9001",
            role="Lead",
            salary="50000.00",
            start_date="2026-01-01"
        )

        response = self.client.post(self.convert_url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("employee_id", response.data)

    def test_password_mismatch_error(self):
        """Outcome 5: Error when password and confirm_password differ."""
        payload = self.valid_payload.copy()
        payload["confirm_password"] = "MismatchedPassword@999"

        response = self.client.post(self.convert_url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_password", response.data)

    def test_missing_required_fields_error(self):
        """Outcome 6: Error when required fields are missing."""
        response = self.client.post(self.convert_url, data={}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("employee_id", response.data)
        self.assertIn("password", response.data)
        self.assertIn("confirm_password", response.data)
        self.assertIn("role", response.data)
        self.assertIn("salary", response.data)
        self.assertIn("start_date", response.data)
        self.assertIn("modules", response.data)

    def test_not_found_error(self):
        """Outcome 7: 404 error when registration ID does not exist."""
        url = "/accounts/employee-registration/999999/convert/"
        response = self.client.post(url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 404)


from datetime import timedelta
from django.utils import timezone
from activity_logs.utils import set_current_user
from accounts.models import (
    Category,
    MaterialReceive,
    MaterialReceiveItem,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
    TermsAndConditions,
    Unit,
)


class PurchasePendingDashboardAPITests(APITestCase):
    def setUp(self):
        set_current_user(None)
        self.user = CustomUser.objects.create_user(
            first_name="Purchase",
            last_name="Admin",
            email="purchase-admin@example.com",
            password="password123",
        )
        self.today = timezone.localdate()
        self.unit = Unit.objects.create(name="Piece")
        self.category = Category.objects.create(name="Hardware")
        self.terms = TermsAndConditions.objects.create(title="Net 30")

        self.product_a = Product.objects.create(
            name="Monitor 24",
            unit=self.unit,
            unit_price=Decimal("1000.00"),
            stock=5,
            category=self.category,
            code="MON-24",
        )
        self.product_b = Product.objects.create(
            name="Keyboard Mech",
            unit=self.unit,
            unit_price=Decimal("500.00"),
            stock=2,
            category=self.category,
            code="KEY-MECH",
        )

        self.business_supplier = Supplier.objects.create(
            supplier_number="SU|100001",
            supplier_type="Business",
            company_name="Acme Supplies Pvt Ltd",
            contact_person_name="Ravi Kumar",
            contact_person_number="9876543210",
            address="12 Industrial Estate",
            email="acme@example.com",
            date=self.today,
            phone="0484123456",
            mobile="9876543210",
            currency="INR",
            payment_terms=self.terms,
        )
        self.other_supplier = Supplier.objects.create(
            supplier_number="SU|100002",
            supplier_type="Business",
            company_name="Beta Traders",
            contact_person_name="Anu Nair",
            contact_person_number="9876500000",
            address="99 Market Road",
            email="beta@example.com",
            date=self.today,
            phone="0484654321",
            mobile="9876500000",
            currency="INR",
            payment_terms=self.terms,
        )

        self.dashboard_url = "/accounts/purchases/pending-dashboard/"
        self.po_url = "/accounts/purchase-orders/"
        self.mr_url = "/accounts/material-receive/"
        self.supplier_url = "/accounts/suppliers/"

    def tearDown(self):
        set_current_user(None)
        super().tearDown()

    def _auth(self):
        self.client.force_authenticate(user=self.user)

    def _create_po_via_api(self, number="PO|100001", po_date=None, expected_delivery_date=None, status_val="draft", items=None):
        payload = {
            "supplier": self.business_supplier.id,
            "purchase_order_number": number,
            "purchase_order_date": str(po_date or self.today),
            "contact_person_name": "Ravi Kumar",
            "contact_person_number": "9876543210",
            "status": status_val,
        }
        if expected_delivery_date is not None:
            payload["expected_delivery_date"] = str(expected_delivery_date)
        if items is not None:
            payload["items"] = items
        return self.client.post(self.po_url, data=payload, format="json")

    def test_requires_authentication(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 401)

    def test_po_full_lifecycle_and_dashboard_clearing(self):
        self._auth()

        # 1. PO created without items -> po_empty_items
        res = self._create_po_via_api(number="PO|100001", items=None)
        self.assertEqual(res.status_code, 201)
        po_id = res.data["data"]["id"]

        dash = self.client.get(self.dashboard_url, {"tab": "purchase_order"}).data
        self.assertEqual(dash["items"][0]["work_type"], "po_empty_items")

        # 2. Add items -> grand_total auto-computed, moves to po_draft
        patch_res = self.client.patch(
            f"{self.po_url}{po_id}/",
            data={"items": [{"product": self.product_a.id, "quantity": 10, "unit_price": "1000.00"}]},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(Decimal(patch_res.data["data"]["grand_total"]), Decimal("10000.00"))

        dash = self.client.get(self.dashboard_url, {"tab": "purchase_order"}).data
        self.assertEqual(dash["items"][0]["work_type"], "po_draft")
        self.assertEqual(dash["items"][0]["urgency"], "medium")

        # 3. Send PO -> po_unreceived (high urgency if >7 days old)
        old_date = self.today - timedelta(days=10)
        self.client.patch(
            f"{self.po_url}{po_id}/",
            data={"status": "sent", "purchase_order_date": str(old_date)},
            format="json",
        )
        dash = self.client.get(self.dashboard_url, {"tab": "purchase_order"}).data
        self.assertEqual(dash["items"][0]["work_type"], "po_unreceived")
        self.assertEqual(dash["items"][0]["urgency"], "high")

        # 4. Partial MR -> PO auto-moves to partially_received
        mr1 = self.client.post(
            self.mr_url,
            data={
                "supplier": self.business_supplier.id,
                "purchase_order": po_id,
                "material_receive_number": "MR|100001",
                "received_date": str(self.today),
                "items": [{"product": self.product_a.id, "quantity": 4, "unit_price": "1000.00"}],
            },
            format="json",
        )
        self.assertEqual(mr1.status_code, 201)
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 9)

        po_obj = PurchaseOrder.objects.get(id=po_id)
        self.assertEqual(po_obj.status, "partially_received")

        dash = self.client.get(self.dashboard_url, {"tab": "purchase_order"}).data
        self.assertEqual(dash["items"][0]["work_type"], "po_partially_received")
        self.assertEqual(dash["items"][0]["meta"]["pending_qty"], 6)

        # 5. Final MR -> PO auto-moves to received and clears purchase_order tab
        mr2 = self.client.post(
            self.mr_url,
            data={
                "supplier": self.business_supplier.id,
                "purchase_order": po_id,
                "material_receive_number": "MR|100002",
                "received_date": str(self.today),
                "items": [{"product": self.product_a.id, "quantity": 6, "unit_price": "1000.00"}],
            },
            format="json",
        )
        self.assertEqual(mr2.status_code, 201)
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 15)

        po_obj.refresh_from_db()
        self.assertEqual(po_obj.status, "received")

        dash = self.client.get(self.dashboard_url, {"tab": "purchase_order"}).data
        self.assertEqual(dash["items_count"], 0)

    def test_po_overdue_closed_and_cancelled_rules(self):
        self._auth()

        overdue_date = self.today - timedelta(days=4)
        res_overdue = self._create_po_via_api(
            number="PO|100010",
            po_date=self.today - timedelta(days=6),
            expected_delivery_date=overdue_date,
            status_val="sent",
            items=[{"product": self.product_a.id, "quantity": 5, "unit_price": "1000.00"}],
        )
        self.assertEqual(res_overdue.status_code, 201)
        po_overdue_id = res_overdue.data["data"]["id"]

        res_closed = self._create_po_via_api(
            number="PO|100011",
            status_val="sent",
            items=[{"product": self.product_b.id, "quantity": 3, "unit_price": "500.00"}],
        )
        po_closed_id = res_closed.data["data"]["id"]

        res_cancelled = self._create_po_via_api(
            number="PO|100012",
            status_val="sent",
            items=[{"product": self.product_b.id, "quantity": 2, "unit_price": "500.00"}],
        )
        po_cancelled_id = res_cancelled.data["data"]["id"]

        # Close and cancel two POs -> only overdue remains
        self.client.patch(f"{self.po_url}{po_closed_id}/", data={"status": "closed"}, format="json")
        self.client.patch(f"{self.po_url}{po_cancelled_id}/", data={"status": "cancelled"}, format="json")

        dash = self.client.get(self.dashboard_url, {"tab": "purchase_order"}).data
        self.assertEqual(dash["items_count"], 1)
        item = dash["items"][0]
        self.assertEqual(item["record_id"], po_overdue_id)
        self.assertEqual(item["work_type"], "po_overdue_delivery")
        self.assertEqual(item["urgency"], "high")
        self.assertEqual(item["due_date"], str(overdue_date))
        self.assertEqual(item["meta"]["days_overdue"], 4)

    def test_mr_verification_rejection_and_discrepancies(self):
        self._auth()

        po_res = self._create_po_via_api(
            number="PO|100020",
            status_val="sent",
            items=[{"product": self.product_a.id, "quantity": 5, "unit_price": "1000.00"}],
        )
        po_id = po_res.data["data"]["id"]

        # MR1: normal partial receive -> defaults to pending_verification
        mr1_res = self.client.post(
            self.mr_url,
            data={
                "supplier": self.business_supplier.id,
                "purchase_order": po_id,
                "material_receive_number": "MR|100020",
                "received_date": str(self.today),
                "items": [{"product": self.product_a.id, "quantity": 3, "unit_price": "1000.00"}],
            },
            format="json",
        )
        self.assertEqual(mr1_res.status_code, 201)
        mr1_id = mr1_res.data["data"]["id"]
        self.assertEqual(mr1_res.data["data"]["status"], "pending_verification")
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 8)

        dash_mr = self.client.get(self.dashboard_url, {"tab": "material_receive"}).data
        self.assertEqual([i["work_type"] for i in dash_mr["items"]], ["mr_pending_verification"])

        # Verify MR1 -> clears mr_pending_verification, keeps stock
        verify_res = self.client.patch(f"{self.mr_url}{mr1_id}/", data={"status": "verified"}, format="json")
        self.assertEqual(verify_res.status_code, 200)
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 8)
        dash_mr = self.client.get(self.dashboard_url, {"tab": "material_receive"}).data
        self.assertEqual(dash_mr["items_count"], 0)

        # Reject MR1 -> reverts stock, rolls PO back to sent, clears MR from dashboard
        reject_res = self.client.patch(f"{self.mr_url}{mr1_id}/", data={"status": "rejected"}, format="json")
        self.assertEqual(reject_res.status_code, 200)
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 5)
        self.assertEqual(PurchaseOrder.objects.get(id=po_id).status, "sent")

        # MR2: empty items + supplier mismatch
        self.client.post(
            self.mr_url,
            data={
                "supplier": self.other_supplier.id,
                "purchase_order": po_id,
                "material_receive_number": "MR|100021",
                "received_date": str(self.today),
                "status": "verified",
            },
            format="json",
        )
        # MR3: over-received + un-ordered product + grand total mismatch
        self.client.post(
            self.mr_url,
            data={
                "supplier": self.business_supplier.id,
                "purchase_order": po_id,
                "material_receive_number": "MR|100022",
                "received_date": str(self.today),
                "status": "verified",
                "grand_total": "999.00",
                "items": [
                    {"product": self.product_a.id, "quantity": 8, "unit_price": "1000.00"},
                    {"product": self.product_b.id, "quantity": 2, "unit_price": "500.00"},
                ],
            },
            format="json",
        )

        dash_mr = self.client.get(self.dashboard_url, {"tab": "material_receive"}).data
        work_types = {it["work_type"] for it in dash_mr["items"]}
        self.assertEqual(
            work_types,
            {"mr_empty_items", "mr_supplier_mismatch", "mr_over_received", "mr_total_mismatch"},
        )
        over_item = next(it for it in dash_mr["items"] if it["work_type"] == "mr_over_received")
        reasons = {d["reason"] for d in over_item["meta"]["discrepancies"]}
        self.assertEqual(reasons, {"exceeds_ordered_quantity", "not_in_purchase_order"})

    def test_mr_bug_fixes_delete_date_filter_item_swap_and_insufficient_stock(self):
        self._auth()

        po_res = self._create_po_via_api(
            number="PO|100030",
            status_val="sent",
            items=[
                {"product": self.product_a.id, "quantity": 10, "unit_price": "1000.00"},
                {"product": self.product_b.id, "quantity": 10, "unit_price": "500.00"},
            ],
        )
        po_id = po_res.data["data"]["id"]

        # Create MR with product_a qty 4 (stock: 5 -> 9)
        mr_res = self.client.post(
            self.mr_url,
            data={
                "supplier": self.business_supplier.id,
                "purchase_order": po_id,
                "material_receive_number": "MR|100030",
                "received_date": str(self.today),
                "items": [{"product": self.product_a.id, "quantity": 4, "unit_price": "1000.00"}],
            },
            format="json",
        )
        self.assertEqual(mr_res.status_code, 201)
        mr_id = mr_res.data["data"]["id"]
        mr_item_id = mr_res.data["data"]["items"][0]["id"]
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 9)

        # Bug fix 1: Date range + status + PO filtering on GET /accounts/material-receive/
        list_res = self.client.get(
            self.mr_url,
            {
                "start_date": str(self.today - timedelta(days=1)),
                "end_date": str(self.today + timedelta(days=1)),
                "status": "pending_verification",
                "purchase_order": po_id,
            },
        )
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.data["data"]), 1)
        self.assertEqual(list_res.data["data"][0]["supplier_name"], "Acme Supplies Pvt Ltd")

        # Bug fix 2: Swapping existing item product updates both old and new product stock
        swap_res = self.client.patch(
            f"{self.mr_url}{mr_id}/",
            data={
                "items": [
                    {
                        "id": mr_item_id,
                        "product": self.product_b.id,
                        "quantity": 3,
                        "unit_price": "500.00",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(swap_res.status_code, 200)
        self.product_a.refresh_from_db()
        self.product_b.refresh_from_db()
        self.assertEqual(self.product_a.stock, 5)
        self.assertEqual(self.product_b.stock, 5)

        # Consume product_b stock below 3 -> rejecting or deleting MR must fail cleanly with 400
        self.product_b.stock = 1
        self.product_b.save(update_fields=["stock"])

        reject_fail = self.client.patch(f"{self.mr_url}{mr_id}/", data={"status": "rejected"}, format="json")
        self.assertEqual(reject_fail.status_code, 400)
        self.assertEqual(MaterialReceive.objects.get(id=mr_id).status, "pending_verification")

        delete_fail = self.client.delete(f"{self.mr_url}{mr_id}/")
        self.assertEqual(delete_fail.status_code, 400)
        self.assertTrue(MaterialReceive.objects.filter(id=mr_id).exists())

        # Restore sufficient stock -> DELETE reverts stock and rolls PO back to sent
        self.product_b.stock = 5
        self.product_b.save(update_fields=["stock"])

        delete_ok = self.client.delete(f"{self.mr_url}{mr_id}/")
        self.assertEqual(delete_ok.status_code, 204)
        self.product_b.refresh_from_db()
        self.assertEqual(self.product_b.stock, 2)
        self.assertEqual(PurchaseOrder.objects.get(id=po_id).status, "sent")

    def test_supplier_controls_display_names_and_query_filters(self):
        self._auth()

        incomplete_biz = Supplier.objects.create(
            supplier_number="SU|100010",
            supplier_type="Business",
            company_name="",
            contact_person_name="",
            contact_person_number="",
            address="",
            email="incbiz@example.com",
            date=self.today,
            phone="111",
            mobile="111",
            currency="INR",
        )
        incomplete_ind = Supplier.objects.create(
            supplier_number="SU|100011",
            supplier_type="Individual",
            first_name="",
            address="",
            email="incind@example.com",
            date=self.today,
            phone="222",
            mobile="222",
            currency="INR",
            payment_terms=self.terms,
        )

        # Supplier tab catches incomplete Business (profile + terms) and Individual (profile)
        sup_dash = self.client.get(self.dashboard_url, {"tab": "supplier"}).data
        self.assertEqual(sup_dash["items_count"], 3)

        biz_profile_item = next(i for i in sup_dash["items"] if i["id"] == f"sup_profile_{incomplete_biz.id}")
        self.assertEqual(
            set(biz_profile_item["meta"]["missing_fields"]),
            {"company_name", "contact_person_name", "contact_person_number", "address"},
        )
        ind_profile_item = next(i for i in sup_dash["items"] if i["id"] == f"sup_profile_{incomplete_ind.id}")
        self.assertEqual(
            set(ind_profile_item["meta"]["missing_fields"]),
            {"first_name", "address"},
        )

        # Deactivate supplier -> clears from dashboard
        deact_res = self.client.patch(
            f"{self.supplier_url}{incomplete_biz.id}/",
            data={"is_active": False},
            format="json",
        )
        self.assertEqual(deact_res.status_code, 200)
        sup_dash = self.client.get(self.dashboard_url, {"tab": "supplier"}).data
        self.assertEqual(sup_dash["items_count"], 1)
        self.assertEqual(sup_dash["items"][0]["record_id"], incomplete_ind.id)

        # Add POs of different urgencies and verify sort, search, urgency, and limit params
        self._create_po_via_api(
            number="PO|100040",
            po_date=self.today,
            status_val="draft",
            items=[{"product": self.product_a.id, "quantity": 1, "unit_price": "1000.00"}],
        )
        self._create_po_via_api(
            number="PO|100041",
            po_date=self.today - timedelta(days=9),
            status_val="sent",
            items=[{"product": self.product_a.id, "quantity": 1, "unit_price": "1000.00"}],
        )

        # Check Business supplier_name on PO list, detail, and report endpoints
        po_list = self.client.get(self.po_url).data["Data"]
        self.assertEqual(po_list[0]["supplier_name"], "Acme Supplies Pvt Ltd")
        self.assertIn("status", po_list[0])
        self.assertIn("expected_delivery_date", po_list[0])

        po_detail = self.client.get(f"{self.po_url}{po_list[0]['id']}/").data["data"][0]
        self.assertEqual(po_detail["supplier_name"], "Acme Supplies Pvt Ltd")

        po_report = self.client.get("/accounts/reports/purchase-order/", {"status": "sent"}).data["Data"]
        self.assertEqual(len(po_report), 1)
        self.assertEqual(po_report[0]["supplier_name"], "Acme Supplies Pvt Ltd")
        self.assertEqual(po_report[0]["status"], "sent")

        sup_active = self.client.get(self.supplier_url, {"is_active": "false"}).data["Data"]
        self.assertEqual(len(sup_active), 1)
        self.assertEqual(sup_active[0]["id"], incomplete_biz.id)

        full_dash = self.client.get(self.dashboard_url).data
        urgencies = [it["urgency"] for it in full_dash["items"]]
        priority_map = {"high": 1, "medium": 2, "low": 3}
        self.assertEqual(urgencies, sorted(urgencies, key=lambda u: priority_map[u]))

        search_dash = self.client.get(self.dashboard_url, {"search": "PO|100041"}).data
        self.assertEqual(search_dash["items_count"], 1)
        self.assertEqual(search_dash["items"][0]["urgency"], "high")

        limit_dash = self.client.get(self.dashboard_url, {"limit": "2"}).data
        self.assertEqual(limit_dash["items_count"], 2)


