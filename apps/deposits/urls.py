from django.urls import path

from . import views

app_name = "deposits"
urlpatterns = [
    path("", views.deposit_list, name="list"),
    path("open/", views.deposit_open, name="open"),
    path("<int:pk>/", views.deposit_detail, name="detail"),
    path("<int:pk>/close/", views.deposit_close, name="close"),
]
