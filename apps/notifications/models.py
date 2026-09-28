from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Type(models.TextChoices):
        TRANSACTION = "TRANSACTION", "Transaction"
        SECURITY = "SECURITY", "Security"
        LOAN = "LOAN", "Loan"
        ACCOUNT = "ACCOUNT", "Account"
        OFFER = "OFFER", "Offer"
        GENERAL = "GENERAL", "General"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=Type.choices, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Announcement(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    body = models.TextField()
    attachment = models.FileField(upload_to="announcements/", null=True, blank=True)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="announcements")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title
