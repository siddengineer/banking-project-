"""Money movement. All balance changes happen here, inside transaction.atomic() with row locks."""
import secrets
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import BankAccount
from apps.audit.services import Actions, log_event
from apps.beneficiaries.models import Beneficiary
from apps.core.utils import generate_reference, inr
from apps.notifications.services import notify
from apps.transactions.models import Transaction, Transfer
from apps.users.services.otp import OTPError, consume_otp, verify_otp

T = Transfer.Type
S = Transfer.Status


class TransferError(Exception):
    """Validation failure (user-facing message)."""


# ------------------------------------------------------------------ helpers
def clean_amount(amount):
    if isinstance(amount, float):
        raise TransferError("Invalid amount.")
    try:
        amt = Decimal(str(amount).strip()) if not isinstance(amount, Decimal) else amount
    except (InvalidOperation, ValueError):
        raise TransferError("Invalid amount.")
    if not amt.is_finite() or amt.as_tuple().exponent < -2:
        raise TransferError("Amount may have at most 2 decimal places.")
    if amt <= 0:
        raise TransferError("Amount must be greater than zero.")
    return amt


def _daily_total(account, exclude_pk=None):
    start = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))  # IST calendar day
    qs = Transfer.objects.filter(from_account=account, status__in=[S.SUCCESS, S.PROCESSING],
                                 created_at__gte=start, created_at__lt=start + timedelta(days=1))
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.aggregate(t=Sum("amount"))["t"] or Decimal("0")


def _limit_problem(transfer_type, amount, account, exclude_pk=None):
    lim = settings.TRANSFER_LIMITS
    cap = lim["EXTERNAL_MAX"] if transfer_type == T.EXTERNAL else lim["INTERNAL_MAX"]
    if amount < lim["MIN"]:
        return f"Minimum transfer is {inr(lim['MIN'])}."
    if amount > cap:
        return f"Exceeds per-transaction limit of {inr(cap)}."
    if _daily_total(account, exclude_pk) + amount > lim["DAILY_MAX"]:
        return "Exceeds daily transfer limit."
    return None


def _is_treasury(acct):
    return acct.account_number == settings.BNB_TREASURY_ACCOUNT_NUMBER


def _lock_accounts(*accounts):
    """Deterministic order (by primary key) avoids deadlocks between opposing transfers (A->B vs B->A)."""
    ids = sorted({a.pk for a in accounts if a is not None})
    return {a.pk: a for a in BankAccount.objects.select_for_update().filter(pk__in=ids).order_by("pk")}


def _post_legs(transfer, from_acc, to_acc):
    amt, now = transfer.amount, timezone.now()
    from_acc.balance -= amt
    from_acc.available_balance = from_acc.balance
    from_acc.save(update_fields=["balance", "available_balance", "updated_at"])
    Transaction.objects.create(transfer=transfer, account=from_acc, entry_type="DEBIT", amount=amt, balance_after=from_acc.balance)
    if to_acc is not None:
        to_acc.balance += amt
        to_acc.available_balance = to_acc.balance
        to_acc.save(update_fields=["balance", "available_balance", "updated_at"])
        Transaction.objects.create(transfer=transfer, account=to_acc, entry_type="CREDIT", amount=amt, balance_after=to_acc.balance)
    transfer.status, transfer.processed_at = S.SUCCESS, now
    transfer.save(update_fields=["status", "processed_at"])


def _fail(transfer, reason, request=None):
    transfer.status, transfer.failure_reason, transfer.processed_at = S.FAILED, reason[:255], timezone.now()
    transfer.save(update_fields=["status", "failure_reason", "processed_at"])
    log_event(Actions.TRANSFER_FAILED, user=transfer.initiated_by, entity_type="Transfer", entity_id=transfer.pk,
              metadata={"reference": transfer.reference_number, "reason": reason}, request=request)
    notify(transfer.initiated_by, "Transfer failed", f"{inr(transfer.amount)} transfer failed: {reason} (Ref {transfer.reference_number})", "TRANSACTION")


# ------------------------------------------------------------------ system movements (loans, deposits, opening balances)
def move_funds(*, from_account, to_account, amount, transfer_type, initiated_by, remarks=""):
    """Atomic internal ledger movement. Raises TransferError (and rolls back if nested) on any problem."""
    amount = clean_amount(amount)
    with transaction.atomic():
        locked = _lock_accounts(from_account, to_account)
        f, t = locked[from_account.pk], locked[to_account.pk]
        if f.pk == t.pk:
            raise TransferError("Cannot transfer to the same account.")
        if f.status != "ACTIVE" or t.status != "ACTIVE":
            raise TransferError("Account is not active.")
        if f.balance < amount:
            raise TransferError("Insufficient funds.")
        tr = Transfer.objects.create(
            reference_number=generate_reference("TXN"), transfer_type=transfer_type, from_account=f, to_account=t,
            amount=amount, status=S.PROCESSING, remarks=remarks[:140], initiated_by=initiated_by)
        _post_legs(tr, f, t)
    return tr


