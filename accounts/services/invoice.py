from decimal import Decimal
from collections import defaultdict
from datetime import datetime, time
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from internship.models import Course
from finance.models import JournalEntry, JournalLine, Account
from finance.utils import JOURNAL_ACCOUNT_MAPPING
from rest_framework.exceptions import ValidationError
from accounts.models import InvoiceModel, InvoiceItem, Customer, StaffProfile, TermsAndConditions, Product

from .tax_service import InvoiceItemCalculator
from .helpers import update_invoice_header


def _to_stock_units(quantity, *, allow_negative=False):
    qty = Decimal(str(quantity))
    if qty != qty.to_integral_value():
        raise ValidationError(
            f"Quantity {quantity} is not supported for integer stock products."
        )

    units = int(qty)
    if not allow_negative and units < 0:
        raise ValidationError("Quantity cannot be negative.")
    return units


def _aggregate_item_quantities(items):
    quantities = defaultdict(int)
    for item in items:
        product_id = item.get("product")
        if not product_id:
            continue
        quantities[int(product_id)] += _to_stock_units(item["quantity"])
    return quantities


def _apply_stock_deltas(stock_deltas):
    """
    stock_deltas:
      delta < 0 => reduce stock (sales)
      delta > 0 => increase stock (revert/restock)
    """
    if not stock_deltas:
        return

    product_ids = list(stock_deltas.keys())
    products = Product.objects.select_for_update().filter(id__in=product_ids)
    product_map = {product.id: product for product in products}

    missing = [pid for pid in product_ids if pid not in product_map]
    if missing:
        raise ValidationError(f"Invalid product id(s): {missing}")

    for product_id, delta in stock_deltas.items():
        if delta == 0:
            continue

        product = product_map[product_id]
        new_stock = product.stock + delta
        if new_stock < 0:
            raise ValidationError(
                f"Insufficient stock for {product.name}. "
                f"Available: {product.stock}, required: {abs(delta)}"
            )

        Product.objects.filter(id=product_id).update(stock=F("stock") + delta)


def _journal_datetime_for_invoice(invoice):
    journal_dt = datetime.combine(invoice.invoice_date, time.min)
    if timezone.is_naive(journal_dt):
        return timezone.make_aware(journal_dt, timezone.get_current_timezone())
    return journal_dt


def _journal_narration_for_invoice(invoice):
    if invoice.invoice_type == "intern":
        return f"Intern Invoice {invoice.invoice_number}"
    return f"Invoice {invoice.invoice_number}"


def _journal_salesperson_for_invoice(invoice):
    if invoice.invoice_type == "client" and invoice.client_id:
        return invoice.client.salesperson
    return None


def sync_invoice_journal(invoice, user=None, previous_invoice_number=None):
    accounts = JOURNAL_ACCOUNT_MAPPING["invoice"]
    debit_account = Account.objects.get(name=accounts["debit"])
    credit_account = Account.objects.get(name=accounts["credit"])

    lookup_numbers = [invoice.invoice_number]
    if previous_invoice_number and previous_invoice_number != invoice.invoice_number:
        lookup_numbers.append(previous_invoice_number)

    journal = (
        JournalEntry.objects
        .filter(type="invoice", type_number__in=lookup_numbers)
        .order_by("id")
        .first()
    )

    if not journal:
        journal = JournalEntry(type="invoice")

    journal.type = "invoice"
    journal.type_number = invoice.invoice_number
    journal.narration = _journal_narration_for_invoice(invoice)
    journal.user = user or invoice.user
    journal.salesperson = _journal_salesperson_for_invoice(invoice)
    journal.date = _journal_datetime_for_invoice(invoice)
    journal.save()

    journal.lines.all().delete()
    JournalLine.objects.bulk_create([
        JournalLine(
            journal=journal,
            account=debit_account,
            debit=invoice.invoice_grand_total
        ),
        JournalLine(
            journal=journal,
            account=credit_account,
            credit=invoice.invoice_grand_total
        )
    ])

    return journal


def delete_invoice_with_journal(invoice):
    with transaction.atomic():
        JournalEntry.objects.filter(
            type="invoice",
            type_number=invoice.invoice_number
        ).delete()
        invoice.delete()

class ClientInvoiceService:

    @staticmethod
    def create(data, user):
        customer = get_object_or_404(Customer, id=data["client"])
        terms = get_object_or_404(TermsAndConditions, id=data["termsandconditions"])

        with transaction.atomic():
            requested_qty = _aggregate_item_quantities(data["items"])
            stock_deltas = {
                product_id: -qty
                for product_id, qty in requested_qty.items()
            }
            _apply_stock_deltas(stock_deltas)

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
            sync_invoice_journal(invoice, user)

        return invoice

    @staticmethod
    def _create_journal(invoice, user):
        return sync_invoice_journal(invoice, user)


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
            sync_invoice_journal(invoice, user)

        return invoice

    @staticmethod
    def _create_journal(invoice, user):
        return sync_invoice_journal(invoice, user)


 

class ClientInvoiceUpdater:

    def update(self, invoice, data, user):
        if "items" not in data:
            raise ValidationError("Client invoice update requires items")

        with transaction.atomic():
            previous_invoice_number = invoice.invoice_number
            # ✅ 1. Update main invoice table
            update_invoice_header(invoice, data)

            old_items = [
                {"product": item.product_id, "quantity": item.quantity}
                for item in invoice.items.all()
            ]
            old_qty = _aggregate_item_quantities(old_items)
            new_qty = _aggregate_item_quantities(data["items"])

            impacted_product_ids = set(old_qty) | set(new_qty)
            stock_deltas = {
                product_id: old_qty.get(product_id, 0) - new_qty.get(product_id, 0)
                for product_id in impacted_product_ids
            }
            _apply_stock_deltas(stock_deltas)

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
            sync_invoice_journal(
                invoice,
                user,
                previous_invoice_number=previous_invoice_number
            )

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
            previous_invoice_number = invoice.invoice_number
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
            sync_invoice_journal(
                invoice,
                user,
                previous_invoice_number=previous_invoice_number
            )

        return invoice

