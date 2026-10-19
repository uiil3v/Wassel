"""Authenticated WSGI mount. The proxy must preserve /wassel in the origin URL."""

from hmac import compare_digest
from http.cookies import SimpleCookie
from ipaddress import ip_address


class ProxyMount:
    prefix = "/wassel"
    public_host = "projects.saifwork.online"

    def __init__(self, application, secret=""):
        self.application = application
        self.secret = secret

    def __call__(self, environ, start_response):
        environ = environ.copy()
        supplied = environ.pop("HTTP_X_WASSEL_PROXY_KEY", None)
        client_ip = environ.pop("HTTP_X_WASSEL_CLIENT_IP", "")
        # Never let visitor-controlled forwarding headers reach Django.
        for key in list(environ):
            if key.startswith("HTTP_X_FORWARDED_") or key in (
                "HTTP_FORWARDED", "HTTP_X_REAL_IP", "SCRIPT_URL", "SCRIPT_URI",
            ):
                environ.pop(key, None)
        environ["SCRIPT_NAME"] = ""
        mounted = supplied is not None
        if mounted:
            if len(self.secret) < 32 or not compare_digest(
                supplied.encode("utf-8"), self.secret.encode("utf-8")
            ):
                return self.reject(start_response)
            path = environ.get("PATH_INFO", "")
            if path == self.prefix:
                query = environ.get("QUERY_STRING", "")
                target = self.prefix + "/" + ("?" + query if query else "")
                start_response("308 Permanent Redirect", [
                    ("Location", target), ("Content-Length", "0"),
                    ("Cache-Control", "no-store"),
                ])
                return [b""]
            if not path.startswith(self.prefix + "/"):
                return self.reject(start_response)
            environ["SCRIPT_NAME"] = self.prefix
            environ["PATH_INFO"] = path[len(self.prefix):]
            environ["HTTP_HOST"] = self.public_host
            environ["SERVER_NAME"] = self.public_host
            environ["SERVER_PORT"] = "443"
            environ["wsgi.url_scheme"] = "https"
            if client_ip:
                try:
                    environ["REMOTE_ADDR"] = str(ip_address(client_ip))
                except ValueError:
                    return self.reject(start_response)
        elif environ.get("HTTP_HOST", "").split(":")[0].lower() == self.public_host:
            # This host is only served through an authenticated mounted request.
            return self.reject(start_response)

        def respond(status, headers, exc_info=None):
            result = []
            for name, value in headers:
                if mounted and name.lower() == "set-cookie":
                    cookie = SimpleCookie()
                    cookie.load(value)
                    for morsel in cookie.values():
                        morsel["path"] = self.prefix + "/"
                        morsel["secure"] = True
                        # Host-only cookies; never share them with other hosts.
                        morsel["domain"] = ""
                        result.append((name, morsel.OutputString()))
                else:
                    result.append((name, value))
            if not environ.get("PATH_INFO", "").startswith("/static/"):
                result = [(n, v) for n, v in result if n.lower() != "cache-control"]
                result.append(("Cache-Control", "private, no-store"))
            return start_response(status, result, exc_info)

        return self.application(environ, respond)

    @staticmethod
    def reject(start_response):
        body = b"Invalid proxy request."
        start_response("403 Forbidden", [
            ("Content-Type", "text/plain"), ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ])
        return [body]
