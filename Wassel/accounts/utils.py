from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse

from .tokens import email_verification_token

from Wassel.email_utils import send_platform_email


def send_email_change_confirmation(user, request):

    uid = urlsafe_base64_encode(
        force_bytes(user.pk)
    )

    token = email_verification_token.make_token(
        user
    )

    confirmation_url = request.build_absolute_uri(
        reverse(
            "accounts:confirm_email_change",
            kwargs={
                "uidb64": uid,
                "token": token
            }
        )
    )

    send_platform_email(
        subject="تأكيد تغيير البريد الإلكتروني",
        recipient=user.pending_email,
        template_name="emails/email_change_confirmation.html",
        context={
            "user": user,
            "confirmation_url": confirmation_url,
        }
    )