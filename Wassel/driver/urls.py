from django.urls import path
from . import views

app_name = "driver"

urlpatterns = [
    path("dashboard/", views.driver_dashboard, name="dashboard"),
    path("profile/", views.driver_profile, name="profile"),
    path("verification/", views.driver_verification, name="verification"),
]