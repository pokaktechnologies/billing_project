from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser,SalesPerson,InvoiceModel,Customer,Product,Supplier
from django.db import models
from django.utils import timezone
from decimal import Decimal
from .utils import JOURNAL_ACCOUNT_MAPPING

# ----------------------
# Account Model
# ----------------------
class Account(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('equity', 'Equity'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    account_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    parent_account = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='sub_accounts'
    ) # optionally link to a parent account
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.name} ({self.type}) - {self.account_number or 'No Number'}"


# ----------------------
# Journal Entry (Header)
# ----------------------
class JournalEntry(models.Model):
    TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('credit_note', 'Credit Note'),
        ('debit_note', 'Debit Note'),
        ('journal_voucher', 'Journal Voucher'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.SET_NULL, null=True, blank=True)
    type_number = models.CharField(max_length=100, blank=True, null=True, unique=True)  # e.g., invoice/payment number
    type = models.CharField(max_length=50, blank=True, null=True , choices=TYPE_CHOICES) 
    date = models.DateTimeField(default=timezone.now)
    narration = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)    


    def total_debit(self):
        return sum(line.debit for line in self.lines.all())

    def total_credit(self):
        return sum(line.credit for line in self.lines.all())

    def is_balanced(self):
        return round(self.total_debit(), 2) == round(self.total_credit(), 2)

    def clean(self):
        if self.pk and not self.is_balanced():
            raise ValidationError(
                f"Journal entry is not balanced: Debit ₹{self.total_debit()} ≠ Credit ₹{self.total_credit()}"
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # Enforces validation before save
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Entry #{self.id} on {self.date.date()} – {self.type or 'No Number'}"


# ----------------------
# Journal Entry Line (Details)
# ----------------------
class JournalLine(models.Model):
    journal = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


    def clean(self):
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A line cannot have both debit and credit.")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("Either debit or credit must be greater than zero.")

    def __str__(self):
        if self.debit > 0:
            return f"Dr ₹{self.debit} to {self.account.name} "
        elif self.credit > 0:
            return f"Cr ₹{self.credit} from {self.account.name}"
        return f"{self.account.name} – ₹0"




class CreditNote(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True)
    client = models.ForeignKey(Customer, on_delete=models.PROTECT)
    invoice = models.ForeignKey(InvoiceModel, on_delete=models.SET_NULL, null=True, blank=True)
    credit_note_number = models.CharField(max_length=50, unique=True)
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    document = models.FileField(upload_to='credit_notes/documents/', null=True, blank=True)
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.SET_NULL, null=True, blank=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # NEW: link to Journal Entry
    journal_entry = models.OneToOneField(
        'JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_note_entry'
    )

    def update_grand_total(self):
        items = self.items.all()
        total_amount = sum((item.total for item in items), Decimal(0))
        cgst_total = sum((item.cgst_amount for item in items), Decimal(0))
        sgst_total = sum((item.sgst_amount for item in items), Decimal(0))
        grand_total = total_amount + cgst_total + sgst_total

        self.total_amount = total_amount
        self.cgst_total = cgst_total
        self.sgst_total = sgst_total
        self.grand_total = grand_total
        self.save(update_fields=["total_amount", "cgst_total", "sgst_total", "grand_total"])

    def __str__(self):
        return f"Credit Note {self.credit_note_number} - {self.client}"

    # ✅ Create or Update Journal Entry
    def create_or_update_journal_entry(self):
        """Automatically creates/updates a balanced journal entry for this credit note."""
        from .models import JournalEntry, JournalLine, Account  # avoid circular import

        # Get or create JournalEntry
        journal, created = JournalEntry.objects.get_or_create(
            id=self.journal_entry.id if self.journal_entry else None,
            defaults={
                "user": self.user,
                "type": "credit_note",
                "type_number": self.credit_note_number,
                "salesperson": self.salesperson,
                "date": self.date,
                "narration": f"Credit Note for {self.client}",
            }
        )

        # Clear old lines if updating
        if not created:
            journal.lines.all().delete()

        # Example accounts (You can change as per your chart)
        accounts = JOURNAL_ACCOUNT_MAPPING['credit_note']

            # Example: Debit Sales Return, Credit Accounts Receivable
        debit_account = Account.objects.get(name=accounts['debit'])
        credit_account = Account.objects.get(name=accounts['credit'])

        # Create lines
        JournalLine.objects.create(
            journal=journal,
            account=debit_account,
            debit=self.grand_total
        )
        JournalLine.objects.create(
            journal=journal,
            account=credit_account,
            credit=self.grand_total
        )

        self.journal_entry = journal
        self.save(update_fields=["journal_entry"])
    # ✅ When Debit Note is deleted, remove its Journal Entry
    def delete(self, *args, **kwargs):
        if self.journal_entry:
            self.journal_entry.delete()
        super().delete(*args, **kwargs)


class CreditNoteItem(models.Model):
    credit_note = models.ForeignKey(CreditNote, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def save(self, *args, **kwargs):
        """Auto-calculate totals and update parent credit note."""
        unit_price = Decimal(self.unit_price or 0)
        quantity = Decimal(self.quantity or 0)

        self.total = unit_price * quantity
        self.cgst_amount = (self.total * Decimal(self.cgst_rate) / 100)
        self.sgst_amount = (self.total * Decimal(self.sgst_rate) / 100)
        self.sub_total = self.total + self.cgst_amount + self.sgst_amount

        super().save(*args, **kwargs)
        # Update parent totals
        self.credit_note.update_grand_total()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.credit_note.update_grand_total()

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


from decimal import Decimal
from django.db import models
from django.utils import timezone

class DebitNote(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    invoice = models.CharField(max_length=100, blank=True, null=True)
    debit_note_number = models.CharField(max_length=50, unique=True)
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    document = models.FileField(upload_to='debit_notes/documents/', null=True, blank=True)
    salesperson = models.ForeignKey(SalesPerson, on_delete=models.SET_NULL, null=True, blank=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: Link to Journal Entry (like Credit Note)
    journal_entry = models.OneToOneField(
        'JournalEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='debit_note_entry'
    )

    def update_grand_total(self):
        """Recalculate and update totals from items."""
        items = self.items.all()
        total_amount = sum((item.total for item in items), Decimal(0))
        cgst_total = sum((item.cgst_amount for item in items), Decimal(0))
        sgst_total = sum((item.sgst_amount for item in items), Decimal(0))
        grand_total = total_amount + cgst_total + sgst_total

        self.total_amount = total_amount
        self.cgst_total = cgst_total
        self.sgst_total = sgst_total
        self.grand_total = grand_total
        self.save(update_fields=["total_amount", "cgst_total", "sgst_total", "grand_total"])

    def __str__(self):
        return f"Debit Note {self.debit_note_number} - {self.supplier}"

    # ✅ Create or Update Journal Entry
    def create_or_update_journal_entry(self):
        """Automatically creates/updates journal entry for this debit note."""
        from .models import JournalEntry, JournalLine, Account  # avoid circular import

        journal, created = JournalEntry.objects.get_or_create(
            id=self.journal_entry.id if self.journal_entry else None,
            defaults={
                "user": self.user,
                "type": "debit_note",
                "type_number": self.debit_note_number,
                 "salesperson": self.salesperson,
                "date": self.date,
                "narration": f"Debit Note for {self.supplier}",
            }
        )

        # Clear existing lines if updated
        if not created:
            journal.lines.all().delete()

        # Example account mapping
        accounts = JOURNAL_ACCOUNT_MAPPING['debit_note']

        # Debit: Accounts Payable, Credit: Purchase Return
        debit_account = Account.objects.get(name=accounts['debit'])
        credit_account = Account.objects.get(name=accounts['credit'])

        # Journal lines
        JournalLine.objects.create(
            journal=journal,
            account=debit_account,
            debit=self.grand_total
        )
        JournalLine.objects.create(
            journal=journal,
            account=credit_account,
            credit=self.grand_total
        )

        self.journal_entry = journal
        self.save(update_fields=["journal_entry"])
    # ✅ When Debit Note is deleted, remove its Journal Entry
    def delete(self, *args, **kwargs):
        if self.journal_entry:
            self.journal_entry.delete()
        super().delete(*args, **kwargs)
class DebitNoteItem(models.Model):
    debit_note = models.ForeignKey(DebitNote, related_name='items', on_delete=models.CASCADE)
    product = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def save(self, *args, **kwargs):
        """Auto-calculate totals and update parent debit note."""
        quantity = Decimal(self.quantity or 0)
        unit_price = Decimal(self.unit_price or 0)

        self.total = unit_price * quantity
        self.cgst_amount = (self.total * Decimal(self.cgst_rate) / 100)
        self.sgst_amount = (self.total * Decimal(self.sgst_rate) / 100)
        self.sub_total = self.total + self.cgst_amount + self.sgst_amount

        super().save(*args, **kwargs)
        # Update parent totals
        self.debit_note.update_grand_total()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.debit_note.update_grand_total()

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


# Payment Model
# class Payment(models.Model):
#     PAYMENT_METHODS = [
#         ('cash', 'Cash'),
#         ('bank', 'Bank Transfer'),
#         ('upi', 'UPI'),
#         ('cheque', 'Cheque'),
#         ('other', 'Other'),
#     ]

#     user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
#     payment_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
#     date = models.DateTimeField(default=timezone.now)
#     paid_to = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='payments')
#     amount = models.DecimalField(max_digits=12, decimal_places=2)
#     payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
#     paid_from_account = models.ForeignKey(
#         Account, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='payments_from'
#     )  # CREDIT SIDE (bank/cash)
#     paid_to_account = models.ForeignKey(
#         Account, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='payments_to'
#     )  # DEBIT SIDE (expense/supplier/payable)
#     remark = models.TextField(blank=True, null=True)
#     journal_entry = models.OneToOneField(JournalEntry, on_delete=models.CASCADE, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Payment ₹{self.amount} to {self.paid_to.supplier_number if self.paid_to else 'N/A'} on {self.date.date()}"


