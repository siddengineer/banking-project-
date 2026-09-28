from django.db import transaction
from django.utils import timezone

from apps.users.models import User

MAX_FAILED = 3


def register_failed_login(user):
    with transaction.atomic():
        u = User.objects.select_for_update().get(pk=user.pk)
        u.failed_login_attempts += 1
        newly_locked = False
        if u.failed_login_attempts >= MAX_FAILED and not u.is_locked:
            u.is_locked, u.locked_at, newly_locked = True, timezone.now(), True
        u.save(update_fields=["failed_login_attempts", "is_locked", "locked_at"])
    return newly_locked


def reset_failed_logins(user):
    User.objects.filter(pk=user.pk).update(failed_login_attempts=0)


def unlock(user):
    User.objects.filter(pk=user.pk).update(failed_login_attempts=0, is_locked=False, locked_at=None)
