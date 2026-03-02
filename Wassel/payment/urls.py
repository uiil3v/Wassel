from django.urls import path
from .views import wallet_view

app_name = "payment"

urlpatterns = [
    path("wallet/", wallet_view, name="wallet"),
]