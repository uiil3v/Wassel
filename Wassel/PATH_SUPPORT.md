# WASSEL: dual root and /wassel/ support (phase 1)

This branch changes Django only. No proxy, deployment, database migration, or
external-service configuration is included.

## Request contract for the later proxy phase

Use the existing WSGI entry point (`Wassel.wsgi:application`, from the `Wassel`
directory) with Gunicorn's WSGI workers. The ASGI entry point does not implement
this mount. Do not set global `FORCE_SCRIPT_NAME` or duplicate the URLconf.

* Direct Render requests use their original root paths.
* The future proxy must fetch the fixed HTTPS Render origin and preserve the
  complete `/wassel/...` path, query string, HTTP method and request body.
* The origin transport Host stays `wassel.onrender.com`.
* Strip visitor-provided `X-Wassel-Proxy-Key` and `X-Wassel-Client-IP` headers.
  Inject `X-Wassel-Proxy-Key` from a private proxy secret binding. Never expose
  this value in JavaScript, HTML, URLs or logs.
* Later, configure the matching `WASSEL_PROXY_SECRET` environment variable in
  Django. Generate a new cryptographically random secret of at least 32 bytes;
  use its URL-safe representation. No deployment secret is created in this branch.
  An empty or short secret disables mounted requests without disabling Render.
* Optionally inject `X-Wassel-Client-IP` from Cloudflare's verified client IP.
  Django accepts a valid IP only after proxy authentication. Otherwise visits
  use the origin peer address. `X-Forwarded-For` is no longer trusted directly.
* Preserve browser Origin and Referer. Do not fabricate either to bypass CSRF.
* The adapter fixes the public host and scheme and sets SCRIPT_NAME/PATH_INFO
  for this request only. Arbitrary forwarded hosts and prefixes are ignored.
* `/wassel` is canonicalized to `/wassel/` with 308, retaining the query string.
  The future proxy must route both paths, preserving the method/body for 308.
* Use manual upstream redirect handling. Relay Location, each Set-Cookie header,
  content types, binary downloads and status codes without collapsing headers.
  No HTML rewriting or cookie path rewriting is needed in the proxy: Django's
  WSGI adapter already scopes mounted cookies, including deletion cookies.
* Bypass edge caching for application responses and never retry mutating
  requests automatically. Django emits `private, no-store` outside `/static/`.
  Only public static assets may be cached. Do not override this with Cache Everything.

Authentication here is a server-to-server shared secret over HTTPS. A caller
with that secret can impersonate the proxy; protect it and rotate if leaked.
Public headers claiming to come from Cloudflare are not sufficient evidence.

## Django changes

* WSGI authentication and mount handling: `Wassel/proxy_mount.py`, `Wassel/wsgi.py`.
* Explicit hosts, named LOGIN_URL, secure application-specific cookies and
  STORAGES configuration: `Wassel/settings.py`.
* Request-local static URLs via `Wassel/static_storage.py`: root requests use
  `/static/...`; mounted requests use `/wassel/static/...`. Both are served by
  WhiteNoise at internal PATH_INFO `/static/...`, including hashed admin assets.
  Run collectstatic as part of a future build before serving DEBUG=False.
* Named password reset redirects in `accounts/views.py`, `accounts/urls.py`.
* Verified-email and visitor-tracking path checks use internal PATH_INFO where
  appropriate (`accounts/middleware.py`, `admin_panel/middleware.py`).
* Safe same-origin, in-mount return redirects: `Wassel/http_utils.py`,
  `accounts/views.py`, `notifications/views.py`.
* Contract PDF base URI follows the current host and mount (`contracts/views.py`).
* `payment/admin.py` now checks authentication before reading the user's role;
  this fixes a pre-existing anonymous admin-login crash, retaining existing roles.

## Sessions, CSRF and compatibility notes

