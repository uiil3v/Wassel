from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField


class SupportTicket(models.Model):

    CATEGORY_CHOICES = (
        ("support", "دعم فني"),
        ("complaint", "شكوى"),
        ("suggestion", "اقتراح"),
        ("report_user", "بلاغ عن مستخدم"),
        ("other", "أخرى"),
    )

    STATUS_CHOICES = (
        ("in_progress", "قيد المعالجة"),
        ("waiting_user", "بانتظار رد العميل"),
        ("resolved", "تم الحل"),
        ("closed", "مغلقة"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets"
    )

    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    name = models.CharField(
        max_length=150
    )

    email = models.EmailField()

    phone = models.CharField(
        max_length=20
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    subject = models.CharField(
        max_length=255
    )

    message = models.TextField()

    attachment = CloudinaryField(
        "file",
        folder="wasl/support",
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="in_progress"
    )

    admin_response = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    resolved_at = models.DateTimeField(
        blank=True,
        null=True
    )

    closed_at = models.DateTimeField(
        blank=True,
        null=True
    )
    
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_tickets"
    )

    def generate_ticket_number(self):

        return f"TKT-{self.id:06d}"

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        if not self.ticket_number:

            self.ticket_number = self.generate_ticket_number()

            super().save(
                update_fields=["ticket_number"]
            )

    def __str__(self):

        return self.ticket_number or f"Ticket #{self.pk}"