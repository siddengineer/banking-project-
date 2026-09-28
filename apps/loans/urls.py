from django.urls import path

from . import views

app_name = "loans"
urlpatterns = [
    path("", views.loan_list, name="list"),
    path("apply/", views.loan_apply, name="apply"),
    path("staff/", views.staff_queue, name="staff_queue"),
    path("staff/<int:pk>/", views.staff_review, name="staff_review"),
    path("staff/<int:pk>/disburse/", views.staff_disburse, name="staff_disburse"),
    path("<int:pk>/", views.loan_detail, name="detail"),
]
