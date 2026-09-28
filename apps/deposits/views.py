from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import customer_required
from apps.core.http import Link, form_page, page
from apps.core.utils import inr

from .forms import OpenDepositForm
from .models import DepositAccount
from .services import DepositError, calculate_maturity, close_premature, open_deposit


@customer_required
def deposit_list(request):
    deposits = DepositAccount.objects.filter(customer__user=request.user).select_related("scheme")
    return render(request, "deposits/deposit_list.html", {"deposits": deposits})


@customer_required
def deposit_open(request):
    form = OpenDepositForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        if request.POST.get("preview"):
            preview = inr(calculate_maturity(d["scheme"].scheme_type, d["amount"], d["scheme"].interest_rate, d["tenure_months"]))
            messages.info(request, f"Estimated maturity amount: {preview}")
        else:
            try:
                dep = open_deposit(user=request.user, scheme_id=d["scheme"].pk, amount=d["amount"], tenure=d["tenure_months"],
                                   linked_account=d["linked_account"], request=request)
                messages.success(request, "Deposit opened.")
                return redirect("deposits:detail", pk=dep.pk)
            except DepositError as e:
                form.add_error(None, str(e))
    return render(request, "deposits/deposit_open.html", {"form": form})


@customer_required
def deposit_detail(request, pk):
    d = get_object_or_404(DepositAccount.objects.select_related("scheme", "linked_account", "linked_account__account_type"), pk=pk, customer__user=request.user)
    return render(request, "deposits/deposit_detail.html", {"deposit": d})


@customer_required
@require_POST
def deposit_close(request, pk):
    try:
        _, payout = close_premature(user=request.user, deposit_id=pk, request=request)
        messages.success(request, f"Closed. {inr(payout)} credited.")
    except (DepositError, DepositAccount.DoesNotExist) as e:
        messages.error(request, str(e) if isinstance(e, DepositError) else "Not found.")
    return redirect("deposits:list")
