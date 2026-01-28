from django.db import transaction
from ..models import JournalEntry, JournalLine

def create_journal_entry(data, user):
    with transaction.atomic():
        lines_data = data.pop('lines', [])
        data['user'] = user
        journal_entry = JournalEntry.objects.create(**data)
        for line in lines_data:
            JournalLine.objects.create(journal=journal_entry, **line)
        return journal_entry

def update_journal_entry(instance, data):
    with transaction.atomic():
        lines_data = data.pop('lines', None)
        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                JournalLine.objects.create(journal=instance, **line_data)
        return instance
