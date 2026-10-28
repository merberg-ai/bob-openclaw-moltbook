"""Offline tests for v0.7.1 integration into the existing three GET routes."""
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "webui"))
import build_v071_manager_candidate as builder
import navigation_shell as nav


def old_html(path: str) -> str:
    legacy = nav.LEGACY_NAVS[0 if path == "/" else 1]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>Bob</title><style>main{padding:20px}</style></head>'
        '<body><main><h1>Legacy page</h1>' + legacy
        + '<form method="post" action="/review/20261028T120000Z/approve">'
        '<input type="hidden" name="csrf" value="synthetic-only-token">'
        '<input type="hidden" name="digest" value="synthetic-digest">'
        '<button>Approve</button></form>'
        '</main></body></html>'
    )


class IntegratedNavigationTests(unittest.TestCase):
    def test_build_preserves_pinned_source_and_applies_exact_three_get_changes(self):
        raw = builder.SOURCE.read_bytes()
        original_hash = hashlib.sha256(raw).hexdigest()
        candidate, module = builder.build()
        self.assertEqual(original_hash, builder.PINNED_BASELINE_SHA256)
        self.assertEqual(builder.SOURCE.read_bytes(), raw)
        self.assertEqual(candidate.count(b"integrate_existing_html"), 4)
        self.assertIn(b"def do_POST(self):", candidate)
        self.assertIn(b"def _valid_origin(self):", candidate)
        self.assertIn(b"def _authenticated(self):", candidate)
        self.assertGreater(len(module), 0)

    def test_security_sensitive_handlers_identical_to_pinned_baseline(self):
        raw = builder.SOURCE.read_text()
        candidate = builder.build()[0].decode()
        base = ast.parse(raw)
        new = ast.parse(candidate)
        def handler_methods(tree):
            handler = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Handler")
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in handler.body if isinstance(n, ast.FunctionDef)}
        old = handler_methods(base)
        curr = handler_methods(new)
        self.assertEqual(set(old), set(curr))
        for name in old:
            if name != "do_GET":
                self.assertEqual(old[name], curr[name], name)
        # State-changing paths were not added or removed.
        self.assertEqual(raw.count("def do_POST(self):"), 1)
        self.assertEqual(candidate.count("def do_POST(self):"), 1)

    def test_shell_preserves_exact_approval_form_and_original_markup(self):
        for path in ("/", "/activity", "/originals"):
            html = old_html(path)
            wrapped = nav.integrate_existing_html(html, path)
            self.assertEqual(wrapped.count('action="/review/20261028T120000Z/approve"'), 1)
            self.assertEqual(wrapped.count('name="csrf" value="synthetic-only-token"'), 1)
            self.assertEqual(wrapped.count('name="digest" value="synthetic-digest"'), 1)
            self.assertEqual(wrapped.count('<h1>Legacy page</h1>'), 1)
            self.assertEqual(wrapped.count('aria-current="page"'), 2)
            self.assertNotIn(nav.LEGACY_NAVS[0], wrapped)
            self.assertNotIn(nav.LEGACY_NAVS[1], wrapped)
            self.assertEqual(wrapped.count('<main class="bob-content"'), 1)
            self.assertIn('@media(max-width:760px)', wrapped)

    def test_shell_rejects_unknown_layout_without_dropping_forms(self):
        malformed = old_html("/")
        with self.assertRaisesRegex(ValueError, "Unexpected original"):
            nav.integrate_existing_html(malformed.replace("<body><main>", "<body>"), "/")
        with self.assertRaises(ValueError):
            nav.integrate_existing_html(old_html("/"), "/shutdown")
        with self.assertRaises(ValueError):
            nav.integrate_existing_html(malformed.replace(nav.LEGACY_NAVS[0], nav.LEGACY_NAVS[0] * 2), "/")
            
    def test_review_zip_contains_exactly_two_development_files_and_manifest(self):
        candidate, navigation = builder.build()
        raw = builder.review_zip(candidate, navigation)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(set(z.namelist()), {
                "bin/bob-activity-manager", "bin/navigation_shell.py", "REVIEW-MANIFEST.json"})
            meta = json.loads(z.read("REVIEW-MANIFEST.json"))
            self.assertIs(meta["deployable"], False)
            self.assertEqual(meta["routes"], ["/", "/activity", "/originals"])
            self.assertEqual(meta["candidate_manager_sha256"], builder.sha256(candidate))
            self.assertEqual(meta["navigation_sha256"], builder.sha256(navigation))
            self.assertEqual(meta["base_manager_sha256"], builder.PINNED_BASELINE_SHA256)

    def test_candidate_get_routes_invoke_shell_without_touching_other_handlers(self):
        candidate, _ = builder.build()
        namespace = {"__name__": "bob_v071_candidate_unit_test"}
        # Imports only pinned, reviewed Python modules into synthetic HOME.
        with tempfile.TemporaryDirectory() as home:
            lib = str(ROOT / "src/lib/bob")
            old_path = list(sys.path)
            try:
                sys.path.insert(0, lib)
                with patch.dict(os.environ, {"HOME": home, "BOB_MANAGER_BIND": "127.0.0.1",
                                             "BOB_MANAGER_PORT": "18790"}):
                    exec(compile(candidate, "bob-activity-manager", "exec"), namespace)
                handler = namespace["Handler"]
                for path, renderer in (
                    ("/", "render"), ("/activity", "activity_page"),
                    ("/originals", "originals_page")
                ):
                    mock_obj = object.__new__(handler)
                    mock_obj.path = path
                    mock_obj.client_address = ("127.0.0.1", 12345)
                    with patch.object(handler, "_valid_host", return_value=True), \
                         patch.object(handler, "_authenticated", return_value=True), \
                         patch.object(handler, "_send") as send, \
                         patch.dict(namespace, {renderer: lambda: old_html(path)}):
                        # exec globals is namespace; patch.dict swaps the renderer.
                        mock_obj.do_GET()
                    send.assert_called_once()
                    args = send.call_args.args
                    self.assertEqual(args[0], 200)
                    self.assertIn('class="bob-layout"', args[1])
                    self.assertIn('name="csrf"', args[1])
                    self.assertEqual(args[2], "text/html; charset=utf-8")
            finally:
                sys.path[:] = old_path


if __name__ == "__main__":
    unittest.main()
