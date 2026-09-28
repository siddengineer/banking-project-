from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Address,
    CustomerProfile,
    EmployeeProfile,
    KYCProfile,
    OTPVerification,
    SecuritySettings,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Bank security", {"fields": ("mobile", "failed_login_attempts", "is_locked", "locked_at")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + ((None, {"fields": ("email", "mobile")}),)
    list_display = ("username", "email", "mobile", "is_active", "is_locked", "is_staff")
    list_filter = ("is_active", "is_locked", "is_staff")
    search_fields = ("username", "email", "mobile")


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("customer_number", "full_name", "user", "gender", "created_at")
    search_fields = ("customer_number", "full_name", "user__username", "user__mobile")
    list_filter = ("gender",)
    readonly_fields = ("customer_number", "created_at", "updated_at")


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "user", "designation", "department", "branch", "status")
    search_fields = ("employee_code", "user__username")
    list_filter = ("status", "department")


@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "masked_pan", "masked_aadhaar", "kyc_status", "verified_by", "verified_at")
    list_filter = ("kyc_status",)
    search_fields = ("user__username",)
    readonly_fields = ("masked_pan", "masked_aadhaar", "created_at", "updated_at")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "address_type", "city", "pincode", "is_default")
    list_filter = ("address_type", "is_default")
    search_fields = ("user__username", "city", "pincode")


@admin.register(SecuritySettings)
class SecuritySettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "two_factor_enabled", "login_alerts", "last_password_change")
    readonly_fields = ("updated_at",)


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """Read-only: OTP records must never be edited or created by hand."""

    list_display = ("user", "purpose", "created_at", "expires_at", "attempt_count", "is_verified", "used_at")
    list_filter = ("purpose", "is_verified")
    search_fields = ("user__username",)
    exclude = ("hashed_otp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
