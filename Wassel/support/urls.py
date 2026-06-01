from django.urls import path
from . import views

app_name = "support"

urlpatterns = [

    path(
        "contact/",
        views.contact_view,
        name="contact"
    ),

    path(
        "track/",
        views.track_ticket,
        name="track_ticket"
    ),

    path(
        "track/verify/",
        views.verify_ticket_code,
        name="verify_ticket_code"
    ),

    path(
        "ticket/<str:ticket_number>/",
        views.ticket_detail_view,
        name="ticket_detail"
    ),

]
