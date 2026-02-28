from django.urls import path
from . import views

app_name = "driver"

urlpatterns = [
    path("dashboard/", views.driver_dashboard, name="dashboard"),
    path("profile/", views.driver_profile, name="profile"),
    path("subscriptions/", views.driver_subscriptions, name="subscriptions"),
    path("requests/", views.driver_requests, name="requests"),
    path("notifications/", views.driver_notifications, name="notifications"),
]