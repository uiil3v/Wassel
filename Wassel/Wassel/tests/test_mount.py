from http.cookies import SimpleCookie
from io import BytesIO
from urllib.parse import urlencode

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse, set_script_prefix

from Wassel.http_utils import safe_return_url
from Wassel.proxy_mount import ProxyMount


def setUpModule():
    from django.core.management import call_command
    from django.core.files.storage import storages
    from django.contrib.staticfiles.storage import staticfiles_storage
    from django.utils.functional import empty
    set_script_prefix("/")
    call_command("collectstatic", interactive=False, verbosity=0)
    # collectstatic uses its own storage; reload the app's manifest after collection.
    storages._storages.clear()
    staticfiles_storage._wrapped = empty


class Browser:
    """Exercise the actual WSGI boundary, not Django Client's bypass of wsgi.py."""

    def __init__(self, mounted=False):
        self.mounted = mounted
        self.prefix = "/wassel" if mounted else ""
        self.host = "projects.saifwork.online" if mounted else "wassel.onrender.com"
        self.cookies = SimpleCookie()
        self.app = ProxyMount(get_wsgi_application(), settings.WASSEL_PROXY_SECRET)

    def request(self, path, method="GET", data=None, headers=None):
        body = urlencode(data or {}).encode()
        environ = RequestFactory()._base_environ(
            PATH_INFO=self.prefix + path, REQUEST_METHOD=method,
            HTTP_HOST="wassel.onrender.com", SERVER_NAME="wassel.onrender.com",
            SERVER_PORT="443", **{"wsgi.url_scheme": "https"},
        )
        environ.update({
            "wsgi.input": BytesIO(body), "CONTENT_LENGTH": str(len(body)),
            "CONTENT_TYPE": "application/x-www-form-urlencoded",
            "HTTP_COOKIE": "; ".join(f"{k}={v.value}" for k, v in self.cookies.items()),
        })
        if self.mounted:
            environ["HTTP_X_WASSEL_PROXY_KEY"] = settings.WASSEL_PROXY_SECRET
        environ.update(headers or {})
        result = {}

        def start(status, response_headers, exc_info=None):
            result["status"] = int(status.split()[0])
            result["headers"] = dict(response_headers)
            result["cookies"] = SimpleCookie()
            for key, value in response_headers:
                if key.lower() == "set-cookie":
                    result["cookies"].load(value)
                    self.cookies.load(value)

        response = self.app(environ, start)
        try:
            result["body"] = b"".join(response)
        finally:
            if hasattr(response, "close"):
                response.close()
        return result

    def post(self, path, data=None, **headers):
        fields = dict(data or {})
        fields["csrfmiddlewaretoken"] = self.cookies[settings.CSRF_COOKIE_NAME].value
        return self.request(path, "POST", fields, {
            "HTTP_ORIGIN": "https://" + self.host, **headers,
        })


