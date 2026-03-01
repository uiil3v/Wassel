from django.urls import path
from . import views

app_name = "driver"

urlpatterns = [
    path("dashboard/", views.driver_dashboard, name="dashboard"),
    path("profile/", views.driver_profile, name="profile"),
    path("subscriptions/create/", views.create_subscription, name="create_subscription"),
    path("subscriptions/", views.driver_subscriptions, name="subscriptions"),
    path("subscriptions/<int:sub_id>/", views.subscription_detail, name="subscription_detail"),
    path("requests/<int:req_id>/", views.subscription_request_detail, name="subscription_request_detail"),
    path("requests/<int:req_id>/approve/", views.approve_request, name="approve_request"),
path("requests/<int:req_id>/reject/", views.reject_request, name="reject_request"),
    path("requests/", views.driver_requests, name="requests"),
    path("notifications/", views.driver_notifications, name="notifications"),
]