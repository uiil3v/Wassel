"""Local-only tests: ignore .env and inherited credentials before importing settings."""

import atexit
import os
import tempfile
from unittest.mock import patch

with patch.dict(os.environ, {
    "DJANGO_SETTINGS_MODULE": "Wassel.test_settings",
    "SECRET_KEY": "isolated-tests-only-not-a-deployment-secret",
}, clear=True):
    from .settings import *  # noqa: F403

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
    "TEST": {"NAME": ":memory:"},
}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_HOST_USER = EMAIL_HOST_PASSWORD = ""
DEFAULT_FROM_EMAIL = "test@example.invalid"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DEBUG_PROPAGATE_EXCEPTIONS = True
WASSEL_PROXY_SECRET = "isolated-proxy-test-key-never-use-in-production"
ALLOWED_HOSTS = ["wassel.onrender.com", "projects.saifwork.online", "testserver"]
_files = tempfile.TemporaryDirectory(prefix="wassel-isolated-tests-")
atexit.register(_files.cleanup)
STATIC_ROOT = Path(_files.name) / "static"
MEDIA_ROOT = Path(_files.name) / "media"
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True
