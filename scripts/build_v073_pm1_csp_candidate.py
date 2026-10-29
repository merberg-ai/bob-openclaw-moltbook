#!/usr/bin/env python3
"""Permit only authenticated same-origin dashboard scripts and status fetching.

The pinned Activity Manager default-src 'none' CSP preceded JavaScript-backed
Overview and Personality pages. Changing the CSP header is the only runtime
difference: no inline execution, third-party scripts, or API cross-origin.
"""
from __future__ import annotations

import build_v073_pm1_personality_candidate as previous


def build():
    manager, navigation = previous.build()
    source = manager.decode("utf-8")
    old = """("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")"""
    new = """("Content-Security-Policy", "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")"""
    if source.count(old) != 1:
        raise ValueError("Manager CSP baseline drift; refusing patch")
    source = source.replace(old,new,1)
    compile(source,"bob-activity-manager","exec")
    compile(navigation,"navigation_shell.py","exec")
    return source.encode("utf-8"),navigation


if __name__ == "__main__":
    manager,nav=build()
    print("PM1 SAME-ORIGIN CSP FIX: CANDIDATE BUILT")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
