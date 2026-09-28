from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class DepositScheme(models.Model):
    class Type(models.TextChoices):
        FD = "FD", "Fixed deposit"
        RD = "RD", "Recurring deposit"

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    scheme_type = models.CharField(max_length=10, choices=Type.choices, db_index=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    min_amount = models.DecimalField(max_digits=18, decimal_places=2)
    min_tenure_months = models.PositiveSmallIntegerField()
    max_tenure_months = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(interest_rate__gte=0), name="depscheme_rate_gte_0"),
            models.CheckConstraint(condition=Q(min_amount__gt=0), name="depscheme_min_gt_0"),
            models.CheckConstraint(condition=Q(max_tenure_months__gte=F("min_tenure_months")), name="depscheme_tenure_range"),
        ]

    def __str__(self):
        return self.name


class DepositAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        MATURED = "MATURED", "Matured"
        CLOSED_PREMATURELY = "CLOSED_PREMATURELY", "Closed prematurely"

    customer = models.ForeignKey("users.CustomerProfile", on_delete=models.PROTECT, related_name="deposits")
    scheme = models.ForeignKey(DepositScheme, on_delete=models.PROTECT, related_name="deposits")
    linked_account = models.ForeignKey("accounts.BankAccount", on_delete=models.PROTECT, related_name="deposits")
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    monthly_installment = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.PositiveSmallIntegerField()
    start_date = models.DateField(db_index=True)
    maturity_date = models.DateField(db_index=True)
    maturity_amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(maturity_date__gt=F("start_date")), name="deposit_maturity_after_start"),
            models.CheckConstraint(condition=Q(maturity_amount__gte=0), name="deposit_maturity_gte_0"),
        ]
