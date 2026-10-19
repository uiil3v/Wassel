from urllib.parse import unquote, urlsplit

from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def safe_return_url(request):
    """Accept a same-origin referrer only inside this application's mount."""
    candidate = request.META.get("HTTP_REFERER", "")
    if url_has_allowed_host_and_scheme(
        candidate, {request.get_host()}, require_https=request.is_secure()
    ):
        path = unquote(urlsplit(candidate).path)
        prefix = request.META.get("SCRIPT_NAME", "") + "/"
        if path.startswith(prefix) and "\\" not in path and not any(
            segment in (".", "..") for segment in path.split("/")
        ):
            return candidate
    return reverse("main:index")
