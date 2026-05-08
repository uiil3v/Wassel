from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from subscriptions.models import SubscriptionRequest

from .services import update_user_rating


class Review(models.Model):

    REVIEW_TYPE = (
        ("driver", "تقييم سائق"),
        ("student", "تقييم طالب"),
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_reviews"
    )

    reviewed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_reviews"
    )

    subscription_request = models.ForeignKey(
        SubscriptionRequest,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    review_type = models.CharField(
        max_length=20,
        choices=REVIEW_TYPE
    )

    rating = models.PositiveSmallIntegerField()

    comment = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["reviewer", "subscription_request"],
                name="unique_review_per_subscription"
            )
        ]

    def clean(self):
        
        # تأكد أن العلاقات موجودة أولاً
        if not self.reviewer_id or not self.reviewed_user_id:
            return

        # منع تقييم النفس
        if self.reviewer == self.reviewed_user:
            raise ValidationError("لا يمكنك تقييم نفسك.")

        # التقييم فقط بعد انتهاء الاشتراك
        subscription = self.subscription_request.subscription

        if subscription.end_date > timezone.now().date():
            raise ValidationError("لا يمكنك التقييم قبل انتهاء الاشتراك.")

        # لازم الطلب يكون approved
        if self.subscription_request.status != "approved":
            raise ValidationError("لا يمكن تقييم اشتراك غير مكتمل.")



        # تحقق العلاقات

        student_user = self.subscription_request.student.user
        driver_user = self.subscription_request.subscription.driver.user

        valid = (
            (self.reviewer == student_user and self.reviewed_user == driver_user)
            or
            (self.reviewer == driver_user and self.reviewed_user == student_user)
        )

        if not valid:
            raise ValidationError("علاقة التقييم غير صحيحة.")

        # تحقق نوع التقييم
        if self.reviewed_user.role == "driver":
            self.review_type = "driver"

        elif self.reviewed_user.role == "student":
            self.review_type = "student"

        # التقييم من 1 إلى 5
        if self.rating < 1 or self.rating > 5:
            raise ValidationError("التقييم يجب أن يكون بين 1 و 5.")


    def save(self, *args, **kwargs):


        super().save(*args, **kwargs)

        update_user_rating(self.reviewed_user)
        
    def delete(self, *args, **kwargs):

        reviewed_user = self.reviewed_user

        super().delete(*args, **kwargs)

        update_user_rating(reviewed_user)

    def __str__(self):
        return f"{self.reviewer.email} → {self.reviewed_user.email} ({self.rating})"