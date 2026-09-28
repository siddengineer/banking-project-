from decimal import Decimal

from django.db import transaction

from apps.core.utils import random_digits

from .models import BankAccount


def generate_account_number():
    for _ in range(50):
        n = random_digits(11)
        if n[0] != "0" and not BankAccount.objects.filter(account_number=n).exists():
            return n
    raise RuntimeError("Could not allocate an account number")


@transaction.atomic
def open_account(*, customer, account_type, branch, initiated_by, initial_deposit=Decimal("0"), account_number=None):
    """Opens an account; the initial deposit is a real ledger entry from the bank settlement account."""
    acct = BankAccount.objects.create(
        account_number=account_number or generate_account_number(), customer=customer,
        account_type=account_type, branch=branch, minimum_balance=account_type.min_balance,
    )
    if initial_deposit and Decimal(initial_deposit) > 0:
        from apps.transactions.services.transfer_service import move_funds
        from apps.transactions.services.treasury import get_treasury_account
        move_funds(from_account=get_treasury_account(), to_account=acct, amount=initial_deposit,
                   transfer_type="INTERNAL", initiated_by=initiated_by, remarks="Opening deposit")
        acct.refresh_from_db()
    return acct
