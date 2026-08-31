from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from location.models import City
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)


        if not extra_fields.get("city"):
            raise ValueError("City is required")

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    
    # بيسكمبنتشسمكيبت


    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", "active")
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("admin_level", 1)  

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        city, _ = City.objects.get_or_create(
            name_en="Default City",
            defaults={
                "name_ar": "مدينة افتراضية",
                "slug": "default-city"
            }
        )
        extra_fields["city"] = city

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):

    username = None  

    ROLE_CHOICES = (
        ('student', 'طالب'),
        ('driver', 'سائق'),
        ('admin', 'مشرف'),  
    )

    STATUS_CHOICES = (
        ('active', 'نشط'),
        ('banned', 'محظور'),
        ('deleted', 'محذوف'),
    )
    
    ADMIN_LEVELS = (
        (1, "Super Admin"),
        (2, "Manager"),
    )

    admin_level = models.IntegerField(
        choices=ADMIN_LEVELS,
        null=True,
        blank=True
    )
    
    def clean(self):
        if self.role != "admin" and self.admin_level is not None:
            raise ValidationError("Only admin users can have admin_level.")

        if self.role == "admin" and self.admin_level is None:
            raise ValidationError("Admin users must have admin_level.")
        
    def save(self, *args, **kwargs):
        self.clean()  # 🔥 يجبر التحقق
        super().save(*args, **kwargs)

    email = models.EmailField(unique=True)
    
    pending_email = models.EmailField(
        unique=True,
        null=True,
        blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student'
    )

    phone = models.CharField(max_length=20, unique=True)

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
    
    email_verified = models.BooleanField(
        default=False
    )
    
    last_verification_email_sent = models.DateTimeField(
        null=True,
        blank=True
    )
    
    last_email_change_confirmation_sent = models.DateTimeField(
        null=True,
        blank=True
    )
    
    last_password_reset_email_sent = models.DateTimeField(
        null=True,
        blank=True
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    USERNAME_FIELD = "email"


    REQUIRED_FIELDS = ["first_name", "last_name", "phone"]

    objects = CustomUserManager()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.email