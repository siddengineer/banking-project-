from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("apps.users.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("beneficiaries/", include("apps.beneficiaries.urls")),
    path("cards/", include("apps.cards.urls")),
    path("loans/", include("apps.loans.urls")),
    path("deposits/", include("apps.deposits.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("support/", include("apps.support.urls")),
    path("", include("apps.transactions.urls")),
    path("", include("apps.core.urls")),
] + (static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) if settings.DEBUG else [])

handler404 = "django.views.defaults.page_not_found"
