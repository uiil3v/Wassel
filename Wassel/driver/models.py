from django.db import models
from django.conf import settings
from django.utils import timezone
from cloudinary.models import CloudinaryField


class DriverProfile(models.Model):

    VERIFICATION_STATUS = (
        ("incomplete", "غير مكتمل"),
        ("pending", "قيد المراجعة"),
        ("approved", "مقبول"),
        ("rejected", "مرفوض"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile"
    )
    
    GENDER_CHOICES = (
        ("male", "ذكر"),
        ("female", "أنثى"),
    )

    # ===== Driver Documents =====
    id_document_image = CloudinaryField(
        'image',
        folder='wasl/drivers/docs',
        blank=True,
        null=True
    )

    driving_license_image = CloudinaryField(
        'image',
        folder='wasl/drivers/docs',
        blank=True,
        null=True
    )

    # ===== Vehicle Documents =====
    vehicle_registration_image = CloudinaryField(
        'image',
        folder='wasl/drivers/vehicle',
        blank=True,
        null=True
    )

    vehicle_insurance_image = CloudinaryField(
        'image',
        folder='wasl/drivers/vehicle',
        blank=True,
        null=True
    )

    vehicle_front_image = CloudinaryField(
        'image',
        folder='wasl/drivers/vehicle',
        blank=True,
        null=True
    )

    vehicle_back_image = CloudinaryField(
        'image',
        folder='wasl/drivers/vehicle',
        blank=True,
        null=True
    )

    vehicle_side_image = CloudinaryField(
        'image',
        folder='wasl/drivers/vehicle',
        blank=True,
        null=True
    )

    vehicle_model = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default="incomplete"
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True
    )
    
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    reviews_count = models.PositiveIntegerField(
        default=0
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def approve(self):
        if self.verification_status == "pending":
            self.verification_status = "approved"
            self.reviewed_at = timezone.now()
            self.rejection_reason = ""
            self.save()

    def reject(self, reason=None):
        self.verification_status = "rejected"
        self.reviewed_at = timezone.now()
        if reason:
            self.rejection_reason = reason
        self.save()

    def __str__(self):
        return f"{self.user.email} ({self.verification_status})"