"""Actual loopback HTTP smoke of candidate, synthetic HOME, GET-only, no real APIs."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_v071_manager_candidate as builder

CHILD = r"""
import json
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec

loader = SourceFileLoader("bob_v071_http_smoke", sys.argv[1])
spec = spec_from_loader("bob_v071_http_smoke", loader)
mod = module_from_spec(spec)
loader.exec_module(mod)
srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
thread = threading.Thread(target=srv.serve_forever, daemon=True)
thread.start()
try:
    statuses = {}
    for route in ("/", "/activity", "/originals", "/healthz"):
        conn = HTTPConnection("127.0.0.1", srv.server_port, timeout=3)
        conn.putrequest("GET", route, skip_host=True)
        conn.putheader("Host", "127.0.0.1:18790")
        conn.endheaders()
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        statuses[route] = response.status
        assert response.status == 200, (route, response.status)
        if route != "/healthz":
            assert body.count('aria-label="Primary navigation"') == 1
            assert body.count('aria-label="Mobile navigation"') == 1
            assert body.count(' aria-current="page"') == 2
            assert '<main class="bob-content"' in body
            assert "default-src 'none'" in response.getheader("Content-Security-Policy")
            if route == "/originals":
                assert 'action="/originals/request/intro"' in body
                assert 'name="csrf"' in body
        else:
            assert json.loads(body)["publishes"] is False
        conn.close()
    # Wrong-host requests must remain forbidden even in test mode.
    conn = HTTPConnection("127.0.0.1", srv.server_port, timeout=3)
    conn.putrequest("GET", "/", skip_host=True)
    conn.putheader("Host", "untrusted.example")
    conn.endheaders()
    denied = conn.getresponse()
    assert denied.status == 403
    denied.read()
    conn.close()
    assert set(statuses.values()) == {200}
    print("INTEGRATED HTTP SMOKE: PASS (3 pages + health, bad Host rejected)")
finally:
    srv.shutdown()
    srv.server_close()
    thread.join(timeout=3)
"""


class IntegratedHttpSmokeTests(unittest.TestCase):
    def test_three_actual_pages_render_on_ephemeral_loopback_from_synthetic_database(self):
        candidate, navigation = builder.build()
        with tempfile.TemporaryDirectory(prefix="bob-v071-ui-http-") as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "home").mkdir()
            manager = root / "bin/bob-activity-manager"
            manager.write_bytes(candidate)
            (root / "bin/navigation_shell.py").write_bytes(navigation)
            env = {**os.environ, "HOME": str(root / "home"),
                   "PYTHONPATH": os.pathsep.join([
                       str(root / "bin"), str(ROOT / "src/lib/bob")]),
                   "BOB_MANAGER_BIND": "127.0.0.1",
                   "BOB_MANAGER_PORT": "18790",
                   "PYTHONDONTWRITEBYTECODE": "1"}
            proc = subprocess.run(
                [sys.executable, "-c", CHILD, str(manager)],
                cwd=root, env=env, timeout=12,
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-1500:])
            self.assertIn("INTEGRATED HTTP SMOKE: PASS", proc.stdout)
            self.assertTrue((root / "home/.config/moltbook/activity-queue.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
