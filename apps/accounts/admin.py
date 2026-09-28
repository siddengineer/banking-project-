from django.contrib import admin

from .models import AccountType, Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("branch_name", "branch_code", "ifsc_code", "city", "state", "status")
    list_filter = ("status", "state")
    search_fields = ("branch_name", "branch_code", "ifsc_code", "city")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ("type_name", "code", "min_balance", "interest_rate", "is_active")
    list_filter = ("is_active",)
    search_fields = ("type_name", "code")

from apps.audit.services import Actions, log_event

from .models import BankAccount, Nominee


class NomineeInline(admin.StackedInline):
    model = Nominee
    extra = 0


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("account_number", "customer", "account_type", "branch", "balance", "status")
    list_filter = ("status", "account_type", "branch")
    search_fields = ("account_number", "customer__full_name", "customer__customer_number")
    # Balances change only through the ledger service, never by hand.
    readonly_fields = ("balance", "available_balance", "opened_at", "created_at", "updated_at")
    inlines = [NomineeInline]
    actions = ["freeze", "unfreeze"]

    def get_readonly_fields(self, request, obj=None):
        ro = list(self.readonly_fields)
        return ro + ["account_number", "customer"] if obj else ro

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        log_event(Actions.ADMIN_ACTION, user=request.user, entity_type="BankAccount", entity_id=obj.pk,
                  metadata={"change": "saved", "status": obj.status}, request=request)

    @admin.action(description="Freeze selected accounts")
    def freeze(self, request, qs):
        for a in qs.filter(status="ACTIVE"):
            a.status = "FROZEN"; a.save(update_fields=["status", "updated_at"])
            log_event(Actions.ADMIN_ACTION, user=request.user, entity_type="BankAccount", entity_id=a.pk, metadata={"change": "FROZEN"}, request=request)

    @admin.action(description="Unfreeze selected accounts")
    def unfreeze(self, request, qs):
        for a in qs.filter(status="FROZEN"):
            a.status = "ACTIVE"; a.save(update_fields=["status", "updated_at"])
            log_event(Actions.ADMIN_ACTION, user=request.user, entity_type="BankAccount", entity_id=a.pk, metadata={"change": "ACTIVE"}, request=request)
