from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


# Activity Log Service

def create_log(user, action, instance):
    from .models import ActivityLog

    #  double safety
    if not user or not user.is_authenticated:
        return

    name = user.get_full_name() if hasattr(user, "get_full_name") else str(user)

    log = ActivityLog.objects.create(
        user=user,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=instance.id,
        description=f"{instance.__class__.__name__} ({instance.id}) was {action.lower()} by {name}"
    )

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "activity_logs",
        {
            "type": "send_log",
            "data": {
                "id": log.id,
                "user": str(log.user),
                "action": log.action,
                "model": log.model_name,
                "description": log.description,
                "time": str(log.timestamp)
            }
        }
    )


from contextvars import ContextVar

_current_user = ContextVar("current_user", default=None)

def set_current_user(user):
    _current_user.set(user)

def get_current_user():
    return _current_user.get()