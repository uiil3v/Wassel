from django.db import models
from django.conf import settings


# ==========================
# Wallet
# ==========================

class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet"
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    frozen_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} Wallet"


# ==========================
# Transaction
# ==========================

class Transaction(models.Model):

    TYPE_CHOICES = (
        ("deposit", "Deposit"),
        ("freeze", "Freeze"),
        ("release", "Release"),
        ("commission", "Commission"),
        ("refund", "Refund"),
        ("withdraw", "Withdraw"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    subscription_request = models.ForeignKey(
        "subscriptions.SubscriptionRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="completed"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.email} - {self.type} - {self.amount}"


# ==========================
# PlatformEarning
# ==========================

class PlatformEarning(models.Model):
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Platform Earning - {self.amount}"