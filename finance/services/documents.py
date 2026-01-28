from django.db import transaction
from ..models import CreditNote, CreditNoteItem, DebitNote, DebitNoteItem

def process_credit_note_creation(data, user):
    with transaction.atomic():
        items_data = data.pop('items')
        data['user'] = user
        credit_note = CreditNote.objects.create(**data)
        for item_data in items_data:
            CreditNoteItem.objects.create(credit_note=credit_note, **item_data)
        credit_note.update_grand_total()
        credit_note.create_or_update_journal_entry()
        return credit_note

def process_credit_note_update(instance, data):
    with transaction.atomic():
        items_data = data.pop('items', None)
        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                CreditNoteItem.objects.create(credit_note=instance, **item_data)
        instance.update_grand_total()
        instance.create_or_update_journal_entry()
        return instance

def process_debit_note_creation(data, user):
    with transaction.atomic():
        items_data = data.pop("items")
        data["user"] = user
        debit_note = DebitNote.objects.create(**data)
        for item_data in items_data:
            DebitNoteItem.objects.create(debit_note=debit_note, **item_data)
        debit_note.update_grand_total()
        debit_note.create_or_update_journal_entry()
        return debit_note

def process_debit_note_update(instance, data):
    with transaction.atomic():
        items_data = data.pop("items", None)
        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                DebitNoteItem.objects.create(debit_note=instance, **item_data)
        instance.update_grand_total()
        instance.create_or_update_journal_entry()
        return instance
