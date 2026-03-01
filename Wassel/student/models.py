from django.db import models
from django.conf import settings


class StudentProfile(models.Model):

    GENDER_CHOICES = (
        ("male", "ذكر"),
        ("female", "أنثى"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    neighborhood = models.CharField(
        max_length=150
    )

    location_url = models.URLField(
        blank=True,
        null=True
    )

    university_name = models.CharField(
        max_length=150
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.university_name}"