from django.urls import path
from . import views


app_name = "reviews"

urlpatterns = [

    path("create/<int:request_id>/", views.create_review, name="create_review"),

]

