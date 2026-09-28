from django.contrib import admin

from .models import ServiceRequest


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "customer", "category", "priority", "status", "assigned_to", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("ticket_number", "subject", "customer__full_name")
    readonly_fields = ("ticket_number", "customer", "created_at", "updated_at")