class ProxySecurityTests(SimpleTestCase):
    def tearDown(self):
        set_script_prefix("/")

    def test_untrusted_forwarding_cannot_mount(self):
        seen = {}
        def app(environ, start):
            seen.update(environ)
            start("200 OK", [])
            return [b"ok"]
        env = {
            "PATH_INFO": "/accounts/login/", "HTTP_HOST": "wassel.onrender.com",
            "HTTP_X_FORWARDED_HOST": "evil.invalid", "HTTP_X_FORWARDED_PREFIX": "/wassel",
            "HTTP_X_FORWARDED_PROTO": "https", "SCRIPT_URL": "/wassel/accounts/login/",
        }
        list(ProxyMount(app)(env, lambda *args: None))
        self.assertEqual(seen["SCRIPT_NAME"], "")
        self.assertEqual(seen["HTTP_HOST"], "wassel.onrender.com")
        self.assertNotIn("HTTP_X_FORWARDED_HOST", seen)
        self.assertNotIn("SCRIPT_URL", seen)

    def test_invalid_disabled_and_missing_authentication(self):
        for secret, headers in [
            (settings.WASSEL_PROXY_SECRET, {"HTTP_X_WASSEL_PROXY_KEY": "wrong"}),
            ("", {"HTTP_X_WASSEL_PROXY_KEY": settings.WASSEL_PROXY_SECRET}),
            (settings.WASSEL_PROXY_SECRET, {"HTTP_HOST": "projects.saifwork.online"}),
        ]:
            with self.subTest(headers=list(headers), enabled=bool(secret)):
                status = []
                app = ProxyMount(lambda *args: self.fail("Must reject before Django"), secret)
                list(app({"PATH_INFO": "/wassel/", **headers}, lambda s, h: status.append(s)))
                self.assertEqual(status, ["403 Forbidden"])

    def test_authenticated_prefix_boundary_and_canonical_redirect(self):
        browser = Browser(True)
        for path in ("/wallet/", "/wassel-evil/", "/"):
            response = browser.request("/", headers={"PATH_INFO": path})
            self.assertEqual(response["status"], 403)
        response = browser.request("/", "POST", {"x": "1"}, {
            "PATH_INFO": "/wassel", "QUERY_STRING": "a=1",
        })
        self.assertEqual(response["status"], 308)
        self.assertEqual(response["headers"]["Location"], "/wassel/?a=1")

    def test_referrer_stays_inside_mount(self):
        set_script_prefix("/wassel/")
        request = RequestFactory().get("/", secure=True, HTTP_HOST="projects.saifwork.online")
        request.META["SCRIPT_NAME"] = "/wassel"
        for candidate in ["https://evil.invalid/wassel/", "/other/", "/wassel/../other/", "//evil.invalid/"]:
            request.META["HTTP_REFERER"] = candidate
            self.assertEqual(safe_return_url(request), "/wassel/")
        request.META["HTTP_REFERER"] = "https://projects.saifwork.online/wassel/wallet/"
        self.assertEqual(safe_return_url(request), request.META["HTTP_REFERER"])

    def test_body_query_ip_and_multiple_cookie_headers_survive_mount(self):
        seen, response_headers = {}, []
        body = b"--multipart-boundary\r\nfile-data\x00\xff"
        def app(environ, start):
            seen.update(environ)
            self.assertEqual(environ["wsgi.input"].read(), body)
            start("200 OK", [
                ("Set-Cookie", "wassel_sessionid=value; Path=/; HttpOnly; SameSite=Lax"),
                ("Set-Cookie", "messages=; Path=/; Max-Age=0; SameSite=Lax"),
            ])
            return [b"ok"]
        env = {
            "PATH_INFO": "/wassel/support/", "QUERY_STRING": "q=%2F&x=1",
            "REQUEST_METHOD": "POST", "CONTENT_TYPE": "multipart/form-data; boundary=test",
            "wsgi.input": BytesIO(body), "HTTP_HOST": "wassel.onrender.com",
            "HTTP_X_WASSEL_PROXY_KEY": settings.WASSEL_PROXY_SECRET,
            "HTTP_X_WASSEL_CLIENT_IP": "192.0.2.10", "HTTP_X_FORWARDED_FOR": "evil",
        }
        list(ProxyMount(app, settings.WASSEL_PROXY_SECRET)(
            env, lambda status, headers, exc_info=None: response_headers.extend(headers)
        ))
        self.assertEqual(seen["QUERY_STRING"], env["QUERY_STRING"])
        self.assertEqual(seen["REQUEST_METHOD"], "POST")
        self.assertEqual(seen["CONTENT_TYPE"], env["CONTENT_TYPE"])
        self.assertEqual(seen["REMOTE_ADDR"], "192.0.2.10")
        self.assertEqual(seen["HTTP_HOST"], "projects.saifwork.online")
        self.assertEqual(seen["PATH_INFO"], "/support/")
        self.assertNotIn("HTTP_X_WASSEL_PROXY_KEY", seen)
        self.assertNotIn("HTTP_X_FORWARDED_FOR", seen)
        cookies = [value for name, value in response_headers if name == "Set-Cookie"]
        self.assertEqual(len(cookies), 2)
        self.assertTrue(all("Path=/wassel/" in value and "Secure" in value for value in cookies))
        self.assertIn("Max-Age=0", cookies[1])

    def test_static_and_reverse_prefix_are_thread_local(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.contrib.staticfiles.storage import staticfiles_storage
        barrier = Barrier(2)
        def urls(prefix):
            set_script_prefix(prefix)
            try:
                barrier.wait(timeout=10)
                return reverse("accounts:login"), staticfiles_storage.url("admin/css/base.css")
            finally:
                set_script_prefix("/")
        with ThreadPoolExecutor(max_workers=2) as executor:
            root, mounted = list(executor.map(urls, ["/", "/wassel/"]))
        self.assertEqual(root[0], "/accounts/login/")
        self.assertEqual(mounted[0], "/wassel/accounts/login/")
        self.assertTrue(root[1].startswith("/static/"))
        self.assertEqual(mounted[1], "/wassel" + root[1])


class DualHostTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from accounts.models import User
        from location.models import City
        city = City.objects.create(name_en="Test", name_ar="Test", slug="test")
        cls.user = User.objects.create_user(
            email="student@example.invalid", password="test-password", city=city,
            role="student", status="active", email_verified=True,
        )
        from student.models import StudentProfile
        StudentProfile.objects.create(
            user=cls.user, neighborhood="Test", university_name="Test", gender="male"
        )

    def tearDown(self):
        set_script_prefix("/")

    def test_login_logout_session_and_csrf_on_both_hosts(self):
        for mounted in (False, True):
            with self.subTest(mounted=mounted):
                browser = Browser(mounted)
                page = browser.request("/accounts/login/")
                self.assertEqual(page["status"], 200)
                self.assertEqual(page["cookies"][settings.CSRF_COOKIE_NAME]["path"], browser.prefix + "/")
                credentials = {"email": self.user.email, "password": "test-password"}
                self.assertEqual(browser.request("/accounts/login/", "POST", credentials)["status"], 403)
                self.assertEqual(browser.post("/accounts/login/", credentials, HTTP_ORIGIN="https://evil.invalid")["status"], 403)
                response = browser.post("/accounts/login/", credentials)
                self.assertEqual(response["status"], 302)
                self.assertEqual(response["headers"]["Location"], browser.prefix + "/")
                session = response["cookies"][settings.SESSION_COOKIE_NAME]
                self.assertEqual(session["path"], browser.prefix + "/")
                self.assertTrue(session["secure"])
                self.assertTrue(session["httponly"])
                self.assertFalse(session["domain"])
                self.assertEqual(browser.request("/wallet/")["status"], 200)
                logout = browser.request("/accounts/logout/")
                self.assertEqual(logout["headers"]["Location"], browser.prefix + "/")
                self.assertEqual(logout["cookies"][settings.SESSION_COOKIE_NAME]["max-age"], "0")
                self.assertEqual(logout["cookies"][settings.SESSION_COOKIE_NAME]["path"], browser.prefix + "/")
                self.assertEqual(browser.request("/wallet/")["status"], 302)

    def test_protected_routes_keep_prefix_and_next(self):
        for mounted in (True, False, True, False):
            browser = Browser(mounted)
            for path in ["/student/dashboard/", "/driver/dashboard/", "/wallet/", "/contracts/", "/contracts/pdf/1/"]:
                with self.subTest(mounted=mounted, path=path):
                    response = browser.request(path)
                    self.assertEqual(response["status"], 302)
                    self.assertEqual(response["headers"]["Location"],
                        browser.prefix + "/accounts/login/?next=" + browser.prefix + path)

    def test_unverified_account_does_not_loop(self):
        self.user.email_verified = False
        self.user.save(update_fields=["email_verified"])
        for mounted in (False, True):
            browser = Browser(mounted)
            browser.request("/accounts/login/")
            response = browser.post("/accounts/login/", {"email": self.user.email, "password": "test-password"})
            self.assertEqual(response["headers"]["Location"], browser.prefix + "/accounts/verify-email-notice/")
            self.assertEqual(browser.request("/accounts/verify-email-notice/")["status"], 200)
            self.assertEqual(browser.request("/accounts/logout/")["status"], 302)

    def test_password_reset_email_and_success_urls(self):
        from django.core import mail
        from django.urls import resolve
        for mounted in (False, True):
            self.user.last_password_reset_email_sent = None
            self.user.save(update_fields=["last_password_reset_email_sent"])
            browser = Browser(mounted)
            browser.request("/accounts/forgot-password/")
            response = browser.post("/accounts/forgot-password/", {"email": self.user.email})
            self.assertEqual(response["status"], 302)
            self.assertEqual(response["headers"]["Location"], browser.prefix + "/accounts/forgot-password/done/")
            self.assertIn("https://" + browser.host + browser.prefix + "/accounts/reset/", mail.outbox[-1].body)
            view = resolve("/accounts/reset/uid/token/").func
            self.assertEqual(str(view.view_initkwargs["success_url"]), browser.prefix + "/accounts/reset-complete/")

    def test_hashed_static_and_admin_urls_alternate_without_leaking_prefix(self):
        from django.contrib.staticfiles.storage import staticfiles_storage
        for mounted in (True, False, True, False):
            browser = Browser(mounted)
            page = browser.request("/admin/login/")
            self.assertEqual(page["status"], 200)
            url = staticfiles_storage.url("admin/css/base.css")
            self.assertTrue(url.startswith(browser.prefix + "/static/admin/css/base."))
            self.assertIn(url.encode(), page["body"])
            response = browser.request(url[len(browser.prefix):])
            self.assertEqual(response["status"], 200)
            self.assertIn("text/css", response["headers"]["Content-Type"])
            self.assertNotIn("no-store", response["headers"].get("Cache-Control", ""))
            self.assertEqual(page["headers"]["Cache-Control"], "private, no-store")

    def test_full_password_reset_flow(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        for mounted in (False, True):
            self.user.refresh_from_db()
            browser = Browser(mounted)
            uid = urlsafe_base64_encode(force_bytes(self.user.pk))
            token = default_token_generator.make_token(self.user)
            response = browser.request(f"/accounts/reset/{uid}/{token}/")
            confirm_path = f"/accounts/reset/{uid}/set-password/"
            self.assertEqual(response["headers"]["Location"], browser.prefix + confirm_path)
            self.assertEqual(browser.request(confirm_path)["status"], 200)
            response = browser.post(confirm_path, {
                "new_password1": "Fresh-passphrase-783!", "new_password2": "Fresh-passphrase-783!",
            })
            self.assertEqual(response["headers"]["Location"], browser.prefix + "/accounts/reset-complete/")
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password("Fresh-passphrase-783!"))

    def test_subscription_wallet_seats_contract_pdf_and_cancellation(self):
        from datetime import timedelta
        from decimal import Decimal
        from accounts.models import User
        from contracts.models import TransportContract
        from driver.models import DriverProfile
        from payment.models import Wallet
        from subscriptions.models import Subscription, SubscriptionRequest
        from django.utils import timezone

        driver_user = User.objects.create_user(
            email="driver@example.invalid", password="test-password", city=self.user.city,
            role="driver", status="active", email_verified=True,
            first_name="Test", last_name="Driver", phone="0500000000",
        )
        driver = DriverProfile.objects.create(
            user=driver_user, gender="male", verification_status="approved",
            vehicle_make="toyota", vehicle_model="test", vehicle_year=2025,
            **{field: "isolated-test-image" for field in (
                "id_document_image", "driving_license_image", "vehicle_registration_image",
                "vehicle_insurance_image", "vehicle_front_image", "vehicle_back_image", "vehicle_side_image",
            )},
        )
        for mounted in (False, True):
            with self.subTest(mounted=mounted):
                student_browser, driver_browser = Browser(mounted), Browser(mounted)
                for browser, user in [(student_browser, self.user), (driver_browser, driver_user)]:
                    browser.request("/accounts/login/")
                    self.assertEqual(browser.post("/accounts/login/", {
                        "email": user.email, "password": "test-password",
                    })["status"], 302)
                self.assertEqual(student_browser.request("/student/dashboard/")["status"], 200)
                self.assertEqual(driver_browser.request("/driver/dashboard/")["status"], 200)
                wallet = Wallet.objects.get(user=self.user)
                old_balance = wallet.balance
                self.assertEqual(student_browser.post("/wallet/", {
                    "action": "deposit", "amount": "100.00",
                })["status"], 302)
                wallet.refresh_from_db()
                self.assertEqual(wallet.balance, old_balance + Decimal("100"))
                subscription = Subscription.objects.create(
                    driver=driver, neighborhood="Test", price=Decimal("100"), seats=2,
                    duration="monthly", start_date=timezone.localdate(),
                    end_date=timezone.localdate() + timedelta(days=30),
                )
                response = student_browser.post(f"/student/create-request/{subscription.pk}/")
                self.assertEqual(response["headers"]["Location"], student_browser.prefix + "/student/dashboard/")
                req = SubscriptionRequest.objects.get(subscription=subscription)
                self.assertEqual(req.schedule.count(), 7)
                wallet.refresh_from_db()
                self.assertEqual(wallet.frozen_balance, Decimal("100"))
                self.assertEqual(wallet.balance, old_balance)
                response = driver_browser.post(f"/driver/requests/{req.pk}/approve/")
                self.assertEqual(response["status"], 302)
                self.assertTrue(response["headers"]["Location"].startswith(driver_browser.prefix + "/driver/"))
                req.refresh_from_db()
                subscription.refresh_from_db()
                wallet.refresh_from_db()
                self.assertEqual(req.status, "approved")
                self.assertEqual(subscription.available_seats, 1)
                self.assertEqual(wallet.frozen_balance, Decimal("0"))
                contract = TransportContract.objects.get(subscription_request=req)
                pdf = student_browser.request(f"/contracts/pdf/{contract.pk}/")
                self.assertEqual(pdf["status"], 200)
                self.assertEqual(pdf["headers"]["Content-Type"], "application/pdf")
                self.assertTrue(pdf["body"].startswith(b"%PDF"))
                self.assertEqual(pdf["headers"]["Cache-Control"], "private, no-store")
                csv = student_browser.request("/wallet/export/csv/")
                self.assertEqual(csv["status"], 200)
                self.assertIn("text/csv", csv["headers"]["Content-Type"])
                response = student_browser.post(f"/student/cancel-request/{req.pk}/")
                self.assertEqual(response["status"], 302)
                req.refresh_from_db()
                subscription.refresh_from_db()
                wallet.refresh_from_db()
                self.assertEqual(req.status, "cancelled")
                self.assertEqual(subscription.available_seats, 2)
                self.assertGreater(wallet.balance, old_balance)

    def test_administrator_pages_and_tracking_exclusion(self):
        from accounts.models import User
        from admin_panel.models import SiteVisit
        administrator = User.objects.create_user(
            email="admin@example.invalid", password="test-password", city=self.user.city,
            role="admin", admin_level=1, is_staff=True, is_superuser=True,
            status="active", email_verified=True, phone="0500000001",
        )
        for mounted in (False, True):
            browser = Browser(mounted)
            browser.request("/accounts/login/")
            browser.post("/accounts/login/", {"email": administrator.email, "password": "test-password"})
            before = list(SiteVisit.objects.values_list("pk", "hits"))
            for path in ("/admin/", "/admin-panel/", "/admin-panel/payments/"):
                self.assertEqual(browser.request(path)["status"], 200)
            self.assertEqual(list(SiteVisit.objects.values_list("pk", "hits")), before)
