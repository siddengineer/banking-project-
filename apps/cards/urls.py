from django.urls import path

from . import views

app_name = "cards"
urlpatterns = [
    path("", views.card_list, name="list"),
    path("<str:ref>/", views.card_detail, name="detail"),
    path("<str:ref>/action/", views.card_action, name="action"),
    path("<str:ref>/limits/", views.card_limits, name="limits"),
]
