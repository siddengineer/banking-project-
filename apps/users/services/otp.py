"""Demo OTP service. Only an HMAC is stored, never the code."""
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.users.models import OTPVerification

log = logging.getLogger(__name__)


class OTPError(Exception):
    pass


def _digest(user, purpose, context, code):
    # bound to user + purpose + context (e.g. transfer reference)
    return salted_hmac("bnb.otp.v1", f"{user.pk}|{purpose}|{context}|{code}").hexdigest()


def issue_otp(user, purpose, context=""):
    """Creates a fresh OTP (older unused ones for this user+purpose are invalidated). Returns the plaintext
    code so the *caller* can show it in demo mode; it is never persisted."""
    code = f"{secrets.randbelow(10**6):06d}"
    now = timezone.now()
    with transaction.atomic():
        OTPVerification.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=now)
        OTPVerification.objects.create(
            user=user, purpose=purpose, hashed_otp=_digest(user, purpose, context, code),
            created_at=now, expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
        )
    if settings.DEBUG:  # dev-only delivery; never in production
        send_mail("BNB demo OTP", f"Your demo OTP is {code}", "noreply@bnb.demo", [user.email], fail_silently=True)
        log.debug("DEMO OTP issued purpose=%s user=%s code=%s", purpose, user.pk, code)
    return code


def verify_otp(user, purpose, code, context=""):
    """Returns (record, error). Attempts are counted (and persisted) even when wrong."""
    code = (code or "").strip()
    with transaction.atomic():
        rec = (OTPVerification.objects.select_for_update()
               .filter(user=user, purpose=purpose, used_at__isnull=True).order_by("-created_at", "-id").first())
        if rec is None:
            return None, "No active OTP. Please request a new one."
        if rec.expires_at <= timezone.now():
            return None, "OTP expired. Please request a new one."
        if rec.attempt_count >= rec.max_attempts:
            return None, "Too many wrong attempts. Please request a new OTP."
        rec.attempt_count += 1
        if code.isdigit() and len(code) == 6 and constant_time_compare(rec.hashed_otp, _digest(user, purpose, context, code)):
            rec.is_verified = True
            rec.verified_at = timezone.now()
            rec.save(update_fields=["attempt_count", "is_verified", "verified_at"])
            return rec, ""
        rec.save(update_fields=["attempt_count"])
        return None, "Invalid OTP."


def consume_otp(rec):
    """Single-use guarantee: atomic conditional update. Call inside the money transaction."""
    n = OTPVerification.objects.filter(pk=rec.pk, is_verified=True, used_at__isnull=True).update(used_at=timezone.now())
    if n != 1:
        raise OTPError("OTP already used.")
