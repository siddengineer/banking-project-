from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone

from apps.core.utils import generate_customer_number
from apps.core.validators import (
    aadhaar_validator,
    mobile_validator,
    pan_validator,
    pincode_validator,
    username_validator,
    validate_min_age,
)


class User(AbstractUser):
    """Custom auth user. Passwords use Django hashing (never plaintext)."""

    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={"unique": "A user with that username already exists."},
    )
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=10, unique=True, validators=[mobile_validator])
    is_active = models.BooleanField(default=True, db_index=True)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    is_locked = models.BooleanField(default=False, db_index=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    REQUIRED_FIELDS = ["email", "mobile"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("username"), name="users_user_username_ci_unique"),
            models.UniqueConstraint(Lower("email"), name="users_user_email_ci_unique"),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_customer(self):
        return hasattr(self, "customerprofile")

    @property
    def is_employee(self):
        return hasattr(self, "employeeprofile")


class CustomerProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    customer_number = models.CharField(max_length=12, unique=True, default=generate_customer_number)
    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField(validators=[validate_min_age])
    gender = models.CharField(max_length=10, choices=Gender.choices)
    occupation = models.CharField(max_length=100, blank=True, default="")
    annual_income = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(annual_income__gte=0), name="customer_income_gte_0"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.customer_number})"


class EmployeeProfile(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SUSPENDED = "SUSPENDED", "Suspended"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_code = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    branch = models.ForeignKey(
        "accounts.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="employees"
    )
    joining_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    def __str__(self):
        return f"{self.employee_code} - {self.user.get_username()}"


class KYCProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pan_number = models.CharField(max_length=10, unique=True, validators=[pan_validator])
    aadhaar_number = models.CharField(max_length=12, unique=True, validators=[aadhaar_validator])
    address_proof_type = models.CharField(max_length=50, blank=True, default="")
    address_proof_number = models.CharField(max_length=50, blank=True, default="")
    kyc_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    verified_by = models.ForeignKey(
        EmployeeProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_kycs"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    documents_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "KYC profile"

    @property
    def masked_aadhaar(self):
        return f"XXXXXXXX{self.aadhaar_number[-4:]}" if self.aadhaar_number else ""

    @property
    def masked_pan(self):
        return f"{self.pan_number[:2]}XXXXX{self.pan_number[-3:]}" if self.pan_number else ""

    def __str__(self):
        return f"KYC {self.user_id} [{self.kyc_status}]"


class Address(models.Model):
    class AddressType(models.TextChoices):
        PERMANENT = "PERMANENT", "Permanent"
        CURRENT = "CURRENT", "Current"
        CORRESPONDENCE = "CORRESPONDENCE", "Correspondence"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address_type = models.CharField(max_length=20, choices=AddressType.choices, db_index=True)
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6, db_index=True, validators=[pincode_validator])
    country = models.CharField(max_length=100, default="India")
    is_default = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.address_type}: {self.city} {self.pincode}"


class SecuritySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    two_factor_enabled = models.BooleanField(default=True)
    registered_mobile = models.CharField(max_length=10, validators=[mobile_validator])
    registered_email = models.EmailField()
    login_alerts = models.BooleanField(default=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "security settings"


class OTPVerification(models.Model):
    """Demo OTP. Only a hash is stored; plaintext is never persisted."""

    class Purpose(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        TRANSFER = "TRANSFER", "Transfer"
        BENEFICIARY_ADD = "BENEFICIARY_ADD", "Add beneficiary"
        PASSWORD_RESET = "PASSWORD_RESET", "Password reset"
        CARD_ACTION = "CARD_ACTION", "Card action"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_verifications")
    purpose = models.CharField(max_length=30, choices=Purpose.choices, db_index=True)
    hashed_otp = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(attempt_count__lte=F("max_attempts")), name="otp_attempts_lte_max"
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("created_at")), name="otp_expires_after_created"
            ),
        ]
        indexes = [models.Index(fields=["user", "purpose", "-created_at"], name="otp_user_purpose_idx")]

    def __str__(self):
        return f"OTP {self.purpose} user={self.user_id}"
