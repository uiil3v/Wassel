from django.db import models
from accounts.models import User

class Notification(models.Model):


    NOTIFICATION_TYPE = (
        ("system", "System"),
        ("admin", "Admin"),
    )

    TARGET_TYPE = (
        ("user", "User"),
        ("student", "Students"),
        ("driver", "Drivers"),
        ("all", "All Users"),
        ("admin", "Admins"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPE,
        default="system"
    )

    target = models.CharField(
        max_length=20,
        choices=TARGET_TYPE,
        default="user"
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.notification_type}"

