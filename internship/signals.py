# signals.py

from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import TestQuestion

@receiver(post_delete, sender=TestQuestion)
def delete_question_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)