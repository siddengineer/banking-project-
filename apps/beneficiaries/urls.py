from django.urls import path

from . import views

app_name = "beneficiaries"
urlpatterns = [
    path("", views.beneficiary_list, name="list"),
    path("add/", views.beneficiary_add, name="add"),
    path("<int:pk>/edit/", views.beneficiary_edit, name="edit"),
    path("<int:pk>/disable/", views.beneficiary_disable, name="disable"),
]
