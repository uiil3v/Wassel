"""Render supplies X-Forwarded-Proto; do not accept alternative scheme headers.

Gunicorn loads this file from Render's configured Root Directory (Wassel/).
Keep its peer trust policy: Render supplies FORWARDED_ALLOW_IPS for its Python
runtime. Do not copy that platform policy to an externally exposed Gunicorn.
"""

secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
# Neither SCRIPT_NAME nor PATH_INFO may be supplied by request headers.
# ProxyMount alone controls mounting after verifying the shared secret.
forwarder_headers = []
