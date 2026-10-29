"""Real loopback HTTP password-rotation acceptance using an entirely synthetic HOME."""
from __future__ import annotations
import base64
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/lib/bob"))
import build_v072_settings_candidate as builder


class BrowserSettingsAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="bob-v072-http-test-")
        cls.root = Path(cls.temp.name)
        cls.root.chmod(0o700)
        auth_dir = cls.root / ".config/bob-system"
        auth_dir.mkdir(parents=True, mode=0o700)
        cls.auth = auth_dir / "lan-auth.json"
        cls.original = "synthetic-initial-password-123"
        cls.updated = "synthetic-updated-password-456"
        cls.auth.write_text(json.dumps({"username": "testbob", "password": cls.original}))
        cls.auth.chmod(0o600)
        bin_dir = cls.root / "bin"
        bin_dir.mkdir(mode=0o700)
        manager, navigation = builder.build()
        (bin_dir / "bob-activity-manager").write_bytes(manager)
        (bin_dir / "navigation_shell.py").write_bytes(navigation)
        cls.patchers = [
            patch("pathlib.Path.home", return_value=cls.root),
            patch.dict(os.environ, {"BOB_MANAGER_BIND": "0.0.0.0",
                                    "BOB_MANAGER_PORT": "18790"})]
        for entry in cls.patchers:
            entry.start()
        sys.path.insert(0, str(bin_dir))
        from importlib.machinery import SourceFileLoader
        from importlib.util import module_from_spec, spec_from_loader
        # Avoid stale v0.7.1 module cached by earlier tests in this process.
        cls.previous_navigation = sys.modules.pop("navigation_shell", None)
        nav_loader = SourceFileLoader("navigation_shell", str(bin_dir / "navigation_shell.py"))
        nav_spec = spec_from_loader(nav_loader.name, nav_loader)
        nav_module = module_from_spec(nav_spec)
        sys.modules["navigation_shell"] = nav_module
        nav_loader.exec_module(nav_module)
        from importlib.util import module_from_spec, spec_from_loader
        loader = SourceFileLoader("synthetic_v072_manager", str(bin_dir / "bob-activity-manager"))
        spec = spec_from_loader(loader.name, loader)
        cls.manager = module_from_spec(spec)
        sys.modules[loader.name] = cls.manager
        loader.exec_module(cls.manager)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cls.manager.Handler)
        cls.port = cls.server.server_port
        cls.manager.ALLOWED_HOSTS.add("127.0.0.1:" + str(cls.port))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=4)
        if cls.previous_navigation is None:
            sys.modules.pop("navigation_shell", None)
        else:
            sys.modules["navigation_shell"] = cls.previous_navigation
        for entry in reversed(cls.patchers):
            entry.stop()
        cls.temp.cleanup()

    def request(self, method, path, password=None, form=None, origin=None):
        headers = {"Host": f"127.0.0.1:{self.port}"}
        if password is not None:
            encoded = base64.b64encode(("testbob:" + password).encode()).decode()
            headers["Authorization"] = "Basic " + encoded
        if origin is not None:
            headers["Origin"] = origin
        payload = urlencode(form).encode() if form else None
        if payload is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        connection = HTTPConnection("127.0.0.1", self.port, timeout=4)
        try:
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_settings_page_and_rotation_and_immediate_invalidation(self):
        status, page = self.request("GET", "/settings", self.original)
        self.assertEqual(status, 200)
        self.assertIn(b'Change dashboard password', page)
        self.assertNotIn(self.original.encode(), page)
        self.assertEqual(self.request("GET", "/settings")[0], 401)
        wrong = {"csrf": self.manager.TOKEN, "current": "bad",
                 "new": self.updated, "confirm": self.updated}
        self.assertEqual(self.request("POST", "/settings/password", self.original,
                                      wrong, "http://127.0.0.1:" + str(self.port))[0], 400)
        self.assertEqual(self.request("GET", "/settings", self.original)[0], 200)
        valid = dict(wrong, current=self.original)
        self.assertEqual(self.request("POST", "/settings/password", self.original,
                                      valid, "http://evil.example")[0], 403)
        self.assertEqual(self.request("GET", "/settings", self.original)[0], 200)
        valid["csrf"] = "invalid"
        self.assertEqual(self.request("POST", "/settings/password", self.original,
                                      valid, "http://127.0.0.1:" + str(self.port))[0], 403)
        valid["csrf"] = self.manager.TOKEN
        status, body = self.request("POST", "/settings/password", self.original,
                                    valid, "http://127.0.0.1:" + str(self.port))
        self.assertEqual(status, 200)
        self.assertNotIn(self.updated.encode(), body)
        self.assertEqual(self.request("GET", "/settings", self.original)[0], 401)
        self.assertEqual(self.request("GET", "/settings", self.updated)[0], 200)
        self.assertEqual(self.auth.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
