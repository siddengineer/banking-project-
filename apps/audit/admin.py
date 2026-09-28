from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("created_at", "action", "user", "entity_type", "entity_id", "ip_address")
    list_filter = ("action", "entity_type")
    search_fields = ("user__username", "entity_id", "action")

