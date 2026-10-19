"""Run path tests with in-memory SQLite and no outgoing network connections."""

import argparse
import os
import socket
import sys
import tempfile
from unittest.mock import patch


def deny_network(*args, **kwargs):
    raise AssertionError("Outgoing network access is forbidden in isolated tests")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbosity", type=int, choices=range(4), default=1)
    parser.add_argument("--failfast", action="store_true")
    options = parser.parse_args()
    # Discard inherited service credentials, Django configuration and DATABASE_URL.
    local_environment = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "PATH", "TEMP", "TMP", "TMPDIR"}
    }
    local_environment["DJANGO_SETTINGS_MODULE"] = "Wassel.test_settings"
    with tempfile.TemporaryDirectory(prefix="wassel-test-cache-") as cache_dir, \
            patch.dict(os.environ, {
                **local_environment, "LOCALAPPDATA": cache_dir, "APPDATA": cache_dir,
                "USERPROFILE": cache_dir, "XDG_CACHE_HOME": cache_dir,
            }, clear=True), \
            patch.object(socket.socket, "connect", deny_network), \
            patch.object(socket.socket, "connect_ex", deny_network), \
            patch.object(socket, "create_connection", deny_network):
        from django.core.management import execute_from_command_line
        import django
        print(f"Isolated tests: Django {django.get_version()}, in-memory SQLite, network blocked", flush=True)
        execute_from_command_line([
            sys.argv[0], "test", "Wassel.tests", "--noinput",
            "--verbosity", str(options.verbosity),
            *(["--failfast"] if options.failfast else []),
        ])
