
import logging
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.db import close_old_connections

logger = logging.getLogger("scheduler")


def send_lead_notification(notification):
    """
    Send notification through WebSocket to the assigned salesperson.
    Database notification is already saved before this function runs.
    """

    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()

        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            f"lead_notifications_{notification.user_id}",
            {
                "type": "notification_message",
                "data": {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "notification_type": notification.notification_type,
                    "is_read": notification.is_read,
                    "followup_id": notification.followup_id,
                    "created_at": notification.created_at.isoformat(),
                }
            }
        )

    except Exception:
        logger.exception(
            "WebSocket delivery failed for notification %s",
            notification.id
        )


def create_followup_notification(followup, notification_type):
    """
    Create a notification only once for a particular follow-up.
    """

    from leads.models import Notification

    try:
        salesperson = followup.lead.salesperson
        user = salesperson.assigned_staff.user

        if not user or not user.is_active:
            return

        if notification_type == "followup_today":
            title = "You have a follow-up today!"
            message = (
                f"{followup.title} with {followup.lead.name}. "
                f"Scheduled at {followup.time.strftime('%I:%M %p')}."
            )

        elif notification_type == "followup_5_min":
            title = "Follow-up starting in 5 minutes!"
            message = (
                f"Your {followup.title} with {followup.lead.name} "
                f"starts in 5 minutes."
            )

        else:
            return

        notification, created = Notification.objects.get_or_create(
            user=user,
            followup=followup,
            notification_type=notification_type,
            defaults={
                "title": title,
                "message": message,
            }
        )

        if created:
            send_lead_notification(notification)

            logger.info(
                "Lead notification created: %s | User: %s | FollowUp: %s",
                notification_type,
                user.id,
                followup.id
            )

    except Exception:
        logger.exception(
            "Failed to create notification for follow-up %s",
            followup.id
        )


def create_daily_followup_notifications():
    """
    Runs daily at 9 AM.
    Creates today's follow-up notifications.
    """

    close_old_connections()

    try:
        from leads.models import FollowUp

        today = timezone.localdate()

        followups = FollowUp.objects.filter(
            date=today,
            status="new"
        ).select_related(
            "lead__salesperson__assigned_staff__user"
        )

        for followup in followups:
            create_followup_notification(
                followup,
                "followup_today"
            )

        logger.info(
            "Daily lead follow-up notification job completed for %s",
            today
        )

    except Exception:
        logger.exception("Daily follow-up notification job failed")

    finally:
        close_old_connections()


def check_followup_reminders():
    """
    Runs every minute.

    Sends reminders when a follow-up is within its final
    5 minutes, provided its scheduled time has not passed.
    """

    close_old_connections()

    try:
        from leads.models import FollowUp

        now = timezone.localtime()

        followups = FollowUp.objects.filter(
            date=now.date(),
            status="new"
        ).select_related(
            "lead__salesperson__assigned_staff__user"
        )

        for followup in followups:

            followup_datetime = timezone.make_aware(
                datetime.combine(
                    followup.date,
                    followup.time
                ),
                timezone.get_current_timezone()
            )

            reminder_time = followup_datetime - timedelta(minutes=5)

            # Only send when the reminder time has arrived
            # and the actual follow-up has not started.
            if reminder_time <= now < followup_datetime:

                create_followup_notification(
                    followup,
                    "followup_5_min"
                )

        logger.info(
            "Follow-up reminder check completed at %s",
            now
        )

    except Exception:
        logger.exception("Follow-up reminder check failed")

    finally:
        close_old_connections()
