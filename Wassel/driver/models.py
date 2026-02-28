from django.db import models
from django.conf import settings


class DriverProfile(models.Model):

    VERIFICATION_STATUS = (
        ("incomplete", "Incomplete"),
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile"
    )

    # ===== Driver Documents =====
    id_document_image = models.ImageField(
        upload_to="driver_docs/%Y/%m/",
        blank=True,
        null=True
    )

    driving_license_image = models.ImageField(
        upload_to="driver_docs/%Y/%m/",
        blank=True,
        null=True
    )

    # ===== Vehicle Documents =====
    vehicle_registration_image = models.ImageField(
        upload_to="driver_vehicle/%Y/%m/",
        blank=True,
        null=True
    )

    vehicle_insurance_image = models.ImageField(
        upload_to="driver_vehicle/%Y/%m/",
        blank=True,
        null=True
    )

    vehicle_front_image = models.ImageField(
        upload_to="driver_vehicle/%Y/%m/",
        blank=True,
        null=True
    )

    vehicle_back_image = models.ImageField(
        upload_to="driver_vehicle/%Y/%m/",
        blank=True,
        null=True
    )

    vehicle_side_image = models.ImageField(
        upload_to="driver_vehicle/%Y/%m/",
        blank=True,
        null=True
    )

    vehicle_model = models.CharField(
        max_length=100,
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

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} ({self.verification_status})"