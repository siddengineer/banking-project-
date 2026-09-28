from django.contrib import admin

from .models import FAQ, InterestRate, Offer


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "scheme_type", "valid_from", "valid_to", "is_active")
    list_filter = ("scheme_type", "is_active")
    search_fields = ("title",)


@admin.register(InterestRate)
class InterestRateAdmin(admin.ModelAdmin):
    list_display = ("category", "product_name", "tenure_label", "rate", "is_active")
    list_filter = ("category", "is_active")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "display_order", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("question",)
