from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from driver.models import DriverProfile
from student.models import StudentProfile
from django.db.models import Q


# ==========================================
# Subscription
# ==========================================

class Subscription(models.Model):

    DURATION_CHOICES = (
        ("monthly", "شهري"),
        ("semester", "فصلي"),
    )

    STATUS_CHOICES = (
        ("active", "نشط"),
        ("inactive_by_driver", "موقوف بواسطة السائق"),
        ("inactive_by_admin", "موقوف بواسطة الإدارة"),
        ("full", "ممتلئ"),
    )

    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    neighborhood = models.CharField(max_length=200)

    price = models.DecimalField(max_digits=8, decimal_places=2)

    seats = models.PositiveIntegerField()
    available_seats = models.PositiveIntegerField()

    duration = models.CharField(
        max_length=20,
        choices=DURATION_CHOICES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    start_date = models.DateField()
    end_date = models.DateField()

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # -------------------------
    # Validation
    # -------------------------
    def clean(self):
        if self.available_seats > self.seats:
            raise ValidationError("Available seats cannot exceed total seats.")

        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date.")

        if (
            self.duration == "semester"
            and
            self.start_date
            and
            self.end_date
            and
            (self.end_date - self.start_date).days < 90
        ):
            raise ValidationError("Semester subscriptions must be at least 90 days.")

    # -------------------------
    # Auto set available seats
    # -------------------------
    def save(self, *args, **kwargs):
        if not self.pk:
            self.available_seats = self.seats
        super().save(*args, **kwargs)

    # -------------------------
    # Seat Management
    # -------------------------
    def decrease_seat(self):
        if self.available_seats <= 0:
            raise ValidationError("No available seats left.")

        self.available_seats -= 1

        if self.available_seats == 0:
            self.status = "full"

        self.save()

    def increase_seat(self):
        if self.available_seats < self.seats:
            self.available_seats += 1

        if self.status == "full":
            self.status = "active"

        self.save()

    def deactivate_by_admin(self):
        self.status = "inactive_by_admin"
        self.save()


    def deactivate_by_driver(self):
        self.status = "inactive_by_driver"
        self.save()


    def activate(self):

        if self.available_seats <= 0:
            self.status = "full"
        else:
            self.status = "active"

        self.save()

    def __str__(self):
        return f"{self.neighborhood} - {self.driver.user.email}"
    
    @property
    def current_status(self):

        today = timezone.localdate()

        # منتهي
        if self.end_date < today:
            return "expired"

        # موقوف إداريًا
        if self.status == "inactive_by_admin":
            return "inactive_by_admin"

        # موقوف بواسطة السائق
        if self.status == "inactive_by_driver":
            return "inactive_by_driver"

        # ممتلئ
        if self.available_seats <= 0:
            return "full"

        # نشط
        return "active"
    
    # -------------------------
    # Check Remaining Percentage
    # -------------------------
    def can_accept_requests(self):

        today = timezone.localdate()

        # إذا منتهي
        if self.end_date <= today:
            return False

        total_days = (self.end_date - self.start_date).days

        if total_days <= 0:
            return False

        remaining_days = (self.end_date - today).days

        remaining_ratio = remaining_days / total_days

        # 🔥 أقل من 30%
        return remaining_ratio > 0.30
    
    
    @property
    def can_edit(self):

        has_students = self.requests.filter(
            status="approved"
        ).exists()

        has_pending = self.requests.filter(
            status="pending"
        ).exists()

        return not has_students and not has_pending


# ==========================================
# SubscriptionRequest
# ==========================================

class SubscriptionRequest(models.Model):

    STATUS_CHOICES = (
        ("pending", "قيد الانتظار"),
        ("approved", "مقبول"),
        ("rejected", "مرفوض"),
        ("cancelled", "ملغي"),
    )

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="subscription_requests"
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="requests"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    
    request_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    request_date = models.DateTimeField(auto_now_add=True)
    decision_date = models.DateTimeField(blank=True, null=True)
    joined_at = models.DateTimeField(null=True, blank=True)

    price_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )

    note = models.TextField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subscription"],
                condition=Q(status__in=["pending", "approved"]),
                name="unique_active_subscription_request"
            )
        ]

    # -------------------------
    # Approve
    # -------------------------
    @transaction.atomic
    def approve(self):

        if self.status != "pending":
            raise ValidationError("Only pending requests can be approved.")

        if self.subscription.current_status != "active":
            raise ValidationError("Subscription is not active.")

        if self.subscription.available_seats <= 0:
            raise ValidationError("No seats available.")

        # Prevent multiple active subscriptions for student
        today = timezone.localdate()
        active_subscription_exists = SubscriptionRequest.objects.filter(
            student=self.student,
            status="approved",
            subscription__end_date__gte=today
        ).exclude(pk=self.pk).exists()

        if active_subscription_exists:
            raise ValidationError("Student already has an active subscription.")

        self.subscription.decrease_seat()

        self.status = "approved"
        self.decision_date = timezone.now()
        self.joined_at = timezone.now()  # 👈 هذا اللي نبيه
        self.price_snapshot = self.subscription.price
        self.save()

    # -------------------------
    # Reject
    # -------------------------
    @transaction.atomic
    def reject(self):

        if self.status != "pending":
            raise ValidationError("Only pending requests can be rejected.")

        self.status = "rejected"
        self.decision_date = timezone.now()
        self.save()

    # -------------------------
    # Cancel
    # -------------------------
    @transaction.atomic
    def cancel(self):

        if self.status != "approved":
            raise ValidationError("Only approved requests can be cancelled.")

        self.subscription.increase_seat()

        self.status = "cancelled"
        self.decision_date = timezone.now()
        self.save()
        
        if hasattr(self, "contract"):
            self.contract.cancel()
        
    def generate_request_code(self):
        year = timezone.now().year
        return f"WSL-{year}-{self.id:06d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.request_code:
            self.request_code = self.generate_request_code()
            super().save(update_fields=["request_code"])

    def get_status(self):
        return self.status

    def __str__(self):
        return f"{self.student.user.email} → {self.subscription.neighborhood}"


# ==========================================
# SubscriptionRequestSchedule
# ==========================================

class SubscriptionRequestSchedule(models.Model):

    DAYS_OF_WEEK = (
        ("sunday", "الأحد"),
        ("monday", "الإثنين"),
        ("tuesday", "الثلاثاء"),
        ("wednesday", "الأربعاء"),
        ("thursday", "الخميس"),
        ("friday", "الجمعة"),
        ("saturday", "السبت"),
    )

    request = models.ForeignKey(
        SubscriptionRequest,
        on_delete=models.CASCADE,
        related_name="schedule"
    )

    day_of_week = models.CharField(
        max_length=20,
        choices=DAYS_OF_WEEK
    )

    pickup_time = models.TimeField(blank=True, null=True)
    return_time = models.TimeField(blank=True, null=True)

    is_off_day = models.BooleanField(default=False)

    def set_day_off(self):
        self.is_off_day = True
        self.pickup_time = None
        self.return_time = None
        self.save()

    def update_times(self, pickup=None, return_time=None):
        if not self.is_off_day:
            self.pickup_time = pickup
            self.return_time = return_time
            self.save()

    def __str__(self):
        return f"{self.request.student.user.email} - {self.day_of_week}"
