from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("interest-rates/", views.interest_rates, name="interest_rates"),
    path("faq/", views.faq, name="faq"),
    path("personal/", views.personal_banking, name="personal"),
    path("business/", views.business_banking, name="business"),
    path("nri/", views.nri_banking, name="nri"),
    path("rural/", views.rural_banking, name="rural"),
    path("loans-info/", views.loans_info, name="loans_info"),
    path("deposits-info/", views.deposits_info, name="deposits_info"),
    path("cards-info/", views.cards_info, name="cards_info"),
    path("digital-info/", views.digital_info, name="digital_info"),
    path("security-info/", views.security_info, name="security_info"),
    path("announcements/", views.announcements_view, name="announcements"),
    path("offers/", views.offers_view, name="offers"),
    path("contact/", views.contact_view, name="contact"),
    path("about/", views.about_view, name="about"),
    path("careers/", views.careers_view, name="careers"),
]
