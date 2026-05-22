from django.urls import path
from . import views

app_name = "driver"

urlpatterns = [
    path("dashboard/", views.driver_dashboard, name="dashboard"),
    path("profile/", views.driver_profile, name="profile"),
    path("delete-account/", views.delete_driver_account, name="delete_account"),
    path("subscriptions/create/", views.create_subscription, name="create_subscription"),
    path("subscriptions/", views.driver_subscriptions, name="subscriptions"),
    path("subscriptions/<int:sub_id>/", views.subscription_detail, name="subscription_detail"),
    path("subscriptions/<int:sub_id>/deactivate/", views.deactivate_subscription, name="deactivate_subscription"),
    path("subscriptions/<int:sub_id>/activate/", views.activate_subscription, name="activate_subscription"),
    path("requests/<int:req_id>/", views.subscription_request_detail, name="subscription_request_detail"),
    path("requests/<int:req_id>/approve/", views.approve_request, name="approve_request"),
    path("requests/<int:req_id>/reject/", views.reject_request, name="reject_request"),
    path("requests/", views.driver_requests, name="requests"),
    path("notifications/", views.driver_notifications, name="notifications"),
    path("subscriptions/<int:sub_id>/edit/", views.edit_subscription, name="edit_subscription"),
    path("subscriptions/delete/<int:sub_id>/", views.delete_subscription, name="delete_subscription"),
    path("schedule/", views.driver_schedule, name="schedule"),
]