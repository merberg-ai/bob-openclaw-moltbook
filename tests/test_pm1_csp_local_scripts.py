"""CSP regression: enabled local dashboard JS without opening other origins.

Offline, no dashboard services or Moltbook traffic. No active host changes.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
for folder in ("scripts","src/lib/bob","webui"):
    sys.path.insert(0,str(ROOT/folder))
import build_v073_pm1_csp_candidate as after
import build_v073_pm1_personality_candidate as before
from bob_personality import javascript as personality_js
from bob_overview import javascript as overview_js


def handler_methods(code):
    tree=ast.parse(code)
    h=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="Handler")
    return {f.name:ast.dump(f,include_attributes=False)
            for f in h.body if isinstance(f,ast.FunctionDef)}


class CSPTests(unittest.TestCase):
    def test_only_csp_condition_changes_in_generated_manager(self):
        old,old_nav=before.build()
        new,new_nav=after.build()
        old_code=old.decode()
        new_code=new.decode()
        old_fragment="""("Content-Security-Policy", ("default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" if self.path == "/system/status" else "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"))"""
        self.assertEqual(old_code.count(old_fragment),1)
        expected=old_code.replace(old_fragment,old_fragment.replace(after.OLD,after.NEW),1)
        self.assertEqual(new_code,expected)
        self.assertEqual(new_nav,old_nav)

    def test_script_permissions_are_limited_to_three_pages(self):
        manager,_=after.build()
        code=manager.decode()
        self.assertEqual(code.count(after.NEW),1)
        policy=next(line for line in code.splitlines()
                    if '("Content-Security-Policy",' in line)
        permitted=policy.split('" if urlsplit(self.path).path in ')[0]
        self.assertIn("script-src 'self'",permitted)
        self.assertIn("connect-src 'self'",permitted)
        self.assertIn("default-src 'none'",policy)
        self.assertIn("frame-ancestors 'none'",policy)
        self.assertIn("base-uri 'none'",policy)
        self.assertIn("form-action 'self'",policy)
        self.assertIn("""else "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"""",policy)
        self.assertIn('("/system/status", "/", "/mind/personality")',policy)
        self.assertNotIn("script-src 'unsafe-inline'",policy)
        self.assertNotIn("'unsafe-eval'",policy)
        self.assertNotIn("https:",policy)
        self.assertNotIn("http:",policy)
        self.assertNotIn("data:",policy)
        self.assertNotIn("*",policy)

    def test_both_js_endpoints_and_refresh_still_exist(self):
        source=after.build()[0].decode()
        self.assertIn('elif self.path == "/assets/bob-personality.js":',source)
        self.assertIn('elif self.path == "/assets/bob-overview.js":',source)
        self.assertIn('"application/javascript; charset=utf-8"',source)
        self.assertIn('elif self.path == "/api/dashboard/overview":',source)
        self.assertIn('src="/assets/bob-personality.js"', (ROOT/"src/lib/bob/bob_personality.py").read_text())
        self.assertIn('src="/assets/bob-overview.js"', (ROOT/"src/lib/bob/bob_overview.py").read_text())
        self.assertIn("preview.textContent",personality_js())
        self.assertIn("input[data-bpm-trait]",personality_js())
        self.assertIn("fetch('/api/dashboard/overview'",overview_js())
        self.assertIn("setInterval(refresh,15000)",overview_js())

    def test_approval_auth_and_settings_methods_are_unchanged(self):
        a=handler_methods(before.build()[0])
        b=handler_methods(after.build()[0])
        self.assertEqual(set(a),set(b))
        for name in a:
            if name!="_headers":
                self.assertEqual(a[name],b[name],name)
        self.assertNotEqual(a["_headers"],b["_headers"])


if __name__=="__main__":
    unittest.main()
