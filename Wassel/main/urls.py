from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("drivers/", views.browse_drivers, name="drivers"),
    path("subscriptions/", views.browse_subscriptions, name="subscriptions"),
    path("subscriptions/<int:sub_id>/", views.public_subscription_detail, name="subscription_detail"),
    path("about/", views.about, name="about"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
]
