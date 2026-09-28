from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class LoanType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, default="")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    min_amount = models.DecimalField(max_digits=18, decimal_places=2)
    max_amount = models.DecimalField(max_digits=18, decimal_places=2)
    tenure_min = models.PositiveSmallIntegerField()
    tenure_max = models.PositiveSmallIntegerField()
    documents_required = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(interest_rate__gte=0), name="loantype_rate_gte_0"),
            models.CheckConstraint(condition=Q(min_amount__gte=0) & Q(max_amount__gte=F("min_amount")), name="loantype_amount_range"),
            models.CheckConstraint(condition=Q(tenure_min__gt=0) & Q(tenure_max__gte=F("tenure_min")), name="loantype_tenure_range"),
        ]

    def __str__(self):
        return self.name


class LoanApplication(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey("users.CustomerProfile", on_delete=models.PROTECT, related_name="loan_applications")
    loan_type = models.ForeignKey(LoanType, on_delete=models.PROTECT, related_name="applications")
    amount_requested = models.DecimalField(max_digits=18, decimal_places=2, db_index=True)
    tenure_months = models.PositiveSmallIntegerField()
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    applied_at = models.DateTimeField(null=True, blank=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey("users.EmployeeProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_loans")
    rejection_reason = models.TextField(blank=True, default="")
    sanctioned_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    sanctioned_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    admin_remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-applied_at", "-id"]
        constraints = [models.CheckConstraint(condition=Q(amount_requested__gt=0) & Q(tenure_months__gt=0), name="loanapp_positive")]

    def __str__(self):
        return f"LA-{self.pk} {self.loan_type}"


class LoanAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"
        DEFAULTED = "DEFAULTED", "Defaulted"

    application = models.OneToOneField(LoanApplication, on_delete=models.PROTECT, related_name="loan_account")
    account_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey("users.CustomerProfile", on_delete=models.PROTECT, related_name="loan_accounts")
    disbursed_amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.PositiveSmallIntegerField()
    emi_amount = models.DecimalField(max_digits=18, decimal_places=2)
    disbursed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(disbursed_amount__gt=0) & Q(emi_amount__gt=0), name="loanacct_positive")]


class LoanInstallment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    loan_account = models.ForeignKey(LoanAccount, on_delete=models.PROTECT, related_name="installments")
    installment_no = models.PositiveSmallIntegerField(db_index=True)
    due_date = models.DateField(db_index=True)
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    transaction = models.ForeignKey("transactions.Transfer", null=True, blank=True, on_delete=models.SET_NULL, related_name="installments")

    class Meta:
        ordering = ["loan_account", "installment_no"]
        constraints = [models.UniqueConstraint(fields=["loan_account", "installment_no"], name="uniq_installment_no")]
