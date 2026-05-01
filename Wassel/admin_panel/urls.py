from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("requests/", views.requests_list, name="requests"),
    path("requests/<int:pk>/approve/", views.approve_request, name="approve_request"),
    path("requests/<int:pk>/reject/", views.reject_request, name="reject_request"),

    path("drivers/<int:pk>/approve/", views.approve_driver, name="approve_driver"),
    path("drivers/<int:pk>/reject/", views.reject_driver, name="reject_driver"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("drivers/<int:pk>/", views.driver_detail, name="driver_detail"),
    path("users/", views.users_list, name="users"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/ban/", views.ban_user, name="ban_user"),
    path("users/<int:pk>/activate/", views.activate_user, name="activate_user"),
    path("payments/", views.payments_view, name="payments"),
    path("notifications/send/", views.send_notification_view, name="send_notification"),
    path("notifications/", views.notifications_list, name="notifications"),
]