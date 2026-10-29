#!/usr/bin/env python3
"""Build focused v0.7.2 live-status UI update on installed styled v0.7.2.

Keeps the existing password form, login semantics, existing routes and job
database untouched. No production install or service change by this builder.
"""
from __future__ import annotations

import build_v072_settings_candidate as current

CSP_OLD = """("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")"""
CSP_NEW = """("Content-Security-Policy", ("default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" if self.path == "/system/status" else "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"))"""

def build():
    baseline, navigation = current.build(styled=True)
    source = baseline.decode("utf-8")
    if source.count(CSP_OLD) != 1:
        raise ValueError("unexpected current CSP: refusing to alter policy")
    source = source.replace(CSP_OLD, CSP_NEW, 1)
    old_import = "from bob_live_status import snapshot as status_snapshot"
    if source.count(old_import) != 1:
        raise ValueError("unexpected v0.7.2 status import")
    source = source.replace(old_import, old_import + "\nfrom bob_status_view import page as status_page, javascript as status_javascript", 1)
    begin = source.index('        elif self.path == "/system/status":')
    end = source.index('        elif self.path == "/settings":', begin)
    expected = source[begin:end]
    if 'status_snapshot()' not in expected or 'meta http-equiv="refresh"' not in expected:
        raise ValueError("refusing unexpected existing status handler")
    new_handler = """        elif self.path == "/system/status":
            self._send(200, status_page(status_snapshot()), "text/html; charset=utf-8")
        elif self.path == "/assets/bob-status.js":
            self._send(200, status_javascript(), "application/javascript; charset=utf-8")
"""
    source = source[:begin] + new_handler + source[end:]
    compile(source, "bob-activity-manager", "exec")
    return source.encode("utf-8"), navigation

if __name__ == "__main__":
    manager, navigation = build()
    print("v0.7.2 STATUS UI CANDIDATE: PASS")
    print("manager_bytes:", len(manager), "navigation_bytes:", len(navigation))
    print("production_modified: NO")
