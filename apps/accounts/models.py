from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.validators import account_number_validator, ifsc_validator, pincode_validator


class Branch(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    branch_code = models.CharField(max_length=10, unique=True)
    branch_name = models.CharField(max_length=150, db_index=True)
    ifsc_code = models.CharField(max_length=11, unique=True, validators=[ifsc_validator])
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6, validators=[pincode_validator])
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, default="")
    manager_name = models.CharField(max_length=150, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["branch_name"]
        verbose_name_plural = "branches"

    def __str__(self):
        return f"{self.branch_name} ({self.ifsc_code})"


class AccountType(models.Model):
    type_name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, default="")
    min_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["type_name"]
        constraints = [
            models.CheckConstraint(condition=Q(min_balance__gte=0), name="accounttype_min_balance_gte_0"),
            models.CheckConstraint(
                condition=Q(interest_rate__isnull=True) | Q(interest_rate__gte=0),
                name="accounttype_interest_rate_gte_0",
            ),
        ]

    def __str__(self):
        return self.type_name


class BankAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FROZEN = "FROZEN", "Frozen"
        DORMANT = "DORMANT", "Dormant"
        CLOSED = "CLOSED", "Closed"

    account_number = models.CharField(max_length=11, unique=True, validators=[account_number_validator])
    customer = models.ForeignKey("users.CustomerProfile", on_delete=models.PROTECT, related_name="accounts")
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT, related_name="accounts")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="accounts")
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0, db_index=True)
    available_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    minimum_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    opened_at = models.DateTimeField(default=timezone.now, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opened_at"]
        constraints = [
            models.CheckConstraint(condition=Q(balance__gte=0), name="bankaccount_balance_gte_0"),
            models.CheckConstraint(condition=Q(available_balance__gte=0), name="bankaccount_available_gte_0"),
            models.CheckConstraint(condition=Q(minimum_balance__gte=0), name="bankaccount_minimum_gte_0"),
        ]

    @property
    def masked_number(self):
        return f"XXXXXXX{self.account_number[-4:]}"

    def __str__(self):
        return self.masked_number


class Nominee(models.Model):
    account = models.OneToOneField(BankAccount, on_delete=models.CASCADE, related_name="nominee")
    name = models.CharField(max_length=150)
    relation = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    percentage_share = models.PositiveSmallIntegerField(
        default=100, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(percentage_share__gte=1) & Q(percentage_share__lte=100), name="nominee_share_1_100"),
        ]
