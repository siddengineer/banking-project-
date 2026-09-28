from django.urls import path

from . import views

app_name = "transactions"
urlpatterns = [
    path("transfers/new/", views.transfer_new, name="transfer_new"),
    path("transfers/<str:reference>/verify/", views.transfer_verify, name="transfer_verify"),
    path("transfers/<str:reference>/resend/", views.transfer_resend, name="transfer_resend"),
    path("transfers/<str:reference>/receipt/", views.transfer_receipt, name="transfer_receipt"),
    path("transactions/", views.transaction_history, name="history"),
    path("statements/", views.statement, name="statement"),
]
