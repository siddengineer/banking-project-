from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import Actions, log_event
from apps.core.utils import add_months, inr, money
from apps.notifications.services import notify
from apps.transactions.services.transfer_service import TransferError, move_funds
from apps.transactions.services.treasury import get_treasury_account

from .models import DepositAccount, DepositScheme


class DepositError(Exception):
    pass


def calculate_maturity(scheme_type, amount, annual_rate, months):
    """Decimal only. FD: simple interest M = P(1 + r*t). RD: interest on each instalment for its remaining months."""
    a, r, n = Decimal(amount), Decimal(annual_rate) / Decimal(100), int(months)
    if scheme_type == "FD":
        return money(a + a * r * Decimal(n) / Decimal(12))
    return money(a * n + a * Decimal(n * (n + 1) // 2) * r / Decimal(12))


@transaction.atomic
def open_deposit(*, user, scheme_id, amount, tenure, linked_account, request=None):
    customer = user.customerprofile
    scheme = DepositScheme.objects.get(pk=scheme_id, is_active=True)
    amount = money(amount)
    if amount < scheme.min_amount:
        raise DepositError(f"Minimum amount is {inr(scheme.min_amount)}.")
    if not scheme.min_tenure_months <= tenure <= scheme.max_tenure_months:
        raise DepositError("Tenure outside allowed range.")
    if linked_account.customer_id != customer.pk or linked_account.status != "ACTIVE":
        raise DepositError("Invalid linked account.")
    try:
        move_funds(from_account=linked_account, to_account=get_treasury_account(), amount=amount, transfer_type="DEPOSIT",
                   initiated_by=user, remarks=f"{scheme.scheme_type} opening")
    except TransferError as e:
        raise DepositError(str(e))
    today = timezone.localdate()
    d = DepositAccount.objects.create(
        customer=customer, scheme=scheme, linked_account=linked_account,
        principal_amount=amount if scheme.scheme_type == "FD" else None,
        monthly_installment=amount if scheme.scheme_type == "RD" else None,
        interest_rate=scheme.interest_rate, tenure_months=tenure, start_date=today,
        maturity_date=add_months(today, tenure), maturity_amount=calculate_maturity(scheme.scheme_type, amount, scheme.interest_rate, tenure))
    log_event(Actions.DEPOSIT_OPENED, user=user, entity_type="DepositAccount", entity_id=d.pk, metadata={"amount": str(amount)}, request=request)
    notify(user, "Deposit opened", f"{scheme.name} opened. Matures {d.maturity_date:%d-%m-%Y}.", "ACCOUNT")
    return d


def _payout(d, amount, status, user, remarks):
    move_funds(from_account=get_treasury_account(), to_account=d.linked_account, amount=amount, transfer_type="DEPOSIT",
               initiated_by=user, remarks=remarks)
    d.status = status
    d.save(update_fields=["status", "updated_at"])


@transaction.atomic
def close_premature(*, user, deposit_id, request=None):
    """FD only. 1% p.a. penalty on the rate, pro-rata by elapsed days; <7 days not allowed."""
    d = DepositAccount.objects.select_for_update().select_related("scheme").get(pk=deposit_id, customer__user=user)
    if d.status != "ACTIVE":
        raise DepositError("Deposit is not active.")
    if d.scheme.scheme_type != "FD":
        raise DepositError("Premature closure is supported for fixed deposits only.")
    today = timezone.localdate()
    days = (today - d.start_date).days
    if days < 7:
        raise DepositError("Premature closure not allowed within 7 days.")
    if today >= d.maturity_date:
        payout, status = d.maturity_amount, "MATURED"
    else:
        eff = max(d.interest_rate - Decimal("1.00"), Decimal("0"))
        payout, status = money(d.principal_amount + d.principal_amount * eff / 100 * Decimal(days) / Decimal(365)), "CLOSED_PREMATURELY"
    try:
        _payout(d, payout, status, user, "FD premature closure")
    except TransferError as e:
        raise DepositError(str(e))
    log_event(Actions.DEPOSIT_CLOSED, user=user, entity_type="DepositAccount", entity_id=d.pk, metadata={"payout": str(payout)}, request=request)
    notify(user, "Deposit closed", f"{inr(payout)} credited to {d.linked_account.masked_number}.", "ACCOUNT")
    return d, payout


def run_due_deposits(today=None):
    today, n = today or timezone.localdate(), 0
    for pk in list(DepositAccount.objects.filter(status="ACTIVE", maturity_date__lte=today).values_list("pk", flat=True)):
        with transaction.atomic():
            d = DepositAccount.objects.select_for_update().select_related("customer__user").get(pk=pk)
            if d.status != "ACTIVE":
                continue
            try:
                _payout(d, d.maturity_amount, "MATURED", d.customer.user, "Deposit maturity payout")
                notify(d.customer.user, "Deposit matured", f"{inr(d.maturity_amount)} credited.", "ACCOUNT")
                n += 1
            except TransferError:
                pass  # e.g. frozen linked account: stays ACTIVE, retried next run
    return n
