import logging

from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Notification

log = logging.getLogger(__name__)


def notify(user, title, message, notification_type=Notification.Type.GENERAL):
    """Best-effort: a notification failure must never block a financial action."""
    try:
        with transaction.atomic():  # savepoint
            return Notification.objects.create(user=user, title=title[:200], message=message, notification_type=notification_type)
    except Exception:  # noqa: BLE001
        log.exception("notification failed")
        return None


def broadcast_announcement(announcement):
    users = get_user_model().objects.filter(is_active=True, customerprofile__isnull=False)
    Notification.objects.bulk_create(
        [Notification(user=u, title=announcement.title[:200], message=announcement.body[:1000], notification_type="GENERAL") for u in users],
        batch_size=500,
    )
    return users.count()
