from .models import ActivityLog

def log_activity(lead, activity_type, action, model=None, obj_id=None):
    ActivityLog.objects.create(
        lead=lead,
        activity_type=activity_type,
        action=action,
        related_model=model,
        related_id=obj_id,
    )
