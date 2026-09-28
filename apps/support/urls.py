from django.urls import path

from . import views

app_name = "support"
urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("new/", views.ticket_new, name="new"),
    path("staff/", views.staff_ticket_list, name="staff_list"),
    path("staff/<str:ticket>/", views.staff_ticket_update, name="staff_update"),
    path("<str:ticket>/", views.ticket_detail, name="detail"),
]
