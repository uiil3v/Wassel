from django.urls import get_script_prefix
from whitenoise.storage import CompressedManifestStaticFilesStorage


class MountedStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Use request-local SCRIPT_NAME without changing the collected file paths."""

    def url(self, name, force=False):
        url = super().url(name, force=force)
        if url.startswith("/") and not url.startswith("//"):
            return get_script_prefix().rstrip("/") + url
        return url
