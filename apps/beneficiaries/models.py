from django.db import models
from django.utils import timezone

from apps.core.validators import ifsc_validator


class Beneficiary(models.Model):
    class Type(models.TextChoices):
        INTERNAL = "INTERNAL", "Bharat Nidhi Bank"
        EXTERNAL = "EXTERNAL", "Other bank (simulated)"

    class Verification(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        FAILED = "FAILED", "Failed"

    owner = models.ForeignKey("users.CustomerProfile", on_delete=models.PROTECT, related_name="beneficiaries")
    beneficiary_name = models.CharField(max_length=150, db_index=True)
    bank_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=16, db_index=True)
    ifsc_code = models.CharField(max_length=11, db_index=True, validators=[ifsc_validator])
    nickname = models.CharField(max_length=50, blank=True, default="")
    beneficiary_type = models.CharField(max_length=20, choices=Type.choices, db_index=True)
    verification_status = models.CharField(max_length=20, choices=Verification.choices, default=Verification.PENDING, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["beneficiary_name"]
        verbose_name_plural = "beneficiaries"

    @property
    def masked_account(self):
        return "X" * max(len(self.account_number) - 4, 0) + self.account_number[-4:]

    def __str__(self):
        return f"{self.beneficiary_name} ({self.masked_account})"
