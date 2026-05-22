from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.conf import settings

from .tokens import email_verification_token


def send_email_change_confirmation(user, request):

    uid = urlsafe_base64_encode(
        force_bytes(user.pk)
    )

    token = email_verification_token.make_token(
        user
    )

    verification_url = request.build_absolute_uri(
        reverse(
            "accounts:confirm_email_change",
            kwargs={
                "uidb64": uid,
                "token": token
            }
        )
    )

    send_mail(
        subject="تأكيد تغيير البريد الإلكتروني",

        message=(
            f"مرحبًا {user.full_name}\n\n"
            f"اضغط الرابط التالي لتأكيد تغيير بريدك الإلكتروني:\n\n"
            f"{verification_url}"
        ),

        from_email=settings.DEFAULT_FROM_EMAIL,

        recipient_list=[user.pending_email],
    )