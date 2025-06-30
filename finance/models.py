from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser

# Chart of Accounts
class Account(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('equity', 'Equity'),
    ]
    account_number = models.CharField(max_length=100, blank=True, null=True, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.type}) - {self.account_number}"

# Journal Entry Header
class JournalEntry(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    journal_number = models.CharField(max_length=100, blank=True, null=True, unique=True)
    date = models.DateTimeField(default=timezone.now)
    description = models.TextField()
    reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def total_debit(self):
        return sum(line.debit for line in self.lines.all())

    def total_credit(self):
        return sum(line.credit for line in self.lines.all())

    def is_balanced(self):
        return round(self.total_debit(), 2) == round(self.total_credit(), 2)

    def clean(self):
        if self.pk and not self.is_balanced():
            raise ValidationError(
                f"Journal entry is not balanced. "
                f"Debit ₹{self.total_debit()} ≠ Credit ₹{self.total_credit()}"
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # Enforces model validation
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Entry #{self.id} on {self.date.date()} – {self.journal_number or 'No Number'}"


# Journal Line
class JournalLine(models.Model):
    journal = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def clean(self):
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A line cannot have both debit and credit.")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("Either debit or credit must be greater than zero.")

    def __str__(self):
        if self.debit > 0:
            return f"Dr ₹{self.debit} to {self.account.name} – {self.description or 'No description'} -- {self.journal.journal_number}"
        elif self.credit > 0:
            return f"Cr ₹{self.credit} from {self.account.name} – {self.description or 'No description'} -- {self.journal.journal_number}"
        return f"{self.account.name} – ₹0"
