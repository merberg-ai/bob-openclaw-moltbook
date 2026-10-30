"""Deterministic v0.8 zip package, read-only views and launcher smoke tests."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import build_v08_shadow_package as package
from bob_v08.inspect import read_status, now_content, inbox_content, render_now


class PackageSmokeTests(unittest.TestCase):
    def test_reproducible_package_contains_only_reviewed_sources(self):
        first, wrapper = package.build()
        second, again = package.build()
        self.assertEqual(first, second)
        self.assertEqual(wrapper, again)
        self.assertLess(len(first), 512 * 1024)
        with ZipFile(BytesIO(first)) as archive:
            self.assertEqual(set(archive.namelist()),
                             {"bob_v08/" + name for name in package.MODULES})
            for member in archive.infolist():
                self.assertEqual(member.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertFalse(member.filename.startswith("/"))
                self.assertNotIn("..", Path(member.filename).parts)
                self.assertIn(b"import", archive.read(member.filename)
                              if member.filename != "bob_v08/__init__.py" else b"import")

    def test_isolated_zip_import_and_read_only_cli(self):
        data, wrapper = package.build()
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            home = folder / "home"
            home.mkdir(mode=0o700)
            bin_dir = folder / "bin"
            bin_dir.mkdir()
            (bin_dir / package.BUNDLE).write_bytes(data)
            (bin_dir / package.ENTRYPOINT).write_bytes(wrapper)
            env = dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE="1")
            env.pop("PYTHONPATH", None)
            for args, expected in ((["--status"], "not_started"),
                                   (["--digest"], "bob-v08-experience-v1"),
                                   (["--once"], "no_verified_saved_sources")):
                with self.subTest(args=args):
                    p = subprocess.run([sys.executable, "-I",
                                        str(bin_dir / package.ENTRYPOINT), *args],
                                       capture_output=True, text=True, env=env,
                                       timeout=10, check=False)
                    self.assertEqual(p.returncode, 0, p.stderr[:1000])
                    self.assertIn(expected, p.stdout)
            self.assertFalse((home / ".config/moltbook").exists())
            self.assertFalse((home / ".local/state/bob-v08-shadow").exists())

    def test_builder_never_has_live_install_path(self):
        source = (ROOT / "scripts/build_v08_shadow_package.py").read_text()
        for disallowed in ("subprocess.run", "systemctl", "urllib",
                           "api_key", "os.system", "pip install"):
            self.assertNotIn(disallowed, source)


class ReadOnlyViewTests(unittest.TestCase):
    def test_missing_event_db_does_not_create_or_fake_a_next_tick(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "nothing.sqlite3"
            status = read_status(path)
            self.assertEqual(status["state"], "not_started")
            self.assertEqual(status["events"], [])
            self.assertFalse(status["scheduled"])
            self.assertFalse(path.exists())
            page = now_content(status)
            self.assertIn("Every v0.8 external action is blocked", page)
            self.assertIn("No verified shadow activity", page)

    def test_event_fields_are_escaped_before_html_output(self):
        injected = "<script>alert(1)</script>"
        status = {"state": "shadow_read_only", "count": 1,
                  "events": [{"at": "UTC", "source_run": injected,
                              "kind": "decision", "action_type": "comment",
                              "reason": injected}]}
        page = now_content(status)
        self.assertNotIn(injected, page)
        self.assertIn("&lt;script&gt;", page)
        inbox = inbox_content({"events": [{"kind": "agent_error",
                                         "source_run": injected, "reason": injected}]},
                              {"observations": []})
        self.assertNotIn(injected, inbox)
        self.assertIn("&lt;script&gt;", inbox)
        self.assertIn("max-width:380px", page)

    def test_wrapper_used_for_authenticated_route_integration(self):
        with tempfile.TemporaryDirectory() as root:
            called = []
            def auth_wrap(title, content, path):
                called.append((title, path))
                return content
            body = render_now(auth_wrap, path=Path(root) / "missing.sqlite3")
            self.assertEqual(called, [("Bob · Shadow Now", "/v08/now")])
            self.assertIn("Shadow Now", body)


if __name__ == "__main__":
    unittest.main()
