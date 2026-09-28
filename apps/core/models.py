from django.db import models
from django.db.models import F, Q
from django.utils import timezone

# NOTE: Offer / InterestRate / FAQ fields are inferred (freeze text was truncated before these entities).


class Offer(models.Model):
    class SchemeType(models.TextChoices):
        LOAN = "LOAN", "Loan"
        DEPOSIT = "DEPOSIT", "Deposit"
        CARD = "CARD", "Card"

    title = models.CharField(max_length=200)
    description = models.TextField()
    scheme_type = models.CharField(max_length=10, choices=SchemeType.choices, db_index=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField()
    image_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(valid_to__gte=F("valid_from")), name="offer_dates_valid")]

    def __str__(self):
        return self.title


class InterestRate(models.Model):
    class Category(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        LENDING = "LENDING", "Lending"

    category = models.CharField(max_length=10, choices=Category.choices, db_index=True)
    product_name = models.CharField(max_length=100)
    tenure_label = models.CharField(max_length=50, blank=True, default="")
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["category", "product_name"]
        constraints = [models.CheckConstraint(condition=Q(rate__gte=0), name="interestrate_rate_gte_0")]

    def __str__(self):
        return f"{self.product_name} {self.tenure_label} {self.rate}%"


class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=50, blank=True, default="", db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "FAQ"

    def __str__(self):
        return self.question
