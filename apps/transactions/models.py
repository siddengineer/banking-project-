from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Transfer(models.Model):
    """Transfer header. Ledger legs live in Transaction."""

    class Type(models.TextChoices):
        OWN = "OWN", "Own accounts"
        INTERNAL = "INTERNAL", "Internal (BNB)"
        EXTERNAL = "EXTERNAL", "External (simulated)"
        BILL = "BILL", "Bill payment"
        LOAN_EMI = "LOAN_EMI", "Loan EMI"
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAWAL = "WITHDRAWAL", "Withdrawal"

    class Mode(models.TextChoices):
        IMPS = "IMPS", "IMPS"
        NEFT = "NEFT", "NEFT"
        RTGS = "RTGS", "RTGS"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REVERSED = "REVERSED", "Reversed"

    reference_number = models.CharField(max_length=30, unique=True)
    transfer_type = models.CharField(max_length=30, choices=Type.choices, db_index=True)
    mode = models.CharField(max_length=10, choices=Mode.choices, blank=True, default="")
    from_account = models.ForeignKey("accounts.BankAccount", on_delete=models.PROTECT, related_name="outgoing_transfers")
    to_account = models.ForeignKey("accounts.BankAccount", null=True, blank=True, on_delete=models.PROTECT, related_name="incoming_transfers")
    beneficiary = models.ForeignKey("beneficiaries.Beneficiary", null=True, blank=True, on_delete=models.PROTECT, related_name="transfers")
    amount = models.DecimalField(max_digits=18, decimal_places=2, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    remarks = models.CharField(max_length=140, blank=True, default="")
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="initiated_transfers")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True, default="")
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="transfer_amount_gt_0")]

    def __str__(self):
        return self.reference_number


class Transaction(models.Model):
    class Entry(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    transfer = models.ForeignKey(Transfer, on_delete=models.PROTECT, related_name="legs")
    account = models.ForeignKey("accounts.BankAccount", on_delete=models.PROTECT, related_name="ledger")
    entry_type = models.CharField(max_length=6, choices=Entry.choices, db_index=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    balance_after = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=Transfer.Status.choices, default=Transfer.Status.SUCCESS, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="txn_amount_gt_0"),
            models.CheckConstraint(condition=Q(balance_after__gte=0), name="txn_balance_after_gte_0"),
        ]
