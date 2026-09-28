from django.db import models
from django.db.models import Q
from django.utils import timezone


class Card(models.Model):
    """Fictional demo card. No PAN, CVV, PIN or track data is ever stored."""

    class Type(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        BLOCKED = "BLOCKED", "Blocked"
        TEMPORARILY_DISABLED = "TEMPORARILY_DISABLED", "Temporarily disabled"
        EXPIRED = "EXPIRED", "Expired"

    user = models.ForeignKey("users.CustomerProfile", on_delete=models.PROTECT, related_name="cards")
    account = models.ForeignKey("accounts.BankAccount", on_delete=models.PROTECT, related_name="cards")
    card_reference = models.CharField(max_length=30, unique=True)
    last_four = models.CharField(max_length=4, db_index=True)
    card_type = models.CharField(max_length=10, choices=Type.choices, db_index=True)
    name_on_card = models.CharField(max_length=150)
    expiry_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    issue_date = models.DateField()
    limit_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(limit_amount__gte=0), name="card_limit_gte_0")]

    @property
    def masked_number(self):
        return f"XXXX XXXX XXXX {self.last_four}"

    def __str__(self):
        return self.masked_number


class CardSettings(models.Model):
    card = models.OneToOneField(Card, on_delete=models.CASCADE, related_name="settings")
    atm_enabled = models.BooleanField(default=True)
    online_enabled = models.BooleanField(default=True)
    international_enabled = models.BooleanField(default=False)
    contactless_enabled = models.BooleanField(default=True)
    daily_atm_limit = models.DecimalField(max_digits=18, decimal_places=2, default=50000)
    daily_pos_limit = models.DecimalField(max_digits=18, decimal_places=2, default=100000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "card settings"
        constraints = [
            models.CheckConstraint(condition=Q(daily_atm_limit__gte=0) & Q(daily_pos_limit__gte=0), name="cardsettings_limits_gte_0"),
        ]
