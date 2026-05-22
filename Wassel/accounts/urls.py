from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("verify-email/<uidb64>/<token>/", views.verify_email_view, name="verify_email"),
    path("verify-email-notice/", views.verify_email_notice_view, name="verify_email_notice"),
    path("resend-verification/", views.resend_verification_email_view, name="resend_verification"),
    path("login/", views.login_view, name="login"),
    path("restore-account/", views.restore_account_view, name="restore_account"),
    path("logout/", views.logout_view, name="logout"), 
    path("profile/<int:user_id>/", views.public_profile_view, name="public_profile"), 
    # =========================
    # Password Reset
    # =========================

    path(
        "forgot-password/",
        views.CustomPasswordResetView.as_view(),
        name="forgot_password"
    ),

    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/forgot_password_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/accounts/reset-complete/"
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),
]