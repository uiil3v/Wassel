from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class EmailVerificationMiddleware:

    def __init__(self, get_response):

        self.get_response = get_response

    def __call__(self, request):

        # =========================
        # إذا المستخدم مسجل دخول
        # =========================

        if request.user.is_authenticated:

            # =========================
            # إذا الإيميل غير مفعل
            # =========================

            if not request.user.email_verified:

                allowed_paths = [

                    reverse("accounts:verify_email_notice"),

                    reverse("accounts:logout"),

                    reverse("accounts:resend_verification"),
                ]

                current_path = request.path

                # السماح فقط للصفحات المصرح بها
                if (current_path not in allowed_paths and not request.path_info.startswith("/accounts/verify-email/") and not request.path_info.startswith("/admin/")):

                    messages.warning(
                        request,
                        "يرجى تفعيل بريدك الإلكتروني أولاً."
                    )

                    return redirect(
                        "accounts:verify_email_notice"
                    )

        response = self.get_response(request)

        return response
