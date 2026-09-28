import csv
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

from apps.transactions.models import Transaction


def day_start(d):
    return timezone.make_aware(datetime.combine(d, time.min))


def history_queryset(user, *, account=None, date_from=None, date_to=None, entry_type=None,
                     min_amount=None, max_amount=None, q=None):
    qs = Transaction.objects.filter(account__customer__user=user).select_related("transfer", "account")
    if account is not None:
        qs = qs.filter(account=account)
    if date_from:
        qs = qs.filter(created_at__gte=day_start(date_from))
    if date_to:
        qs = qs.filter(created_at__lt=day_start(date_to) + timedelta(days=1))
    if entry_type:
        qs = qs.filter(entry_type=entry_type)
    if min_amount is not None:
        qs = qs.filter(amount__gte=min_amount)
    if max_amount is not None:
        qs = qs.filter(amount__lte=max_amount)
    if q:
        qs = qs.filter(Q(transfer__reference_number__icontains=q) | Q(transfer__remarks__icontains=q))
    return qs.order_by("-created_at", "-id")


@dataclass
class Statement:
    account: object
    date_from: object
    date_to: object
    opening_balance: Decimal
    closing_balance: Decimal
    rows: list


def build_statement(user, account, date_from, date_to):
    """Ownership enforced by queryset. Renderers (HTML/CSV now, PDF later) consume this dataclass."""
    base = Transaction.objects.filter(account=account, account__customer__user=user)
    before = base.filter(created_at__lt=day_start(date_from)).order_by("-created_at", "-id").first()
    opening = before.balance_after if before else Decimal("0.00")
    rows = list(base.filter(created_at__gte=day_start(date_from), created_at__lt=day_start(date_to) + timedelta(days=1))
                .select_related("transfer").order_by("created_at", "id"))
    closing = rows[-1].balance_after if rows else opening
    return Statement(account, date_from, date_to, opening, closing, rows)


def _safe(v):  # CSV formula-injection guard
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


def statement_csv(st):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="statement_{st.account.account_number[-4:]}_{st.date_from}_{st.date_to}.csv"'
    w = csv.writer(resp)
    w.writerow(["Account", st.account.masked_number, "From", st.date_from, "To", st.date_to])
    w.writerow(["Opening balance", st.opening_balance])
    w.writerow(["Date", "Reference", "Type", "Remarks", "Debit", "Credit", "Balance"])
    for r in st.rows:
        w.writerow([r.created_at.strftime("%d-%m-%Y %H:%M"), r.transfer.reference_number, r.transfer.transfer_type,
                    _safe(r.transfer.remarks), r.amount if r.entry_type == "DEBIT" else "",
                    r.amount if r.entry_type == "CREDIT" else "", r.balance_after])
    w.writerow(["Closing balance", st.closing_balance])
    return resp
