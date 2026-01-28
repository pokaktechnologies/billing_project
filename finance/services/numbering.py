from ..utils import generate_next_number
from ..models import Account, JournalEntry, CreditNote, DebitNote

def get_next_finance_number(model_type):
    model_map = {
        'ACT': (Account, 'account_number', 'ACT'),
        'JE': (JournalEntry, 'type_number', 'JE'),
        'CN': (CreditNote, 'credit_note_number', 'CN'),
        'DN': (DebitNote, 'debit_note_number', 'DN')
    }

    if model_type not in model_map:
        return None

    model, field_name, prefix = model_map[model_type]
    return generate_next_number(model, field_name, prefix, 6)
