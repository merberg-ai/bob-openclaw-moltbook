#!/usr/bin/env python3
"""Allow local scripts on Overview/Personality, retaining existing Status CSP.

The v0.7.2 manager already conditionally permits same-origin scripts ONLY for
/system/status. Expand that allowlist to the two newer script-backed pages.
All other paths retain the identical default-src 'none' fallback.
"""
from __future__ import annotations

import build_v073_pm1_personality_candidate as previous

OLD = 'if self.path == "/system/status"'
NEW = 'if urlsplit(self.path).path in ("/system/status", "/", "/mind/personality")'


def build():
    manager, navigation = previous.build()
    source = manager.decode("utf-8")
    # Anchor the existing conditional to its CSP header, not another route.
    fragment = '''("Content-Security-Policy", ("default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" if self.path == "/system/status" else "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"))'''
    if source.count(fragment)!=1:
        raise ValueError("Manager conditional CSP baseline drift; refusing patch")
    source=source.replace(fragment, fragment.replace(OLD,NEW), 1)
    compile(source,"bob-activity-manager","exec")
    compile(navigation,"navigation_shell.py","exec")
    return source.encode("utf-8"),navigation


if __name__ == "__main__":
    manager,nav=build()
    print("PM1 SAME-ORIGIN CSP FIX: CANDIDATE BUILT")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
