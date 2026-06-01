from django.db import models
from django.utils import timezone


class SiteVisit(models.Model):
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=255)
    visit_date = models.DateField(default=timezone.localdate)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    hits = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = (
            "ip_address",
            "user_agent",
            "visit_date",
        )
        ordering = ["-last_seen_at"]

    def __str__(self):
        return f"{self.ip_address} - {self.visit_date}"
