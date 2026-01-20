def update_invoice_header(invoice, data):
    """
    Updates only safe, editable invoice header fields.
    """
    editable_fields = [
        'client',
        "intern",
        "course",
        "remark",
        "invoice_date",
        "termsandconditions",
        "description",
    ]

    updated = False

    for field in editable_fields:
        if field in data:
            setattr(invoice, field, data[field])
            updated = True

    if updated:
        invoice.save(update_fields=editable_fields)
