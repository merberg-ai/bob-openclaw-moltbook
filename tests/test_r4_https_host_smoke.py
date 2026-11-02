"""R4 generated dashboard on a real ephemeral, CA-verified HTTPS socket.

Synthetic HOME, temporary CA and credentials only. No live OMEN, systemd,
real Bob publisher, Moltbook endpoint or public-facing listener. R4 routes
remain read-only without a migrated DB, and HTTPS/auth/CSRF fail closed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_r4_manager_candidate as builder
import build_r313d_off_package as r3
import build_v08_shadow_package as shadow
import prepare_ch_https2 as certificates

CHILD = r"""
from http.client import HTTPConnection, HTTPSConnection
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec
from pathlib import Path
from urllib.parse import urlencode
import base64
import os
import pwd
import ssl
import sys
import threading

home = Path.home()
pwd.getpwuid = lambda uid: type("SyntheticAccount", (), {
    "pw_dir": str(home), "pw_name": "openclaw"})()
loader = SourceFileLoader("r4_synthetic_tls_manager", sys.argv[1])
spec = spec_from_loader(loader.name, loader)
manager = module_from_spec(spec)
loader.exec_module(manager)

from bob_manager_tls import tls_context
server = ThreadingHTTPServer(("127.0.0.1", 0), manager.Handler)
server.socket = tls_context().wrap_socket(server.socket, server_side=True)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
auth = "Basic " + base64.b64encode(
    b"r4-test-user:r4-synthetic-long-password-1234").decode()
trusted = ssl.create_default_context(
    cafile=str(home / ".config/bob-system/manager-tls/ca.crt"))
trusted.minimum_version = ssl.TLSVersion.TLSv1_2
try:
    def req(method, path, *, authenticated=False, host="127.0.0.1:18790",
            origin=None, fields=None):
        conn = HTTPSConnection("127.0.0.1", server.server_port,
                               context=trusted, timeout=4)
        headers = {"Host": host}
        if authenticated:
            headers["Authorization"] = auth
        if origin is not None:
            headers["Origin"] = origin
        payload = urlencode(fields).encode() if fields else None
        if payload:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(method, path, body=payload, headers=headers)
        result = conn.getresponse()
        output = (result.status, result.read(131073))
        conn.close()
        return output

    for route in ("/r4/now", "/r4/inbox", "/r4/bob",
                  "/r4/controls", "/r4/diagnostics", "/r4/chat"):
        assert req("GET", route)[0] == 401, route
        assert req("GET", route, authenticated=True,
                   host="attacker.example")[0] == 403, route
        code, data = req("GET", route, authenticated=True)
        assert code == 200, (route, code, data[:200])
        assert b"R4 Autonomy" in data, route

    # Verify R4 GETs themselves never create SQLite, before legacy routes.
    assert not (home / ".config/moltbook/activity-queue.sqlite3").exists()

    assert req("GET", "/r3", authenticated=True)[0] == 200
    assert req("GET", "/activity", authenticated=True)[0] == 200
    assert b"future CH1" in req(
        "GET", "/r4/chat", authenticated=True)[1]

    mutation = "/r4/controls/upvote"
    assert req("POST", mutation, origin="https://127.0.0.1:18790",
               fields={"csrf": "invalid", "mode": "propose",
                       "confirmation": "SET R4 UPVOTE PROPOSE"})[0] == 401
    assert req("POST", mutation, authenticated=True,
               origin="https://attacker.example",
               fields={"csrf": manager.TOKEN, "mode": "propose",
                       "confirmation": "SET R4 UPVOTE PROPOSE"})[0] == 403
    assert req("POST", mutation, authenticated=True,
               origin="https://127.0.0.1:18790",
               fields={"csrf": "invalid", "mode": "propose",
                       "confirmation": "SET R4 UPVOTE PROPOSE"})[0] == 403
    # A correct origin/CSRF still fails because no trusted R4 installed
    # package and owner DB were created in this synthetic HOME.
    assert req("POST", mutation, authenticated=True,
               origin="https://127.0.0.1:18790",
               fields={"csrf": manager.TOKEN, "mode": "propose",
                       "confirmation": "SET R4 UPVOTE PROPOSE"})[0] == 409

    try:
        plain = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        try:
            plain.request("GET", "/r4/now")
            plain.getresponse()
            raise AssertionError("plaintext HTTP unexpectedly accepted")
        finally:
            plain.close()
    except (OSError, ssl.SSLError, TimeoutError):
        pass

    wrong = ssl.create_default_context()
    connection = HTTPSConnection("127.0.0.1", server.server_port,
                                 context=wrong, timeout=3)
    try:
        connection.request("GET", "/r4/now")
        connection.getresponse()
        raise AssertionError("unknown CA unexpectedly trusted")
    except ssl.SSLCertVerificationError:
        pass
    finally:
        connection.close()
    print("R4 real ephemeral HTTPS: 6 GET routes, auth, host, CSRF, TLS, no schema: PASS")
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)
"""


class R4RealHttpsRehearsal(unittest.TestCase):
    def test_ephemeral_authenticated_r4_and_legacy_routes(self):
        with tempfile.TemporaryDirectory(prefix="r4-https-rehearsal-") as temp:
            root = Path(temp)
            home = root / "home"
            config = home / ".config/bob-system"
            tls = config / "manager-tls"
            tls.mkdir(parents=True, mode=0o700)
            config.chmod(0o700)
            with patch.object(certificates, "OPENSSL", Path("/usr/bin/openssl")), \
                 patch.object(certificates, "TLS_DIR", tls):
                certificates._generate(tls)
            creds = config / "lan-auth.json"
            creds.write_text(json.dumps({
                "username": "r4-test-user",
                "password": "r4-synthetic-long-password-1234"}))
            creds.chmod(0o600)
            installed = home / ".local/bin"
            installed.mkdir(parents=True, mode=0o700)
            registry_dir = home / ".local/state/bob-updater"
            registry_dir.mkdir(parents=True, mode=0o700)
            z2, _ = shadow.build()
            z3, _ = r3.build()
            hashes = {}
            for name, blob in (
                ("bob_v08_package.pyz", z2),
                ("bob_r3_package.pyz", z3),
            ):
                path = installed / name
                path.write_bytes(blob)
                path.chmod(0o700)
                hashes[name] = hashlib.sha256(blob).hexdigest()
            registry = registry_dir / "installed.json"
            registry.write_text(json.dumps({
                "format": "bob-updater-v1",
                "release": "v0.8.0-r3canary1", "files": hashes}))
            registry.chmod(0o600)
            manager, nav = builder.build()
            bin_dir = root / "bin"
            bin_dir.mkdir()
            main = bin_dir / "bob-activity-manager"
            main.write_bytes(manager)
            (bin_dir / "navigation_shell.py").write_bytes(nav)
            env = {**os.environ, "HOME": str(home),
                   "PYTHONPATH": os.pathsep.join([
                       str(bin_dir), str(ROOT / "src/lib/bob"),
                       str(ROOT / "src")]),
                   "BOB_MANAGER_BIND": "0.0.0.0",
                   "BOB_MANAGER_PORT": "18790",
                   "PYTHONDONTWRITEBYTECODE": "1"}
            outcome = subprocess.run(
                [sys.executable, "-c", CHILD, str(main)],
                cwd=root, env=env, capture_output=True,
                text=True, timeout=30)
            self.assertEqual(outcome.returncode, 0, outcome.stderr[-3500:])
            self.assertIn("R4 real ephemeral HTTPS:", outcome.stdout)


if __name__ == "__main__":
    unittest.main()
