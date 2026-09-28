from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin

from .models import Beneficiary


@admin.register(Beneficiary)
class BeneficiaryAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("beneficiary_name", "owner", "masked_account", "beneficiary_type", "verification_status", "is_active")
    list_filter = ("beneficiary_type", "verification_status", "is_active")
    search_fields = ("beneficiary_name", "owner__full_name")
