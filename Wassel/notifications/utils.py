from .models import Notification
from accounts.models import User

def send_notification(title, message, target="user", user=None, notification_type="system", sent_by=None):


    # 👤 إرسال لمستخدم معين
    if target == "user" and user:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            target="user",
            notification_type=notification_type,
            sent_by=sent_by
        )

    # 👥 كل الطلاب
    elif target == "student":
        users = User.objects.filter(role="student")
        Notification.objects.bulk_create([
            Notification(
                user=u,
                title=title,
                message=message,
                target="student",
                notification_type=notification_type,
                sent_by=sent_by
            ) for u in users
        ])

    # 🚗 كل السائقين
    elif target == "driver":
        users = User.objects.filter(role="driver")
        Notification.objects.bulk_create([
            Notification(
                user=u,
                title=title,
                message=message,
                target="driver",
                notification_type=notification_type,
                sent_by=sent_by
            ) for u in users
        ])

    # 🛠 كل الأدمن
    elif target == "admin":
        users = User.objects.filter(role="admin")
        Notification.objects.bulk_create([
            Notification(
                user=u,
                title=title,
                message=message,
                target="admin",
                notification_type=notification_type,
                sent_by=sent_by
            ) for u in users
        ])

    # 🌍 الجميع
    elif target == "all":
        users = User.objects.all()
        Notification.objects.bulk_create([
            Notification(
                user=u,
                title=title,
                message=message,
                target="all",
                notification_type=notification_type,
                sent_by=sent_by
            ) for u in users
        ])

