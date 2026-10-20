"""
WSGI config for Wassel project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.conf import settings
from .proxy_mount import ProxyMount

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Wassel.settings")

django_application = get_wsgi_application()
application = ProxyMount(django_application, settings.WASSEL_PROXY_SECRET)
