from django.contrib import admin

from .models import Card, CardSettings


class SettingsInline(admin.StackedInline):
    model = CardSettings
    extra = 0


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("card_reference", "masked_number", "user", "card_type", "status", "expiry_date")
    list_filter = ("card_type", "status")
    search_fields = ("card_reference", "last_four", "user__full_name")
    readonly_fields = ("card_reference", "last_four", "created_at", "updated_at")
    inlines = [SettingsInline]
