from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from internship.models import Course
from finance.models import JournalEntry, JournalLine, Account
from finance.utils import JOURNAL_ACCOUNT_MAPPING
from accounts.models import InvoiceModel, InvoiceItem,Customer,StaffProfile,TermsAndConditions

from .tax_service import InvoiceItemCalculator
from .helpers import update_invoice_header

class ClientInvoiceService:

    @staticmethod
    def create(data, user):
        customer = get_object_or_404(Customer, id=data["client"])
        terms = get_object_or_404(TermsAndConditions, id=data["termsandconditions"])

        with transaction.atomic():
            invoice = InvoiceModel.objects.create(
                invoice_type="client",
                client=customer,
                invoice_number=data["invoice_number"],
                invoice_date=data["invoice_date"],
                user=user,
                termsandconditions=terms,
                remark=data.get("remark", ""),
                description=data.get("description", "")
            )

            items = []
            for item in data["items"]:
                calc = InvoiceItemCalculator.calculate(
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    sgst_pct=item.get("sgst_percentage", 0),
                    cgst_pct=item.get("cgst_percentage", 0),
                )

                items.append(
                    InvoiceItem(
                        invoice=invoice,
                        product_id=item.get("product"),
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        sgst_percentage=item.get("sgst_percentage", 0),
                        cgst_percentage=item.get("cgst_percentage", 0),
                        total=calc["total"],
                        sgst=calc["sgst"],
                        cgst=calc["cgst"],
                        sub_total=calc["sub_total"],
                    )
                )

            InvoiceItem.objects.bulk_create(items)

            invoice.recalculate_total()
            ClientInvoiceService._create_journal(invoice, user)

        return invoice

    @staticmethod
    def _create_journal(invoice, user):
        accounts = JOURNAL_ACCOUNT_MAPPING["invoice"]

        journal = JournalEntry.objects.create(
            type="invoice",
            type_number=invoice.invoice_number,
            narration=f"Invoice {invoice.invoice_number}",
            user=user
        )

        JournalLine.objects.bulk_create([
            JournalLine(
                journal=journal,
                account=Account.objects.get(name=accounts["debit"]),
                debit=invoice.invoice_grand_total
            ),
            JournalLine(
                journal=journal,
                account=Account.objects.get(name=accounts["credit"]),
                credit=invoice.invoice_grand_total
            )
        ])


class InternInvoiceService:

    @staticmethod
    def create(data, user):
        intern = get_object_or_404(StaffProfile, id=data["intern"])
        course = get_object_or_404(Course, id=data["course"])
        terms = get_object_or_404(TermsAndConditions, id=data["termsandconditions"])

        # ✅ Explicit extraction (NO items expected)
        fee_amount = Decimal(data["fee_amount"])
        sgst_pct = Decimal(data.get("sgst_percentage", 0))
        cgst_pct = Decimal(data.get("cgst_percentage", 0))

        calc = InvoiceItemCalculator.calculate(
            quantity=1,
            unit_price=fee_amount,
            sgst_pct=sgst_pct,
            cgst_pct=cgst_pct
        )

        with transaction.atomic():
            invoice = InvoiceModel.objects.create(
                invoice_type="intern",
                intern=intern,
                course=course,
                invoice_number=data["invoice_number"],
                invoice_date=data["invoice_date"],
                user=user,
                termsandconditions=terms,
                remark=data.get("remark", "Internship Fee"),
                description=data.get("description", "")
            )

            # ✅ Single service item
            InvoiceItem.objects.create(
                invoice=invoice,
                quantity=1,
                unit_price=fee_amount,
                sgst_percentage=sgst_pct,
                cgst_percentage=cgst_pct,
                total=calc["total"],
                sgst=calc["sgst"],
                cgst=calc["cgst"],
                sub_total=calc["sub_total"],
            )

            invoice.recalculate_total()
            InternInvoiceService._create_journal(invoice, user)

        return invoice

    @staticmethod
    def _create_journal(invoice, user):
        accounts = JOURNAL_ACCOUNT_MAPPING["invoice"]

        journal = JournalEntry.objects.create(
            type="invoice",
            type_number=invoice.invoice_number,
            narration=f"Intern Invoice {invoice.invoice_number}",
            user=user
        )

        JournalLine.objects.bulk_create([
            JournalLine(
                journal=journal,
                account=Account.objects.get(name=accounts["debit"]),
                debit=invoice.invoice_grand_total
            ),
            JournalLine(
                journal=journal,
                account=Account.objects.get(name=accounts["credit"]),
                credit=invoice.invoice_grand_total
            )
        ])


 
from rest_framework.exceptions import ValidationError

class ClientInvoiceUpdater:

    def update(self, invoice, data, user):
        if "items" not in data:
            raise ValidationError("Client invoice update requires items")

        with transaction.atomic():
            # ✅ 1. Update main invoice table
            update_invoice_header(invoice, data)

            # ✅ 2. Replace items completely
            invoice.items.all().delete()

            items = []
            for item in data["items"]:
                calc = InvoiceItemCalculator.calculate(
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    sgst_pct=item.get("sgst_percentage", 0),
                    cgst_pct=item.get("cgst_percentage", 0),
                )

                items.append(
                    InvoiceItem(
                        invoice=invoice,
                        product_id=item.get("product"),
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        sgst_percentage=item.get("sgst_percentage", 0),
                        cgst_percentage=item.get("cgst_percentage", 0),
                        total=calc["total"],
                        sgst=calc["sgst"],
                        cgst=calc["cgst"],
                        sub_total=calc["sub_total"],
                    )
                )

            InvoiceItem.objects.bulk_create(items)

            # ✅ 3. Recalculate totals
            invoice.recalculate_total()

        return invoice



class InternInvoiceUpdater:

    def update(self, invoice, data, user):
        if "fee_amount" not in data:
            raise ValidationError("Intern invoice requires fee_amount")

        fee = Decimal(data["fee_amount"])
        sgst = Decimal(data.get("sgst_percentage", 0))
        cgst = Decimal(data.get("cgst_percentage", 0))

        calc = InvoiceItemCalculator.calculate(
            quantity=1,
            unit_price=fee,
            sgst_pct=sgst,
            cgst_pct=cgst,
        )

        with transaction.atomic():
            # ✅ 1. Update main invoice table
            update_invoice_header(invoice, data)

            # ✅ 2. Replace single service item
            invoice.items.all().delete()

            InvoiceItem.objects.create(
                invoice=invoice,
                quantity=1,
                unit_price=fee,
                sgst_percentage=sgst,
                cgst_percentage=cgst,
                total=calc["total"],
                sgst=calc["sgst"],
                cgst=calc["cgst"],
                sub_total=calc["sub_total"],
            )

            # ✅ 3. Recalculate totals
            invoice.recalculate_total()

        return invoice