from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin

from .models import DepositAccount, DepositScheme


@admin.register(DepositScheme)
class DepositSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "scheme_type", "interest_rate", "is_active")
    list_filter = ("scheme_type", "is_active")


@admin.register(DepositAccount)
class DepositAccountAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "customer", "scheme", "maturity_date", "maturity_amount", "status")
    list_filter = ("status", "scheme")
