from datetime import timedelta
import uuid

from django.contrib import messages
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.audit.services import Actions, log_event
from apps.core.decorators import customer_required
from apps.core.http import Link, form_page, page, paginate
from apps.core.utils import inr
from apps.users.services.otp import OTPError, issue_otp

from .forms import HistoryFilterForm, OTPForm, StatementForm, TransferForm
from .models import Transfer
from .services import history
from .services.transfer_service import TransferError, confirm_transfer, create_transfer_intent


def _demo_otp(request, code):
    if settings.DEMO_SHOW_OTP:
        messages.info(request, f"DEMO MODE - your OTP is {code}")


@customer_required
def transfer_new(request):
    if request.method == "POST":
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            d = form.cleaned_data
            try:
                tr, created = create_transfer_intent(
                    user=request.user, from_account=d["from_account"], amount=d["amount"], transfer_type=d["transfer_type"],
                    to_account=d.get("to_account"), beneficiary=d.get("beneficiary"), mode=d.get("mode") or "",
                    remarks=d.get("remarks") or "", idempotency_key=d["idempotency_key"])
            except TransferError as e:
                form.add_error(None, str(e))
            else:
                if created:
                    _demo_otp(request, issue_otp(request.user, "TRANSFER", context=tr.reference_number))
                return redirect("transactions:transfer_verify", reference=tr.reference_number)
    else:
        form = TransferForm(user=request.user, initial={"idempotency_key": uuid.uuid4().hex})
    return render(request, "transactions/transfer_new.html", {"form": form})


@customer_required
def transfer_verify(request, reference):
    tr = get_object_or_404(Transfer.objects.select_related("from_account", "to_account", "beneficiary", "from_account__account_type"),
                           reference_number=reference, initiated_by=request.user)
    if tr.status != "PENDING":
        return redirect("transactions:transfer_receipt", reference=reference)
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            confirm_transfer(user=request.user, reference=reference, otp_code=form.cleaned_data["otp"], request=request)
            return redirect("transactions:transfer_receipt", reference=reference)
        except OTPError as e:
            form.add_error("otp", str(e))
    dest = tr.beneficiary or tr.to_account
    return render(request, "transactions/transfer_verify.html", {
        "transfer": tr,
        "form": form,
        "dest": dest,
    })


@customer_required
@require_POST
def transfer_resend(request, reference):
    tr = get_object_or_404(Transfer, reference_number=reference, initiated_by=request.user, status="PENDING")
    _demo_otp(request, issue_otp(request.user, "TRANSFER", context=tr.reference_number))
    return redirect("transactions:transfer_verify", reference=reference)


@customer_required
def transfer_receipt(request, reference):
    tr = get_object_or_404(Transfer.objects.select_related("from_account", "to_account", "beneficiary", "from_account__branch", "from_account__account_type", "to_account__account_type"),
                           reference_number=reference, initiated_by=request.user)
    dest = tr.beneficiary or tr.to_account
    return render(request, "transactions/transfer_receipt.html", {
        "transfer": tr,
        "dest": dest,
    })


@customer_required
def transaction_history(request):
    form = HistoryFilterForm(request.GET or None, user=request.user)
    if not request.GET:
        form = HistoryFilterForm(user=request.user)
        qs = history.history_queryset(request.user, date_from=timezone.localdate() - timedelta(days=30))
    elif form.is_valid():
        qs = history.history_queryset(request.user, **form.cleaned_data)
    else:
        qs = history.history_queryset(request.user).none()
    p, qstr = paginate(request, qs, 20)
    rows = [[t.created_at.strftime("%d-%m-%Y %H:%M"), t.transfer.reference_number, t.transfer.transfer_type,
             t.account.masked_number, t.entry_type, inr(t.amount), inr(t.balance_after), t.status] for t in p]
    return page(request, "Transactions", filter_form=form, page_obj=p, querystring=qstr,
                table={"headers": ["Date", "Reference", "Type", "Account", "Dr/Cr", "Amount", "Balance", "Status"], "rows": rows})


@customer_required
def statement(request):
    form = StatementForm(request.GET or None, user=request.user)
    if request.GET and form.is_valid():
        d = form.cleaned_data
        st = history.build_statement(request.user, d["account"], d["date_from"], d["date_to"])
        log_event(Actions.STATEMENT_GENERATED, user=request.user, entity_type="BankAccount", entity_id=d["account"].pk,
                  metadata={"from": str(d["date_from"]), "to": str(d["date_to"])}, request=request)
        if d["format"] == "csv":
            return history.statement_csv(st)
        rows = [[r.created_at.strftime("%d-%m-%Y"), r.transfer.reference_number, r.transfer.remarks,
                 inr(r.amount) if r.entry_type == "DEBIT" else "", inr(r.amount) if r.entry_type == "CREDIT" else "",
                 inr(r.balance_after)] for r in st.rows]
        return page(request, f"Statement {st.account.masked_number}",
                    details=[("Period", f"{st.date_from:%d-%m-%Y} to {st.date_to:%d-%m-%Y}"), ("Opening", inr(st.opening_balance)), ("Closing", inr(st.closing_balance))],
                    table={"headers": ["Date", "Reference", "Remarks", "Debit", "Credit", "Balance"], "rows": rows})
    return form_page(request, "Account statement", form, "Generate", method="get")
