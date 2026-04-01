from decimal import Decimal
from datetime import datetime, time, date
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from internship.models import Course
from finance.models import JournalEntry, JournalLine, Account
from finance.utils import JOURNAL_ACCOUNT_MAPPING
from accounts.models import InvoiceModel, ReceiptModel, Customer, StaffProfile
from rest_framework.exceptions import ValidationError


def _receipt_datetime(receipt):
    receipt_date = receipt.receipt_date

    if isinstance(receipt_date, str):
        receipt_date = parse_date(receipt_date)
        if receipt_date is None:
            raise ValidationError({"receipt_date": "Invalid receipt_date format. Use YYYY-MM-DD."})

    if isinstance(receipt_date, datetime):
        receipt_date = receipt_date.date()

    if not isinstance(receipt_date, date):
        raise ValidationError({"receipt_date": "Invalid receipt_date value."})

    journal_dt = datetime.combine(receipt_date, time.min)
    if timezone.is_naive(journal_dt):
        return timezone.make_aware(journal_dt, timezone.get_current_timezone())
    return journal_dt


def _receipt_salesperson(receipt):
    if receipt.receipt_type == "client" and receipt.client_id and receipt.client.salesperson:
        return receipt.client.salesperson
    return None


def _receipt_narration(receipt):
    if receipt.receipt_type == "intern" and receipt.intern_id:
        return f"Intern Receipt {receipt.receipt_number} from {receipt.intern.user.first_name}"

    client = receipt.client
    if client:
        full_name = " ".join(filter(None, [client.first_name, client.last_name])).strip()
        if full_name:
            return f"Receipt {receipt.receipt_number} from {full_name}"
    return f"Receipt {receipt.receipt_number}"


def _receipt_tax_narration(receipt):
    if receipt.receipt_type == "intern" and receipt.intern_id:
        return f"Intern Receipt Tax {receipt.receipt_number} from {receipt.intern.user.first_name}"

    client = receipt.client
    if client:
        full_name = " ".join(filter(None, [client.first_name, client.last_name])).strip()
        if full_name:
            return f"Receipt Tax {receipt.receipt_number} from {full_name}"
    return f"Receipt Tax {receipt.receipt_number}"


def _resolve_receipt_main_accounts(data, existing_journal=None):
    debit_id = data.get("debit_id")
    credit_id = data.get("credit_id")

    if debit_id:
        debit_account = get_object_or_404(Account, pk=int(debit_id))
    elif existing_journal:
        debit_account = existing_journal.lines.filter(debit__gt=0).select_related("account").first()
        debit_account = debit_account.account if debit_account else None
    else:
        debit_account = None

    if credit_id:
        credit_account = get_object_or_404(Account, pk=int(credit_id))
    elif existing_journal:
        credit_account = existing_journal.lines.filter(credit__gt=0).select_related("account").first()
        credit_account = credit_account.account if credit_account else None
    else:
        credit_account = None

    if not debit_account or not credit_account:
        default_accounts = JOURNAL_ACCOUNT_MAPPING["receipt"]
        if not debit_account:
            debit_account = Account.objects.get(name=default_accounts["debit"])
        if not credit_account:
            credit_account = Account.objects.get(name=default_accounts["credit"])

    return debit_account, credit_account


def sync_receipt_journals(receipt, user=None, data=None, previous_receipt_number=None):
    data = data or {}
    lookup_numbers = [receipt.receipt_number]
    if previous_receipt_number and previous_receipt_number != receipt.receipt_number:
        lookup_numbers.append(previous_receipt_number)

    main_journal = (
        JournalEntry.objects
        .filter(type="receipt", type_number__in=lookup_numbers)
        .order_by("id")
        .first()
    )
    debit_account, credit_account = _resolve_receipt_main_accounts(data, existing_journal=main_journal)

    if not main_journal:
        main_journal = JournalEntry(type="receipt")

    main_journal.type = "receipt"
    main_journal.type_number = receipt.receipt_number
    main_journal.salesperson = _receipt_salesperson(receipt)
    main_journal.narration = _receipt_narration(receipt)
    main_journal.user = user or receipt.user
    main_journal.date = _receipt_datetime(receipt)
    main_journal.save()

    amount = (receipt.cheque_amount or Decimal("0.00")).quantize(Decimal("0.01"))
    rate = receipt.tax_rate or Decimal("0.00")
    tax_amount = ((amount * rate) / (Decimal("100.00") + rate)).quantize(Decimal("0.01")) if rate > 0 else Decimal("0.00")

    main_journal.lines.all().delete()
    JournalLine.objects.bulk_create([
        JournalLine(journal=main_journal, account=debit_account, debit=amount),
        JournalLine(journal=main_journal, account=credit_account, credit=amount),
    ])

    tax_lookup_numbers = [f"{receipt.receipt_number}_TAX"]
    if previous_receipt_number and previous_receipt_number != receipt.receipt_number:
        tax_lookup_numbers.append(f"{previous_receipt_number}_TAX")

    tax_journal = (
        JournalEntry.objects
        .filter(type="tax_payment", type_number__in=tax_lookup_numbers)
        .order_by("id")
        .first()
    )

    if tax_amount > 0:
        tax_accounts = JOURNAL_ACCOUNT_MAPPING["receipt_tax"]
        debit_account_tax = Account.objects.get(name=tax_accounts["debit"])
        credit_account_tax = Account.objects.get(name=tax_accounts["credit"])

        if not tax_journal:
            tax_journal = JournalEntry(type="tax_payment")

        tax_journal.type = "tax_payment"
        tax_journal.type_number = f"{receipt.receipt_number}_TAX"
        tax_journal.salesperson = _receipt_salesperson(receipt)
        tax_journal.narration = _receipt_tax_narration(receipt)
        tax_journal.user = user or receipt.user
        tax_journal.date = _receipt_datetime(receipt)
        tax_journal.save()

        tax_journal.lines.all().delete()
        JournalLine.objects.bulk_create([
            JournalLine(journal=tax_journal, account=debit_account_tax, debit=tax_amount),
            JournalLine(journal=tax_journal, account=credit_account_tax, credit=tax_amount),
        ])
    elif tax_journal:
        tax_journal.delete()

    return main_journal


