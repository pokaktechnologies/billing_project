from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .utils import create_log, get_current_user
from .models import ActivityLog


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):

    if sender == ActivityLog:
        return

    user = get_current_user()

    if not user:
        return

    action = "CREATE" if created else "UPDATE"

    create_log(user, action, instance)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):

    if sender == ActivityLog:
        return

    user = get_current_user()

    if not user:
        return

    create_log(user, "DELETE", instance)