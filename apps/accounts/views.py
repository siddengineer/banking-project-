from django.shortcuts import get_object_or_404, render

from apps.core.decorators import customer_required
from apps.core.http import Link, page
from apps.core.utils import inr

from .models import BankAccount


def _own_accounts(user):
    return BankAccount.objects.filter(customer__user=user).select_related("account_type", "branch")


@customer_required
def account_list(request):
    accounts = _own_accounts(request.user)
    return render(request, "accounts/account_list.html", {"accounts": accounts})


@customer_required
def account_detail(request, account_number):
    # Ownership enforced in the queryset; foreign IDs give 404 (no enumeration).
    a = get_object_or_404(_own_accounts(request.user), account_number=account_number)
    banner = "Account is not active - contact your branch." if a.status != "ACTIVE" else ""
    transactions = a.ledger.select_related("transfer").order_by("-created_at")[:15]
    return render(request, "accounts/account_detail.html", {
        "account": a,
        "banner": banner,
        "transactions": transactions,
    })
