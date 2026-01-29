from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser,SalesPerson,InvoiceModel,Customer,Product,Supplier
from django.db import models
from django.utils import timezone
from decimal import Decimal
from .utils import JOURNAL_ACCOUNT_MAPPING
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
# ----------------------
# Account Model
# ----------------------
class Account(models.Model):
    """
    Chart of Accounts model with strict hierarchy and accounting rules.
    
    HIERARCHY RULES:
    - Maximum 3 levels: Type → Parent → Child
    - Level 1 (Type): e.g., 10000 Assets - NON-POSTING
    - Level 2 (Parent): e.g., 1.1000 Current Assets - NON-POSTING  
    - Level 3 (Child): e.g., 1.10001 Cash - POSTING
    
    NUMBERING SCHEME:
    - Type level: X0000 (no dot) - 10000, 20000, 30000...
    - Parent level: X.Y000 - 1.1000, 1.2000, 2.1000...
    - Child level: X.Y000Z - 1.10001, 1.10002, 1.20001...
    
    TYPE PREFIXES:
    - 1 → asset
    - 2 → liability
    - 3 → equity
    - 4 → sales
    - 5 → cost_of_sales
    - 6 → revenue
    - 7 → general_expenses
    """
    
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),  # 1
        ('liability', 'Liability'),  # 2
        ('equity', 'Equity'),  # 3
        ('sales', 'Sales'),  # 4
        ('cost_of_sales', 'Cost of Sales'),  # 5
        ('revenue', 'Revenue'),  # 6
        ('general_expenses', 'General Expenses'),  # 7
    ]
    
    # Maps account type to number prefix for validation
    TYPE_PREFIX_MAP = {
        'asset': '1',
        'liability': '2',
        'equity': '3',
        'sales': '4',
        'cost_of_sales': '5',
        'revenue': '6',
        'general_expenses': '7',
    }
    
    # Reverse map: prefix to type
    PREFIX_TYPE_MAP = {v: k for k, v in TYPE_PREFIX_MAP.items()}
    
    # Account types where balance = opening + debit - credit
    DEBIT_BALANCE_TYPES = {'asset', 'cost_of_sales', 'general_expenses'}
    
    # Account types where balance = opening + credit - debit
    CREDIT_BALANCE_TYPES = {'liability', 'equity', 'sales', 'revenue'}

    # 1,2,3 are for Balance Sheet accounts 
    # 4,5,6,7 are for P&L accounts
    # 4-5 = gross profit,
    # revenue - general expense = operating profit,
    # 4-5+6-7 = net profit/net loss
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    account_number = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    parent_account = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='sub_accounts'
    )
    is_posting = models.BooleanField(
        default=True,
        help_text="Only posting accounts can receive journal entries. Parent accounts must be non-posting."
    )
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['account_number']

    def get_depth(self):
        """
        Calculate the depth of this account in the hierarchy.
        Level 1 = no parent (Type account)
        Level 2 = has parent, parent has no parent (Parent account)
        Level 3 = has parent, parent has parent (Child/Leaf account)
        """
        depth = 1
        current = self
        while current.parent_account:
            depth += 1
            current = current.parent_account
            if depth > 3:
                # Safety check to prevent infinite loops
                break
        return depth
    
    def get_root_account(self):
        """Get the root (type-level) account of this hierarchy."""
        current = self
        while current.parent_account:
            current = current.parent_account
        return current
    
    @staticmethod
    def get_type_from_account_number(account_number):
        """
        Derive account type from account number prefix.
        Returns the account type string or None if invalid.
        """
        if not account_number:
            return None
        prefix = account_number[0]
        return Account.PREFIX_TYPE_MAP.get(prefix)

    def clean(self):
        """
        Validate account according to Chart of Accounts rules.
        
        Validations:
        1. Account number is required
        2. Account number prefix must match account type
        3. Maximum hierarchy depth is 3 levels
        4. Parent account must be non-posting
        5. Child account number must follow parent prefix
        6. Account type must be consistent within hierarchy
        7. is_posting rules based on depth
        """
        errors = {}
        
        # 1. Account number is required
        if not self.account_number:
            errors['account_number'] = "Account number is required."
        else:
            # 2. Validate account number prefix matches type
            expected_prefix = self.TYPE_PREFIX_MAP.get(self.type)
            if expected_prefix and not self.account_number.startswith(expected_prefix):
                errors['account_number'] = (
                    f"Account number must start with '{expected_prefix}' for type '{self.type}'. "
                    f"Got: '{self.account_number}'"
                )
        
        # 3. Validate hierarchy depth (max 3 levels)
        if self.parent_account:
            # Calculate what the depth would be
            parent_depth = self.parent_account.get_depth()
            my_depth = parent_depth + 1
            
            if my_depth > 3:
                errors['parent_account'] = (
                    f"Maximum hierarchy depth is 3 levels. "
                    f"Parent '{self.parent_account.name}' is at depth {parent_depth}."
                )
            
            # 4. Parent account must be non-posting
            if self.parent_account.is_posting:
                errors['parent_account'] = (
                    f"Parent account '{self.parent_account.name}' must be non-posting. "
                    f"Only leaf (child) accounts can be posting accounts."
                )
            
            # 5. Child account number must follow parent prefix
            if self.account_number and self.parent_account.account_number:
                # Child number should start with a pattern derived from parent
                # E.g., parent 1.1000 -> children should be 1.1xxx
                parent_num = self.parent_account.account_number
                # Extract common prefix (first 3 chars for parent-child relationship)
                # 1.0000 -> children start with 1.
                # 1.1000 -> children start with 1.1
                if '.' in parent_num:
                    # Parent is type level (X.0000) or sub-level (X.Y000)
                    parent_prefix = parent_num.split('.')[0] + '.'
                    if not self.account_number.startswith(parent_prefix):
                        errors['account_number'] = (
                            f"Child account number must start with parent prefix '{parent_prefix}'. "
                            f"Got: '{self.account_number}'"
                        )
            
            # 6. Account type must match parent type
            if self.type != self.parent_account.type:
                errors['type'] = (
                    f"Account type must match parent account type. "
                    f"Parent type is '{self.parent_account.type}', got '{self.type}'."
                )
        
        # 7. Validate is_posting based on depth
        depth = 1
        if self.parent_account:
            depth = self.parent_account.get_depth() + 1
        
        # Type and Parent levels (depth 1 and 2) must be non-posting
        if depth < 3 and self.is_posting:
            # Check if this account has any children - if not, it can be posting
            # This allows leaf accounts at any level to be posting
            has_children = False
            if self.pk:
                has_children = self.sub_accounts.exists()
            
            if has_children:
                errors['is_posting'] = (
                    f"Accounts with sub-accounts must be non-posting. "
                    f"This account has child accounts."
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def closing_balance(self):
        """
        Calculate closing balance based on account type.
        
        Debit-normal accounts (Asset, Cost of Sales, General Expenses):
            closing = opening + debit - credit
            
        Credit-normal accounts (Liability, Equity, Sales, Revenue):
            closing = opening + credit - debit
        """
        debit_total = self.journalline_set.aggregate(
            total=Coalesce(Sum('debit'), Value(0), output_field=DecimalField())
        )['total'] or Decimal(0)

        credit_total = self.journalline_set.aggregate(
            total=Coalesce(Sum('credit'), Value(0), output_field=DecimalField())
        )['total'] or Decimal(0)

        if self.type in self.DEBIT_BALANCE_TYPES:
            # Asset, Cost of Sales, General Expenses: opening + debit - credit
            return self.opening_balance + debit_total - credit_total
        else:
            # Liability, Equity, Sales, Revenue: opening + credit - debit
            return self.opening_balance + credit_total - debit_total

    def __str__(self):
        posting_indicator = "(POSTING)" if self.is_posting else "(NON-POSTING)"
        return f"{posting_indicator} {self.account_number} - {self.name} ({self.type})"


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
        ('tax_payment', 'Tax Payment'),
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
    """
    Individual line in a journal entry (double-entry accounting).
    
    POSTING RULES:
    - Can only post to accounts where is_posting=True
    - Cannot have both debit and credit amounts
    - Must have either debit or credit > 0
    """
    journal = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


    def clean(self):
        """
        Validate journal line according to accounting rules.
        
        Validations:
        1. Cannot post to non-posting accounts
        2. Cannot have both debit and credit
        3. Must have either debit or credit > 0
        """
        errors = {}
        
        # 1. Validate account is a posting account
        if self.account_id:
            # Use account_id to avoid extra DB query if account is already loaded
            try:
                account = self.account
                if not account.is_posting:
                    errors['account'] = (
                        f"Cannot post to non-posting account '{account.name}'. "
                        f"Only posting (leaf) accounts can receive journal entries."
                    )
            except Account.DoesNotExist:
                errors['account'] = "Invalid account specified."
        
        # 2. Cannot have both debit and credit
        if self.debit > 0 and self.credit > 0:
            errors['__all__'] = "A line cannot have both debit and credit."
        
        # 3. Must have either debit or credit > 0
        if self.debit == 0 and self.credit == 0:
            errors['__all__'] = "Either debit or credit must be greater than zero."
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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
        return f"{self.product} ({self.quantity})"


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
        return f"{self.product} ({self.quantity})"


class CashflowCategoryMapping(models.Model):
    CATEGORY_CHOICES = [
        ('operating', 'Operating'),
        ('investing', 'Investing'),
        ('financing', 'Financing'),
    ]

    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    sub_category = models.CharField(max_length=100)
    accounts = models.ManyToManyField(Account, related_name='cashflow_categories')

    class Meta:
        unique_together = ('category', 'sub_category')


    def __str__(self):
        return f"{self.category.title()} - {self.sub_category}"



class TaxSettings(models.Model):
    name = models.CharField(max_length=100, unique=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.rate}%"