Session and CSRF cookies are named `wassel_sessionid` and `wassel_csrftoken`.
This intentionally requires users with old cookie names to log in again on a
future deployment; it does not delete database sessions or user records.
Cookies remain host-only; direct requests have Path=/ and mounted requests have
Path=/wassel/. Mounted cookies are always Secure; direct cookies are Secure
unless DEBUG=True. Session cookies remain HttpOnly and SameSite=Lax.

No cross-origin CSRF exception is needed: the adapter provides the verified
browser-facing HTTPS host. Cross-origin requests remain rejected. Sessions are
separate in browsers on the two domains; logging out on one does not log out the
other. Paths do not provide a security boundary against another compromised app
on the same `projects.saifwork.online` origin.

The existing GET logout flow and post-login destination are preserved. Email
links generated during a request use that request's host and prefix. Future
background jobs, if introduced, must choose an explicit public base URL.

Cloudinary fields and uploads, PostgreSQL configuration, models, transaction
boundaries, subscription/payment calculations and migrations are unchanged.
The optional local contract FileField is not converted into persistent storage.

## Isolated verification

From the repository root, with the project's requirements installed:

```powershell
.\venv\Scripts\python.exe -B Wassel/run_isolated_tests.py --verbosity 2
```

The runner discards inherited service credentials and Django/database settings,
does not load `.env`, blocks outbound socket connections, uses SQLite entirely
in memory, captures email locally and writes collected static/media only into
a disposable temporary directory. Test schema creation occurs only in memory.
Do not replace this command with a production-settings manage.py test invocation.

Tests exercise the WSGI boundary on both hosts: proxy rejection, prefix boundary,
canonical redirects, referrer validation, authentication/session cookies and
deletion, CSRF accept/reject, password reset emails and actual reset, admin and
hashed static, unverified accounts, protected routes, wallet deposits, subscription
creation/approval/cancellation, seat counts, contract creation, real PDF generation
and CSV responses. All users, contracts and balances are synthetic.

These tests do not certify PostgreSQL concurrency, live Cloudinary uploads, live
email delivery or the eventual Cloudflare/Gunicorn network integration. A separate
staging environment with a non-production database and service credentials is
still required before enabling the proxy. No live endpoint is exercised here.

### Verification result for this implementation

All 14 tests passed on Django 5.2.4 (the requirements.txt version), with no Django
system-check issues. collectstatic and actual WeasyPrint PDF generation succeeded.
`git diff --check` passed. No model or migration files or payment services changed.

The existing local venv reports Django 6.0.2, so the final verification used
Django 5.2.4 installed separately in the OS temporary directory, without replacing
the venv or changing requirements. To reproduce that exact local selection while
the temporary installation remains available:

```powershell
$env:PYTHONPATH = Join-Path ([System.IO.Path]::GetTempPath()) 'wassel-path-django524'
.\venv\Scripts\python.exe -B Wassel/run_isolated_tests.py --verbosity 2
```

The runner prints the actual Django version before execution. A fresh isolated
environment installed from the project requirements is preferable for staging.
Windows GLib emitted desktop-application registration warnings; PDF generation
and all assertions nevertheless passed. These are not Django test failures.

## Later activation / rollback (not performed)

1. Review this branch; provision independent staging configuration and data.
2. Build static assets and run the WSGI application in staging.
3. Separately implement and review the proxy using the contract above.
4. Configure a fresh shared secret on staging only and verify both host paths,
   TLS detection through Render/Gunicorn, multipart uploads, email, redirects,
   cookie isolation and unrelated Pages routes with an actual browser.
5. After approval, deploy the backwards-compatible Django change before enabling
   the public proxy route. Keep the Render root URL available throughout.

To disable the mount, disable the proxy route and remove the shared-secret
configuration. The direct Render route stays available; no database rollback or
schema migration is associated with these changes.

References:
* https://docs.djangoproject.com/en/5.2/ref/settings/#force-script-name
* https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.HttpRequest.path_info
* https://whitenoise.readthedocs.io/en/stable/django.html#whitenoise-static-prefix
