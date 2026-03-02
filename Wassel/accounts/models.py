from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from location.models import City


class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        # 🔥 تأكد أن المدينة موجودة للمستخدم العادي
        if not extra_fields.get("city"):
            raise ValueError("City is required")

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", "active")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        # 🔥 تعيين أول مدينة تلقائيًا لو ما انرسلت
        if "city" not in extra_fields or not extra_fields["city"]:
            first_city = City.objects.first()
            if not first_city:
                raise ValueError("You must create at least one City before creating a superuser.")
            extra_fields["city"] = first_city

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):

    username = None  # حذفنا username رسميًا

    ROLE_CHOICES = (
        ('student', 'طالب'),
        ('driver', 'سائق'),
    )

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('banned', 'Banned'),
    )

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student'
    )

    phone = models.CharField(max_length=20)

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="المدينة"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    USERNAME_FIELD = "email"

    # 🔥 حذفنا city من هنا عشان ما يطلبها createsuperuser
    REQUIRED_FIELDS = ["first_name", "last_name", "phone"]

    objects = CustomUserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.email