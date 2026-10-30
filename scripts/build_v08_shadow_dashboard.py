#!/usr/bin/env python3
"""R2 temporary compatibility bridge: two authenticated GET-only shadow routes.

This adapter is deliberately limited to the existing reviewed v0.7.7 Activity
Manager. R3 replaces generated-dashboard patch chains with source templates.
No POST handlers, authentication, CSRF, publisher or service actions change.
"""
from __future__ import annotations
import build_v076_fm41_candidate as prior


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("R2 authenticated dashboard baseline drift")
    return text.replace(old, new, 1)


def build():
    manager, menu = prior.build()
    manager = manager.decode("utf-8")
    menu = menu.decode("utf-8")
    manager = once(manager,
        "from bob_social_memory import page as social_memory_page",
        "from bob_social_memory import page as social_memory_page\n"
        "from bob_v08_bridge import now_page as v08_now_page, inbox_page as v08_inbox_page")
    manager = once(manager,
        '        elif urlsplit(self.path).path == "/moltbook/social-memory":',
        '        elif urlsplit(self.path).path == "/v08/now":\n'
        '            self._send(200,v08_now_page(wrap),"text/html; charset=utf-8")\n'
        '        elif urlsplit(self.path).path == "/v08/inbox":\n'
        '            self._send(200,v08_inbox_page(wrap),"text/html; charset=utf-8")\n'
        '        elif urlsplit(self.path).path == "/moltbook/social-memory":')
    anchor = '    ("/moltbook/social-memory", "Moltbook · Social Memory", "Source-linked private encounters and evolving interests"),'
    menu = once(menu, anchor,
        anchor + '\n'
        '    ("/v08/now", "Bob v0.8 · Shadow Now", "Hypothetical decisions, no external actions"),\n'
        '    ("/v08/inbox", "Bob v0.8 · Shadow Inbox", "Read-only preview and anomalies"),')
    compile(manager, "bob-activity-manager", "exec")
    compile(menu, "navigation_shell.py", "exec")
    return manager.encode("utf-8"), menu.encode("utf-8")


if __name__ == "__main__":
    manager, menu = build()
    print("R2 AUTHENTICATED SHADOW GET ROUTES: PASS")
    print("manager bytes:", len(manager), "navigation bytes:", len(menu))
