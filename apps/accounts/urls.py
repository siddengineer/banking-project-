from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("", views.account_list, name="list"),
    path("<str:account_number>/", views.account_detail, name="detail"),
]
