from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import Actions, log_event
from apps.core.utils import add_months, inr, money, random_digits
from apps.notifications.services import notify
from apps.transactions.services.transfer_service import TransferError, move_funds
from apps.transactions.services.treasury import get_treasury_account

from .models import LoanAccount, LoanApplication, LoanInstallment

A = LoanApplication.Status


class LoanError(Exception):
    pass


def calc_emi(principal, annual_rate, months):
    P, n = Decimal(principal), int(months)
    r = Decimal(annual_rate) / Decimal(1200)
    if r == 0:
        return money(P / n)
    f = (1 + r) ** n
    return money(P * r * f / (f - 1))


def build_schedule(principal, annual_rate, months, first_due):
    """Reducing-balance schedule; final instalment absorbs rounding."""
    bal, r, emi, rows = Decimal(principal), Decimal(annual_rate) / Decimal(1200), calc_emi(principal, annual_rate, months), []
    for i in range(1, months + 1):
        interest = money(bal * r)
        principal_part = bal if i == months else money(emi - interest)
        total = principal_part + interest
        rows.append((i, add_months(first_due, i - 1), principal_part, interest, total))
        bal -= principal_part
    return emi, rows


@transaction.atomic
def submit_application(*, customer, loan_type, amount, tenure, purpose, request=None):
    if LoanApplication.objects.filter(customer=customer, status__in=[A.SUBMITTED, A.UNDER_REVIEW]).exists():
        raise LoanError("You have an application under review.")
    app = LoanApplication.objects.create(customer=customer, loan_type=loan_type, amount_requested=amount, tenure_months=tenure,
                                         purpose=purpose, status=A.SUBMITTED, applied_at=timezone.now())
    log_event(Actions.LOAN_APPLIED, user=customer.user, entity_type="LoanApplication", entity_id=app.pk, request=request)
    return app


@transaction.atomic
def review_application(*, application_id, employee, reviewer_user, approve, sanctioned_amount=None, sanctioned_rate=None,
                       remarks="", rejection_reason="", request=None):
    app = LoanApplication.objects.select_for_update().select_related("loan_type", "customer__user").get(pk=application_id)
    if app.status not in (A.SUBMITTED, A.UNDER_REVIEW):
        raise LoanError("Application is not awaiting review.")
    if approve:
        amt = money(sanctioned_amount if sanctioned_amount is not None else app.amount_requested)
        lt = app.loan_type
        if not lt.min_amount <= amt <= lt.max_amount:
            raise LoanError("Sanctioned amount outside product limits.")
        app.status, app.sanctioned_amount = A.APPROVED, amt
        app.sanctioned_rate = sanctioned_rate if sanctioned_rate is not None else lt.interest_rate
        action = Actions.LOAN_APPROVED
    else:
        if len((rejection_reason or "").strip()) < 5:
            raise LoanError("A rejection reason is mandatory.")
        app.status, app.rejection_reason = A.REJECTED, rejection_reason.strip()
        action = Actions.LOAN_REJECTED
    app.admin_remarks, app.reviewed_by, app.reviewed_at = remarks, employee, timezone.now()
    app.save()
    log_event(action, user=reviewer_user, entity_type="LoanApplication", entity_id=app.pk, request=request)
    notify(app.customer.user, "Loan application update", f"Your loan application LA-{app.pk} was {app.get_status_display().lower()}.", "LOAN")
    return app


@transaction.atomic
def disburse_loan(*, application_id, account, reviewer_user, request=None):
    """Idempotent: a second call raises 'Already disbursed'. Credits customer via the ledger."""
    app = LoanApplication.objects.select_for_update().select_related("customer__user").get(pk=application_id)
    if hasattr(app, "loan_account"):
        raise LoanError(f"Already disbursed ({app.loan_account.account_number}).")
    if app.status != A.APPROVED:
        raise LoanError("Only approved applications can be disbursed.")
    if account.customer_id != app.customer_id or account.status != "ACTIVE":
        raise LoanError("Disbursal account must be an active account of the applicant.")
    try:
        tr = move_funds(from_account=get_treasury_account(), to_account=account, amount=app.sanctioned_amount,
                        transfer_type="INTERNAL", initiated_by=reviewer_user, remarks=f"Loan disbursal LA-{app.pk}")
    except TransferError as e:
        raise LoanError(str(e))
    emi, rows = build_schedule(app.sanctioned_amount, app.sanctioned_rate, app.tenure_months, add_months(timezone.localdate(), 1))
    loan = LoanAccount.objects.create(application=app, account_number="LN" + random_digits(10), customer=app.customer,
                                      disbursed_amount=app.sanctioned_amount, interest_rate=app.sanctioned_rate,
                                      tenure_months=app.tenure_months, emi_amount=emi, disbursed_at=timezone.now())
    LoanInstallment.objects.bulk_create([LoanInstallment(loan_account=loan, installment_no=i, due_date=d, principal_amount=p,
                                                         interest_amount=it, total_amount=t) for i, d, p, it, t in rows])
    log_event(Actions.LOAN_DISBURSED, user=reviewer_user, entity_type="LoanAccount", entity_id=loan.pk,
              metadata={"amount": str(app.sanctioned_amount)}, request=request)
    notify(app.customer.user, "Loan disbursed", f"{inr(app.sanctioned_amount)} credited to {account.masked_number}.", "LOAN")
    return loan


def run_due_installments(today=None):
    """Job: debit EMIs due on/before today. Insufficient funds -> installment FAILED + notification."""
    today, paid, failed = today or timezone.localdate(), 0, 0
    for inst_id in list(LoanInstallment.objects.filter(status="PENDING", due_date__lte=today).values_list("pk", flat=True)):
        with transaction.atomic():
            inst = LoanInstallment.objects.select_for_update().select_related("loan_account__customer__user").get(pk=inst_id)
            if inst.status != "PENDING":
                continue
            loan = inst.loan_account
            acct = loan.customer.accounts.filter(status="ACTIVE").order_by("-balance").first()
            try:
                if acct is None:
                    raise TransferError("No active account")
                with transaction.atomic():
                    tr = move_funds(from_account=acct, to_account=get_treasury_account(), amount=inst.total_amount,
                                    transfer_type="LOAN_EMI", initiated_by=loan.customer.user, remarks=f"EMI {inst.installment_no} {loan.account_number}")
                inst.status, inst.paid_at, inst.transaction = "PAID", timezone.now(), tr
                paid += 1
            except TransferError:
                inst.status = "FAILED"
                failed += 1
                notify(loan.customer.user, "EMI bounced", f"EMI {inst.installment_no} of {loan.account_number} failed (insufficient funds).", "LOAN")
            inst.save()
            if not loan.installments.exclude(status="PAID").exists():
                loan.status = "CLOSED"; loan.save(update_fields=["status", "updated_at"])
    return paid, failed
