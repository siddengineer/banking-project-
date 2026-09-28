from .models import AuditLog

FORBIDDEN_KEYS = {"password", "otp", "cvv", "pin", "aadhaar", "aadhaar_number", "pan", "pan_number", "token", "session"}


class Actions:
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    BENEFICIARY_CREATED = "BENEFICIARY_CREATED"
    BENEFICIARY_UPDATED = "BENEFICIARY_UPDATED"
    BENEFICIARY_DISABLED = "BENEFICIARY_DISABLED"
    TRANSFER_INITIATED = "TRANSFER_INITIATED"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    TRANSFER_FAILED = "TRANSFER_FAILED"
    CARD_DISABLED = "CARD_DISABLED"
    CARD_ENABLED = "CARD_ENABLED"
    CARD_BLOCKED = "CARD_BLOCKED"
    CARD_SETTINGS_CHANGED = "CARD_SETTINGS_CHANGED"
    STATEMENT_GENERATED = "STATEMENT_GENERATED"
    LOAN_APPLIED = "LOAN_APPLIED"
    LOAN_APPROVED = "LOAN_APPROVED"
    LOAN_REJECTED = "LOAN_REJECTED"
    LOAN_DISBURSED = "LOAN_DISBURSED"
    DEPOSIT_OPENED = "DEPOSIT_OPENED"
    DEPOSIT_CLOSED = "DEPOSIT_CLOSED"
    SERVICE_REQUEST_CREATED = "SERVICE_REQUEST_CREATED"
    SERVICE_REQUEST_UPDATED = "SERVICE_REQUEST_UPDATED"
    ADMIN_ACTION = "ADMIN_ACTION"


def _clean(meta):
    return {k: v for k, v in (meta or {}).items() if k.lower() not in FORBIDDEN_KEYS}


def log_event(action, *, user=None, entity_type="", entity_id="", metadata=None, request=None):
    ip = request.META.get("REMOTE_ADDR") if request is not None else None
    if user is not None and not getattr(user, "pk", None):
        user = None
    return AuditLog.objects.create(
        user=user, action=action, entity_type=entity_type, entity_id=str(entity_id or ""),
        ip_address=ip or None, metadata=_clean(metadata),
    )
