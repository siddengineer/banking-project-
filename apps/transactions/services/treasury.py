import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

from apps.accounts.models import AccountType, BankAccount, Branch
from apps.users.models import CustomerProfile


def get_treasury_account():
    a = BankAccount.objects.filter(account_number=settings.BNB_TREASURY_ACCOUNT_NUMBER).first()
    if a is None:
        raise ImproperlyConfigured("Settlement account missing. Run: python manage.py seed_demo")
    return a


def ensure_treasury():
    """Idempotently creates the bank settlement account (counter-party for loans, FDs, EMIs, opening deposits)."""
    existing = BankAccount.objects.filter(account_number=settings.BNB_TREASURY_ACCOUNT_NUMBER).first()
    if existing:
        return existing
    User = get_user_model()
    user = User(username="bnbtreasury", email="treasury@bnb.invalid", mobile="6000000000", is_active=False)
    user.set_unusable_password()
    user.save()
    cust = CustomerProfile.objects.create(user=user, full_name="Bharat Nidhi Bank Settlement",
                                          date_of_birth=datetime.date(2000, 1, 1), gender="OTHER")
    branch, _ = Branch.objects.get_or_create(branch_code="HQ001", defaults=dict(
        branch_name="BNB Head Office", ifsc_code="BNBK0000000", address="1 Nariman Point", city="Mumbai",
        district="Mumbai", state="Maharashtra", pincode="400021", phone="02200000000"))
    atype, _ = AccountType.objects.get_or_create(code="SETTLE", defaults=dict(type_name="Settlement", is_active=False))
    return BankAccount.objects.create(
        account_number=settings.BNB_TREASURY_ACCOUNT_NUMBER, customer=cust, account_type=atype, branch=branch,
        balance=Decimal("5000000000000.00"), available_balance=Decimal("5000000000000.00"))
