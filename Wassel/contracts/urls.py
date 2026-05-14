from django.urls import path
from . import views

app_name = "contracts"

urlpatterns = [

    path(
        "",
        views.my_contracts,
        name="my_contracts"
    ),

    path(
        "pdf/<int:contract_id>/",
        views.download_contract_pdf,
        name="download_contract_pdf"
    ),

]