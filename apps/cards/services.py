from datetime import date

from django.db import transaction

from apps.core.utils import add_months, random_digits

from .models import Card, CardSettings


@transaction.atomic
def issue_demo_card(*, customer, account, card_type="DEBIT", limit_amount=0):
    today = date.today()
    card = Card.objects.create(
        user=customer, account=account, card_reference="CRD" + random_digits(12), last_four=random_digits(4),
        card_type=card_type, name_on_card=customer.full_name.upper()[:150], issue_date=today,
        expiry_date=add_months(today, 60), limit_amount=limit_amount)
    CardSettings.objects.create(card=card)
    return card
