from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin

from .models import Transaction, Transfer


class LegInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = Transaction
    extra = 0


@admin.register(Transfer)
class TransferAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("reference_number", "transfer_type", "amount", "status", "from_account", "to_account", "created_at")
    list_filter = ("transfer_type", "status")
    search_fields = ("reference_number", "from_account__account_number")
    inlines = [LegInline]


@admin.register(Transaction)
class TransactionAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("created_at", "account", "entry_type", "amount", "balance_after", "status")
    list_filter = ("entry_type", "status")
    search_fields = ("transfer__reference_number", "account__account_number")
