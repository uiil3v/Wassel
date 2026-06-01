from django.db import DatabaseError
from django.utils import timezone

from .models import SiteVisit


class SiteVisitTrackingMiddleware:
    SKIPPED_PREFIXES = (
        "/admin/",
        "/admin-panel/",
        "/static/",
        "/media/",
        "/favicon.ico",
        "/robots.txt",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if self._should_track(request, response):
            self._track_visit(request)

        return response

    def _should_track(self, request, response):
        if request.method != "GET":
            return False

        if response.status_code >= 400:
            return False

        path = request.path or ""

        if any(path.startswith(prefix) for prefix in self.SKIPPED_PREFIXES):
            return False

        if path.startswith("/__debug__/"):
            return False

        if request.user.is_authenticated and request.user.role == "admin":
            return False

        return True

    def _track_visit(self, request):
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
        today = timezone.localdate()

        try:
            visit, created = SiteVisit.objects.get_or_create(
                ip_address=ip_address,
                user_agent=user_agent,
                visit_date=today,
                defaults={
                    "path": request.path[:255],
                },
            )

            if not created:
                visit.path = request.path[:255]
                visit.hits += 1
                visit.save(update_fields=["path", "hits", "last_seen_at"])

        except DatabaseError:
            return

    def _get_client_ip(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "0.0.0.0")
