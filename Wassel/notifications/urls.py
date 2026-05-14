from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [

    path(
        "read/<int:notification_id>/",
        views.mark_notification_read,
        name="mark_read"
    ),

    path(
        "read-all/",
        views.mark_all_notifications_read,
        name="mark_all_read"
    ),

    path(
        "delete/<int:notification_id>/",
        views.delete_notification,
        name="delete"
    ),

    path(
        "delete-all/",
        views.delete_all_notifications,
        name="delete_all"
    ),
]