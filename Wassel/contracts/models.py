from django.db import models
from django.utils import timezone

from subscriptions.models import SubscriptionRequest


class TransportContract(models.Model):

    STATUS_CHOICES = (
        ("active", "نشط"),
        ("completed", "مكتمل"),
        ("cancelled", "ملغي"),
    )

    subscription_request = models.OneToOneField(
        SubscriptionRequest,
        on_delete=models.CASCADE,
        related_name="contract"
    )

    contract_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    pdf_file = models.FileField(
        upload_to="contracts/pdfs/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    cancelled_at = models.DateTimeField(
        blank=True,
        null=True
    )

    cancellation_reason = models.TextField(
        blank=True,
        null=True
    )

    def generate_contract_number(self):

        year = timezone.now().year

        return f"CTR-{year}-{self.id:06d}"

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        if not self.contract_number:

            self.contract_number = self.generate_contract_number()

            super().save(
                update_fields=["contract_number"]
            )

    def mark_completed(self):

        self.status = "completed"

        self.completed_at = timezone.now()

        self.save()

    def cancel(self, reason=None):

        self.status = "cancelled"

        self.cancelled_at = timezone.now()

        if reason:
            self.cancellation_reason = reason

        self.save()
        
    def refresh_status(self):

        subscription = self.subscription_request.subscription

        # الطلب ملغي
        if self.subscription_request.status == "cancelled":

            self.status = "cancelled"

            if not self.cancelled_at:
                self.cancelled_at = timezone.now()

        # الاشتراك منتهي
        elif subscription.current_status == "expired":

            self.status = "completed"

            if not self.completed_at:
                self.completed_at = timezone.now()

        # غير كذا يعتبر نشط
        else:

            self.status = "active"

        self.save()

    def __str__(self):

        return self.contract_number or f"Contract #{self.pk}"