from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .utils import create_log, get_current_user

IGNORE_MODELS = [
    "ActivityLog",
    "CustomUser",
    "ModulePermission",
    "Notification",
    "UserSetting",
    "Feedback",
    
]


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):

    # Ignore models
    if sender.__name__ in IGNORE_MODELS:
        return

    user = get_current_user()

    if not user:
        return

    action = "CREATE" if created else "UPDATE"

    create_log(user, action, instance)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):

    if sender.__name__ in IGNORE_MODELS:
        return

    user = get_current_user()

    if not user:
        return

    create_log(user, "DELETE", instance)