from django.db import models
from django.utils import timezone

# NOTE: fields after assigned_to inferred (freeze text truncated).


class ServiceRequest(models.Model):
    class Category(models.TextChoices):
        ACCOUNT_QUERY = "ACCOUNT_QUERY", "Account query"
        DEBIT_CARD = "DEBIT_CARD", "Debit card issue"
        CHEQUE_BOOK = "CHEQUE_BOOK", "Cheque book"
        ADDRESS_CHANGE = "ADDRESS_CHANGE", "Address change"
        COMPLAINT = "COMPLAINT", "Complaint - unauthorized transaction"
        LOAN_QUERY = "LOAN_QUERY", "Loan query"
        GENERAL = "GENERAL", "General query"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        WAITING_FOR_CUSTOMER = "WAITING_FOR_CUSTOMER", "Waiting for customer"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    ticket_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey("users.CustomerProfile", on_delete=models.PROTECT, related_name="service_requests")
    category = models.CharField(max_length=30, choices=Category.choices, db_index=True)
    subject = models.CharField(max_length=120)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    assigned_to = models.ForeignKey("users.EmployeeProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_requests")
    admin_response = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.ticket_number