def delete_receipt_with_journals(receipt):
    with transaction.atomic():
        JournalEntry.objects.filter(type="receipt", type_number=receipt.receipt_number).delete()
        JournalEntry.objects.filter(type="tax_payment", type_number=f"{receipt.receipt_number}_TAX").delete()
        receipt.delete()

class ClientReceiptService:

    @staticmethod
    def create(data, user):
        customer = get_object_or_404(Customer, id=data["client"])
        invoice_id = data.get("invoice")
        invoice = get_object_or_404(InvoiceModel, id=invoice_id) if invoice_id else None

        with transaction.atomic():
            receipt = ReceiptModel.objects.create(
                receipt_type="client",
                client=customer,
                invoice=invoice,
                receipt_number=data["receipt_number"],
                receipt_date=data["receipt_date"],
                cheque_amount=Decimal(data.get("cheque_amount", 0)),
                total_amount=Decimal(data.get("cheque_amount", 0)), # Assuming same as cheque for now
                tax_rate=Decimal(data.get("tax_rate", 0)),
                user=user,
                remark=data.get("remark", ""),
                description=data.get("description", ""),
                cheque_number=data.get("cheque_number", ""),
                bank_name=data.get("bank_name", ""),
                prepared_by=data.get("prepared_by", ""),
                recived_by=data.get("recived_by", ""),
                # debit_id and credit_id handled in Views currently, but should be moved here eventually.
                # preserving view logic for debit/credit lookup for journals 
            )


            # Journal Entry Creation is currently handled in the View using debit/credit IDs from request.
            # To strictly follow the service pattern, we should move it here. 
            # However, looking at the previous ReceiptView, it used `request.data.get('credit_id')` etc.
            # which are not in the standard model fields. 
            # I will return the receipt object and let the View handle the specific Journal creation 
            # OR I will implement a `_create_journal` that accepts the account IDs.
            
            # For now, I'll allow the view to handle the Journal creation call to `_create_journal` 
            # passing the extra data needed.
            
            sync_receipt_journals(receipt, user, data)

        return receipt

    @staticmethod
    def _create_journal(receipt, user, data):
        return sync_receipt_journals(receipt, user, data)


class InternReceiptService:

    @staticmethod
    def create(data, user):
        intern = get_object_or_404(StaffProfile, id=data["intern"])
        course = get_object_or_404(Course, id=data["course"])
        
        invoice_id = data.get("invoice")
        invoice = get_object_or_404(InvoiceModel, id=invoice_id) if invoice_id else None

        with transaction.atomic():
            receipt = ReceiptModel.objects.create(
                receipt_type="intern",
                intern=intern,
                course=course,
                invoice=invoice,
                receipt_number=data["receipt_number"],
                receipt_date=data["receipt_date"],
                cheque_amount=Decimal(data.get("cheque_amount", 0)),
                total_amount=Decimal(data.get("cheque_amount", 0)),
                tax_rate=Decimal(data.get("tax_rate", 0)),
                user=user,
                remark=data.get("remark", ""),
                description=data.get("description", ""),
                cheque_number=data.get("cheque_number", ""),
                bank_name=data.get("bank_name", ""),
                prepared_by=data.get("prepared_by", ""),
                recived_by=data.get("recived_by", ""),
            )

            sync_receipt_journals(receipt, user, data)

        return receipt

    @staticmethod
    def _create_journal(receipt, user, data):
        return sync_receipt_journals(receipt, user, data)


class ClientReceiptUpdater:
    def update(self, receipt, data, user): 
        with transaction.atomic():
            previous_receipt_number = receipt.receipt_number
            for field, value in data.items():
                if field in {"debit_id", "credit_id"}:
                    continue
                setattr(receipt, field, value)
            receipt.save()
            sync_receipt_journals(
                receipt,
                user,
                data=data,
                previous_receipt_number=previous_receipt_number
            )
        return receipt

class InternReceiptUpdater:
    def update(self, receipt, data, user):
        with transaction.atomic():
            previous_receipt_number = receipt.receipt_number
            for field, value in data.items():
                if field in {"debit_id", "credit_id"}:
                    continue
                setattr(receipt, field, value)
            receipt.save()
            sync_receipt_journals(
                receipt,
                user,
                data=data,
                previous_receipt_number=previous_receipt_number
            )
        return receipt
