from django.contrib import admin

from .models import Announcement, Notification
from .services import broadcast_announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "is_active", "created_by")
    list_filter = ("is_active",)
    search_fields = ("title",)
    actions = ["broadcast"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Broadcast as notification to all active customers")
    def broadcast(self, request, queryset):
        n = sum(broadcast_announcement(a) for a in queryset)
        self.message_user(request, f"Sent {n} notifications.")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("user__username", "title")
