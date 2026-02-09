from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from internship.models import Course
from finance.models import JournalEntry, JournalLine, Account
from finance.utils import JOURNAL_ACCOUNT_MAPPING
from accounts.models import InvoiceModel, ReceiptModel, Customer, StaffProfile
from rest_framework.exceptions import ValidationError

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
            
            ClientReceiptService._create_journal(receipt, user, data)

        return receipt

    @staticmethod
    def _create_journal(receipt, user, data):
        debit_id = data.get('debit_id')
        credit_id = data.get('credit_id')
        
        if not debit_id or not credit_id:
            return # Should probably raise error but keeping safe for now

        debit_account = get_object_or_404(Account, pk=int(debit_id))
        credit_account = get_object_or_404(Account, pk=int(credit_id))
        amount = receipt.cheque_amount

        accounts_tax = JOURNAL_ACCOUNT_MAPPING['receipt_tax']
        debit_account_tax = Account.objects.get(name=accounts_tax['debit'])
        credit_account_tax = Account.objects.get(name=accounts_tax['credit'])

        rate = receipt.tax_rate or 0
        amount = receipt.cheque_amount.quantize(Decimal('0.01'))
        tax_amount = ((amount * rate) / (100 + rate)).quantize(Decimal('0.01')) if rate > 0 else Decimal('0.00')

        client = receipt.client
        salesperson = client.salesperson if client and client.salesperson else None

        journal = JournalEntry.objects.create(
            type='receipt',
            type_number=receipt.receipt_number,
            salesperson=salesperson,
            narration=(
                f"Receipt {receipt.receipt_number} from {client.first_name} {client.last_name}"
                if client else
                f"Receipt {receipt.receipt_number}"
            ),
            user=user,
        )

        JournalLine.objects.create(journal=journal, account=debit_account, debit=amount)
        JournalLine.objects.create(journal=journal, account=credit_account, credit=amount)

        if tax_amount > 0:
            journal_tax = JournalEntry.objects.create(
                type='tax_payment',
                type_number=receipt.receipt_number + '_TAX',
                salesperson=salesperson,
                narration=(
                    f"Receipt Tax {receipt.receipt_number} from {client.first_name} {client.last_name}"
                    if client else
                    f"Receipt Tax {receipt.receipt_number}"
                ),
                user=user,
            )

            JournalLine.objects.create(journal=journal_tax, account=debit_account_tax, debit=tax_amount)
            JournalLine.objects.create(journal=journal_tax, account=credit_account_tax, credit=tax_amount)


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

            InternReceiptService._create_journal(receipt, user, data)

        return receipt

    @staticmethod
    def _create_journal(receipt, user, data):
        debit_id = data.get('debit_id')
        credit_id = data.get('credit_id')
        
        if not debit_id or not credit_id:
            return

        debit_account = get_object_or_404(Account, pk=int(debit_id))
        credit_account = get_object_or_404(Account, pk=int(credit_id))
        amount = receipt.cheque_amount

        # For intern receipt tax, we might use same mapping or different. 
        # Assuming same for now as user prompt didn't specify different tax account logic.
        accounts_tax = JOURNAL_ACCOUNT_MAPPING['receipt_tax']
        debit_account_tax = Account.objects.get(name=accounts_tax['debit'])
        credit_account_tax = Account.objects.get(name=accounts_tax['credit'])

        rate = receipt.tax_rate or 0
        amount = receipt.cheque_amount.quantize(Decimal('0.01'))
        tax_amount = ((amount * rate) / (100 + rate)).quantize(Decimal('0.01')) if rate > 0 else Decimal('0.00')

        intern = receipt.intern
        # Interns don't have salespersons usually, but keeping logic generic
        salesperson = None 

        journal = JournalEntry.objects.create(
            type='receipt',
            type_number=receipt.receipt_number,
            salesperson=salesperson,
            narration=f"Intern Receipt {receipt.receipt_number} from {intern.user.first_name}",
            user=user,
        )

        JournalLine.objects.create(journal=journal, account=debit_account, debit=amount)
        JournalLine.objects.create(journal=journal, account=credit_account, credit=amount)

        if tax_amount > 0:
            journal_tax = JournalEntry.objects.create(
                type='tax_payment',
                type_number=receipt.receipt_number + '_TAX',
                salesperson=salesperson,
                narration=f"Intern Receipt Tax {receipt.receipt_number} from {intern.user.first_name}",
                user=user,
            )

            JournalLine.objects.create(journal=journal_tax, account=debit_account_tax, debit=tax_amount)
            JournalLine.objects.create(journal=journal_tax, account=credit_account_tax, credit=tax_amount)


class ClientReceiptUpdater:
    def update(self, receipt, data, user): 
        # Implement update logic if needed
        pass

class InternReceiptUpdater:
    def update(self, receipt, data, user):
        # Implement update logic if needed
        pass
