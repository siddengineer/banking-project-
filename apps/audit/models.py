from django.conf import settings
from django.db import models
from django.utils import timezone

# NOTE: fields inferred from SRS 7.4 (freeze text truncated before AuditLog).


class AuditLog(models.Model):
    """Append-only. Updates and single-object deletes are refused at model level."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=50, db_index=True)
    entity_type = models.CharField(max_length=50, blank=True, default="", db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise PermissionError("Audit logs are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit logs are append-only.")

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"
