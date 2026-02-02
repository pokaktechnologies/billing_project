# utils.py
def generate_next_number(model, field_name: str, prefix: str, length: int) -> str:
    start = 10**(length - 1) + 1

    latest_order = model.objects.filter(
        **{f"{field_name}__startswith": f"{prefix}|"}
    ).order_by(f"-{field_name}").first()

    if latest_order:
        latest_number_str = getattr(latest_order, field_name).split('|')[1]
        next_number = int(latest_number_str) + 1
    else:
        next_number = start

    return f"{prefix}|{next_number:0{length}d}"

JOURNAL_ACCOUNT_MAPPING = {
    'invoice': {'debit': 'Accounts Receivable', 'credit': 'Service Income'},
    'receipt': {'debit': 'Cash', 'credit': 'Accounts Receivable'},
    'receipt_tax': {'debit': 'Output Tax Control', 'credit': 'Output Tax Payable'},
    'credit_note': {'debit': 'Sales Returns', 'credit': 'Accounts Receivable'},
    'debit_note': {'debit': 'Accounts Payable', 'credit': 'Purchase Returns'},
}
