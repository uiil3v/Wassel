from django.urls import path
from . import views

app_name = "student"

urlpatterns = [
    path("dashboard/", views.student_dashboard, name="dashboard"),
    path("my-subscription/<int:req_id>/", views.student_subscription_detail, name="subscription_detail"),
    path("subscriptions/", views.available_subscriptions, name="subscriptions"),
    path("subscription/<int:sub_id>/", views.subscription_detail_view, name="subscription_detail_view"),
    path("create-request/<int:sub_id>/", views.create_request, name="create_request"),
    path("cancel-request/<int:req_id>/", views.cancel_request, name="cancel_request"),
]