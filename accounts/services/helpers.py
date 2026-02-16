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

    fk_fields = {'client', 'intern', 'course', 'termsandconditions'}

    updated = False

    for field in editable_fields:
        if field in data:
            # Use _id suffix for ForeignKeys to handle direct ID assignment from request
            target_field = f"{field}_id" if field in fk_fields else field
            setattr(invoice, target_field, data[field])
            updated = True

    if updated:
        invoice.save(update_fields=editable_fields)
