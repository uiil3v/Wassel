from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse


def send_platform_email(
    *,
    subject,
    recipient,
    template_name,
    context
):

    html_content = render_to_string(
        template_name,
        context
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )

    email.attach_alternative(
        html_content,
        "text/html"
    )

    email.send()
    


def send_driver_approved_email(user, request):

    dashboard_url = request.build_absolute_uri(
        reverse("driver:dashboard")
    )

    send_platform_email(
        subject="تم اعتماد حسابك كسائق - وصل",
        recipient=user.email,
        template_name="emails/driver_approved_email.html",
        context={
            "user": user,
            "dashboard_url": dashboard_url,
        }
    )


def send_driver_rejected_email(user, reason):

    send_platform_email(
        subject="تم رفض طلب التوثيق - وصل",
        recipient=user.email,
        template_name="emails/driver_rejected_email.html",
        context={
            "user": user,
            "reason": reason,
        }
    )
    


def send_request_approved_email(req, request):

    subscription = req.subscription

    contracts_url = request.build_absolute_uri(
        reverse("contracts:my_contracts")
    )

    duration_map = {
        "monthly": "شهري",
        "semester": "فصلي",
    }

    send_platform_email(
        subject="تم قبول طلب اشتراكك - وصل",
        recipient=req.student.user.email,
        template_name="emails/request_approved_email.html",
        context={
            "user": req.student.user,
            "driver_name": subscription.driver.user.full_name,
            "neighborhood": subscription.neighborhood,
            "price": subscription.price,
            "duration": duration_map.get(
                subscription.duration,
                subscription.duration
            ),
            "contracts_url": contracts_url,
        }
    )


def send_request_rejected_email(req):

    send_platform_email(
        subject="تم رفض طلب الاشتراك - وصل",
        recipient=req.student.user.email,
        template_name="emails/request_rejected_email.html",
        context={
            "user": req.student.user,
        }
    )
    
    
def send_student_cancelled_subscription_email(user):

    send_platform_email(
        subject="تم إلغاء اشتراكك - وصل",
        recipient=user.email,
        template_name="emails/student_cancelled_subscription_email.html",
        context={
            "user": user,
        }
    )


def send_driver_subscription_cancelled_email(req):

    subscription = req.subscription

    send_platform_email(
        subject="تم إلغاء أحد الاشتراكات - وصل",
        recipient=subscription.driver.user.email,
        template_name="emails/driver_subscription_cancelled_email.html",
        context={
            "driver_name": subscription.driver.user.full_name,
            "student_name": req.student.user.full_name,
            "neighborhood": subscription.neighborhood,
            "price": subscription.price,
        }
    )
    


def send_user_banned_email(user):

    send_platform_email(
        subject="تم تقييد حسابك - وصل",
        recipient=user.email,
        template_name="emails/user_banned_email.html",
        context={
            "user": user,
        }
    )


def send_user_activated_email(user):

    send_platform_email(
        subject="تم إعادة تفعيل حسابك - وصل",
        recipient=user.email,
        template_name="emails/user_activated_email.html",
        context={
            "user": user,
        }
    )
    
    
def send_subscription_deactivated_email(subscription):

    send_platform_email(
        subject="تم إيقاف أحد اشتراكاتك - وصل",
        recipient=subscription.driver.user.email,
        template_name="emails/subscription_deactivated_email.html",
        context={
            "user": subscription.driver.user,
            "neighborhood": subscription.neighborhood,
            "price": subscription.price,
        }
    )


def send_subscription_activated_email(subscription):

    send_platform_email(
        subject="تمت إعادة تفعيل اشتراكك - وصل",
        recipient=subscription.driver.user.email,
        template_name="emails/subscription_activated_email.html",
        context={
            "user": subscription.driver.user,
            "neighborhood": subscription.neighborhood,
            "price": subscription.price,
        }
    )
    


def send_wallet_deposit_email(user, amount):

    send_platform_email(
        subject="تم شحن المحفظة بنجاح - وصل",
        recipient=user.email,
        template_name="emails/wallet_deposit_email.html",
        context={
            "user": user,
            "amount": amount,
            "balance": user.wallet.balance,
        }
    )


def send_wallet_withdraw_email(user, amount):

    send_platform_email(
        subject="تم سحب مبلغ من المحفظة - وصل",
        recipient=user.email,
        template_name="emails/wallet_withdraw_email.html",
        context={
            "user": user,
            "amount": amount,
            "balance": user.wallet.balance,
        }
    )
    
def send_admin_notification_email(
    user,
    title,
    message
):

    send_platform_email(
        subject=title,
        recipient=user.email,
        template_name="emails/admin_notification_email.html",
        context={
            "user": user,
            "title": title,
            "message": message,
        }
    )
    
