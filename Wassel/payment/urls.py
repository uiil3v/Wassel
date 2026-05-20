from django.urls import path
from .views import wallet_view, export_wallet_csv

app_name = "payment"

urlpatterns = [
    path("wallet/", wallet_view, name="wallet"),
    path("wallet/export/csv/", export_wallet_csv, name="export_wallet_csv"),
]