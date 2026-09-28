from django.contrib import admin

from apps.core.admin_mixins import ReadOnlyAdminMixin

from .models import LoanAccount, LoanApplication, LoanInstallment, LoanType


@admin.register(LoanType)
class LoanTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "interest_rate", "min_amount", "max_amount", "is_active")


@admin.register(LoanApplication)
class LoanApplicationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):  # decisions go through the audited staff workflow
    list_display = ("id", "customer", "loan_type", "amount_requested", "status", "applied_at")
    list_filter = ("status", "loan_type")
    search_fields = ("customer__full_name",)


@admin.register(LoanAccount)
class LoanAccountAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("account_number", "customer", "disbursed_amount", "emi_amount", "status")
    list_filter = ("status",)


@admin.register(LoanInstallment)
class LoanInstallmentAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("loan_account", "installment_no", "due_date", "total_amount", "status")
    list_filter = ("status",)
