from django.db import models
from django.conf import settings
from django.utils import timezone
from cloudinary.models import CloudinaryField
from .vehicle_data import VEHICLE_MAKE_CHOICES, vehicle_make_name


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
        blank=False,
        null=True
    )

    vehicle_make = models.CharField(
        max_length=40,
        choices=VEHICLE_MAKE_CHOICES,
        blank=False,
        null=True
    )

    vehicle_year = models.PositiveIntegerField(
        blank=False,
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

    @property
    def documents_complete(self):
        return all([
            self.id_document_image,
            self.driving_license_image,
            self.vehicle_registration_image,
            self.vehicle_insurance_image,
            self.vehicle_front_image,
            self.vehicle_back_image,
            self.vehicle_side_image,
        ])

    @property
    def vehicle_info_complete(self):
        return all([
            self.vehicle_make,
            self.vehicle_model,
            self.vehicle_year,
        ])

    @property
    def account_info_complete(self):
        return all([
            self.user.first_name,
            self.user.last_name,
            self.user.phone,
            self.user.city_id,
            self.gender,
        ])

    @property
    def is_profile_complete(self):
        return all([
            self.account_info_complete,
            self.vehicle_info_complete,
            self.documents_complete,
        ])

    def enforce_incomplete_status(self):
        if self.verification_status == "approved" and not self.is_profile_complete:
            self.verification_status = "incomplete"
            self.save(update_fields=["verification_status", "updated_at"])
            return True
        return False

    @property
    def vehicle_make_display(self):
        return vehicle_make_name(self.vehicle_make)

    @property
    def vehicle_display_name(self):
        parts = [
            self.vehicle_make_display,
            self.vehicle_model,
            str(self.vehicle_year) if self.vehicle_year else "",
        ]
        return " ".join(part for part in parts if part).strip()
