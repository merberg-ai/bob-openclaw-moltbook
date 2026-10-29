"""Offline tests for v0.7.1 navigation markup (no server or network)."""
from pathlib import Path
import importlib.util
import sys
import unittest

MODULE = Path(__file__).resolve().parents[1] / "webui" / "navigation_shell.py"
SPEC = importlib.util.spec_from_file_location("bob_navigation_shell_under_test", MODULE)
NAV = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NAV)


class NavigationShellTests(unittest.TestCase):
    def test_only_existing_routes_are_linked(self):
        html = NAV.wrap("Scout", "<p>Example</p>", "/")
        for href in ('href="/"', 'href="/activity"', 'href="/originals"'):
            self.assertEqual(html.count(href), 2)
        self.assertNotIn("href=\"/healthz\"", html)
        self.assertNotIn("method=\"post\"", html)

    def test_exactly_one_current_link_per_navigation(self):
        for path in ("/", "/activity", "/originals"):
            html = NAV.wrap("Test", "<p>Safe</p>", path)
            self.assertEqual(html.count(' aria-current="page"'), 2)
            self.assertEqual(html.count(f'href="{path}" aria-current="page"'), 2)

    def test_unknown_routes_refused(self):
        for path in ("/admin", "/activity/../", '"><script>alert(1)</script>'):
            with self.assertRaises(ValueError):
                NAV.wrap("Test", "", path)

    def test_heading_and_title_are_html_escaped(self):
        html = NAV.wrap("<img src=x onerror=alert(1)>", "<p>Trusted</p>", "/")
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img", html)
        self.assertIn("<p>Trusted</p>", html)

    def test_keyboard_accessible_no_javascript_required(self):
        html = NAV.wrap("Published activity", "<p>Trusted</p>", "/activity")
        self.assertIn('aria-label="Primary navigation"', html)
        self.assertIn('aria-label="Mobile navigation"', html)
        self.assertIn("<details><summary>", html)
        self.assertIn("a:focus-visible", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("onclick=", html)

    def test_accessible_skip_link_and_real_mobile_open_selector(self):
        markup = NAV.wrap("Scout & review", "<p>Content</p>", "/")
        self.assertIn('href="#main-content">Skip to content</a>', markup)
        self.assertIn('id="main-content" tabindex="-1"', markup)
        self.assertIn('.bob-mobile details[open] summary::after', NAV.CSS)
        self.assertNotIn('.bob-mobile[open]', NAV.CSS)
        self.assertIn('min-height:44px', NAV.CSS)
        self.assertIn('max-width:100%', NAV.CSS)

    def test_small_screen_layout_and_reduced_motion(self):
        self.assertIn("@media(max-width:760px)", NAV.CSS)
        self.assertIn("prefers-reduced-motion:reduce", NAV.CSS)
        self.assertIn("overflow-wrap:anywhere", NAV.CSS)


if __name__ == "__main__":
    unittest.main()
