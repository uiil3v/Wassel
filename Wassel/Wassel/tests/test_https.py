"""Synthetic WSGI requests: no live Render requests or database access."""

import runpy
from pathlib import Path

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.test import RequestFactory, SimpleTestCase

from Wassel.proxy_mount import ProxyMount


class HttpsBoundaryTests(SimpleTestCase):
    def probe(self, scheme, *, mounted=False, origin=None, token=True, **headers):
        observed = {}
        csrf_secret = "a" * 32

        def application(environ, start_response):
            request = WSGIRequest(environ)
            csrf = CsrfViewMiddleware(lambda request: HttpResponse())
            csrf.process_request(request)
            rejected = csrf.process_view(request, lambda request: HttpResponse(), (), {})
            observed.update(
                secure=request.is_secure(),
                url=request.build_absolute_uri(request.path),
                csrf_status=rejected.status_code if rejected else 200,
                environ=environ,
            )
            start_response("200 OK", [])
            return [b""]

        path = "/wassel/accounts/login/" if mounted else "/accounts/login/"
        environ = RequestFactory()._base_environ(
            REQUEST_METHOD="POST", PATH_INFO=path,
            HTTP_HOST="wassel.onrender.com",
            HTTP_COOKIE=f"{settings.CSRF_COOKIE_NAME}={csrf_secret}",
            **{"wsgi.url_scheme": scheme},
        )
        if token:
            environ["HTTP_X_CSRFTOKEN"] = csrf_secret
        if origin is not None:
            environ["HTTP_ORIGIN"] = origin
        if mounted:
            environ["HTTP_X_WASSEL_PROXY_KEY"] = settings.WASSEL_PROXY_SECRET
        environ.update(headers)
        status = []
        list(ProxyMount(application, settings.WASSEL_PROXY_SECRET)(
            environ, lambda value, headers, exc_info=None: status.append(value)
        ))
        observed["status"] = status[0]
        return observed

    def test_render_https_survives_forwarded_header_removal(self):
        for value in ("https", "http", "https, http"):
            with self.subTest(header=value):
                result = self.probe("https", origin="https://wassel.onrender.com",
                                    HTTP_X_FORWARDED_PROTO=value)
                self.assertTrue(result["secure"])
                self.assertEqual(result["csrf_status"], 200)
                self.assertEqual(result["url"], "https://wassel.onrender.com/accounts/login/")
                self.assertNotIn("HTTP_X_FORWARDED_PROTO", result["environ"])

    def test_http_cannot_be_upgraded_by_visitor_headers(self):
        result = self.probe("http", origin="https://wassel.onrender.com",
                            HTTP_X_FORWARDED_PROTO="https", HTTP_X_FORWARDED_SSL="on",
                            HTTP_X_FORWARDED_PROTOCOL="ssl", HTTP_FORWARDED="proto=https",
                            HTTP_X_FORWARDED_HOST="projects.saifwork.online")
        self.assertFalse(result["secure"])
        self.assertEqual(result["csrf_status"], 403)
        self.assertEqual(result["url"], "http://wassel.onrender.com/accounts/login/")
        local = self.probe("http", origin="http://wassel.onrender.com")
        self.assertEqual(local["csrf_status"], 200)

    def test_https_rejects_bad_origin_missing_token_and_insecure_referer(self):
        for headers in (
            {"origin": "https://evil.invalid"},
            {"origin": "http://wassel.onrender.com"},
            {"origin": "https://wassel.onrender.com", "token": False},
            {"HTTP_REFERER": "http://wassel.onrender.com/accounts/login/"},
            {},
        ):
            with self.subTest(headers=headers):
                self.assertEqual(self.probe("https", **headers)["csrf_status"], 403)
        self.assertEqual(self.probe("https", HTTP_REFERER="https://wassel.onrender.com/")["csrf_status"], 200)

    def test_authenticated_mount_sets_https_but_does_not_bypass_csrf(self):
        result = self.probe("http", mounted=True, origin="https://projects.saifwork.online",
                            HTTP_X_FORWARDED_PROTO="http")
        self.assertTrue(result["secure"])
        self.assertEqual(result["csrf_status"], 200)
        self.assertEqual(result["url"], "https://projects.saifwork.online/wassel/accounts/login/")
        self.assertEqual(self.probe("http", mounted=True, origin="https://evil.invalid")["csrf_status"], 403)
        rejected = self.probe("http", mounted=True, HTTP_X_WASSEL_PROXY_KEY="forged")
        self.assertEqual(rejected, {"status": "403 Forbidden"})

    def test_gunicorn_configuration_limits_forwarded_metadata(self):
        config = runpy.run_path(str(Path(settings.BASE_DIR) / "gunicorn.conf.py"))
        self.assertEqual(config["secure_scheme_headers"], {"X-FORWARDED-PROTO": "https"})
        self.assertEqual(config["forwarder_headers"], [])
        self.assertNotIn("forwarded_allow_ips", config)
        self.assertIsNone(settings.SECURE_PROXY_SSL_HEADER)
        self.assertFalse(settings.USE_X_FORWARDED_HOST)