# ------------------------------------------------------------------ customer flow: intent -> OTP -> execute
def create_transfer_intent(*, user, from_account, amount, transfer_type, to_account=None, beneficiary=None,
                           mode="", remarks="", idempotency_key):
    """Validates everything server-side and stores a PENDING transfer. NO money moves here.
    Returns (transfer, created). Same idempotency_key -> same transfer, never a second one."""
    if not idempotency_key or len(idempotency_key) > 64:
        raise TransferError("Invalid request token.")
    existing = Transfer.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.initiated_by_id != user.id:
            raise TransferError("Invalid request token.")
        return existing, False

    customer = getattr(user, "customerprofile", None)
    if customer is None:
        raise TransferError("Not a customer.")
    amount = clean_amount(amount)
    if transfer_type not in (T.OWN, T.INTERNAL, T.EXTERNAL):
        raise TransferError("Unsupported transfer type.")
    # never trust posted objects: re-fetch scoped to the authenticated customer
    src = BankAccount.objects.filter(pk=getattr(from_account, "pk", None), customer=customer).first()
    if src is None:
        raise TransferError("Invalid source account.")
    if src.status != "ACTIVE":
        raise TransferError("Source account is not active.")
    remarks = (remarks or "").strip()
    if len(remarks) > 140:
        raise TransferError("Remarks too long.")

    dest, ben = None, None
    if transfer_type == T.OWN:
        dest = BankAccount.objects.filter(pk=getattr(to_account, "pk", None), customer=customer).first()
        if dest is None:
            raise TransferError("Invalid destination account.")
    else:
        ben = Beneficiary.objects.filter(pk=getattr(beneficiary, "pk", None), owner=customer, is_active=True,
                                         verification_status="VERIFIED").first()
        if ben is None:
            raise TransferError("Invalid or unverified beneficiary.")
        if transfer_type == T.INTERNAL:
            if ben.beneficiary_type != "INTERNAL":
                raise TransferError("Beneficiary is not a Bharat Nidhi Bank account.")
            dest = BankAccount.objects.filter(account_number=ben.account_number, branch__ifsc_code=ben.ifsc_code).first()
            if dest is None:
                raise TransferError("Beneficiary account not found.")
        else:
            if ben.beneficiary_type != "EXTERNAL":
                raise TransferError("Beneficiary is not an external account.")
            if mode not in ("IMPS", "NEFT", "RTGS"):
                raise TransferError("Choose IMPS, NEFT or RTGS.")
    if dest is not None:
        if dest.pk == src.pk:
            raise TransferError("Cannot transfer to the same account.")
        if dest.status != "ACTIVE" or _is_treasury(dest):
            raise TransferError("Destination account cannot receive funds.")
    problem = _limit_problem(transfer_type, amount, src)
    if problem:
        raise TransferError(problem)
    if src.available_balance < amount:
        raise TransferError("Insufficient funds.")

    try:
        with transaction.atomic():
            tr = Transfer.objects.create(
                reference_number=generate_reference("TXN"), transfer_type=transfer_type,
                mode=mode if transfer_type == T.EXTERNAL else "", from_account=src, to_account=dest, beneficiary=ben,
                amount=amount, status=S.PENDING, remarks=remarks, initiated_by=user, idempotency_key=idempotency_key)
            log_event(Actions.TRANSFER_INITIATED, user=user, entity_type="Transfer", entity_id=tr.pk,
                      metadata={"reference": tr.reference_number, "type": transfer_type, "amount": str(amount)})
    except IntegrityError:  # double-submit race on the unique idempotency key
        ex = Transfer.objects.filter(idempotency_key=idempotency_key, initiated_by=user).first()
        if ex:
            return ex, False
        raise
    return tr, True


def confirm_transfer(*, user, reference, otp_code, request=None):
    """Verify OTP, then execute atomically. Already-processed transfers are returned untouched (no double debit)."""
    tr = Transfer.objects.get(reference_number=reference, initiated_by=user)  # DoesNotExist -> 404 in view
    if tr.status != S.PENDING:
        return tr
    rec, err = verify_otp(user, "TRANSFER", otp_code, context=tr.reference_number)
    if rec is None:
        raise OTPError(err)
    return _execute(tr.pk, user, rec, request)


def _execution_problem(tr, user, f, t):
    if f.customer.user_id != user.id:
        return "Source account does not belong to you."
    if f.status != "ACTIVE":
        return "Source account is frozen or inactive."
    if t is not None and t.status != "ACTIVE":
        return "Destination account is not active."
    if tr.beneficiary_id:
        b = Beneficiary.objects.get(pk=tr.beneficiary_id)
        if not b.is_active or b.owner_id != f.customer_id or b.verification_status != "VERIFIED":
            return "Beneficiary is no longer valid."
    if tr.transfer_type == T.OWN and t.customer_id != f.customer_id:
        return "Destination is not your account."
    lp = _limit_problem(tr.transfer_type, tr.amount, f, exclude_pk=tr.pk)
    if lp:
        return lp
    if f.balance < tr.amount:
        return "Transaction declined - insufficient funds."
    return None


def _execute(pk, user, otp_rec, request=None):
    with transaction.atomic():
        tr = Transfer.objects.select_for_update().get(pk=pk, initiated_by=user)
        if tr.status != S.PENDING:
            return tr
        consume_otp(otp_rec)  # single-use, replay-safe
        locked = _lock_accounts(tr.from_account, tr.to_account)
        f, t = locked[tr.from_account_id], locked.get(tr.to_account_id)
        problem = _execution_problem(tr, user, f, t)
        if problem is None and tr.transfer_type == T.EXTERNAL and secrets.randbelow(10**6) < int(settings.EXTERNAL_FAILURE_RATE * 10**6):
            problem = "Network timeout at beneficiary bank (simulated)."  # nothing debited -> funds stay safe
        if problem:
            _fail(tr, problem, request)
            return tr
        tr.status = S.PROCESSING
        _post_legs(tr, f, t)
        log_event(Actions.TRANSFER_COMPLETED, user=user, entity_type="Transfer", entity_id=tr.pk,
                  metadata={"reference": tr.reference_number, "amount": str(tr.amount)}, request=request)
        notify(user, "Transfer successful", f"{inr(tr.amount)} sent. Ref {tr.reference_number}", "TRANSACTION")
        if t is not None and t.customer.user_id != user.id:
            notify(t.customer.user, "Money received", f"{inr(tr.amount)} credited. Ref {tr.reference_number}", "TRANSACTION")
    return tr
