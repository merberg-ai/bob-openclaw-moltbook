#!/usr/bin/env python3
"""PM2.1: add a private, operator-curated memory page to the PM1 Activity Manager.

Exact source anchors, no modification to existing routes or publishers.
The memory store is an additive module and remains disconnected from agents.
"""
from __future__ import annotations
import build_v073_pm1_apply_candidate as prior


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("PM2 candidate baseline changed; refusing source patch")
    return text.replace(old, new, 1)


def build():
    manager, nav = prior.build()
    source = manager.decode("utf-8")
    navigation = nav.decode("utf-8")
    source = once(
        source, "apply as personality_apply, rollback as personality_rollback",
        "apply as personality_apply, rollback as personality_rollback\n"
        "from bob_memory import page as memory_page, dispatch as memory_dispatch")
    source = once(
        source, '        elif self.path == "/mind/personality":',
        '''        elif urlsplit(self.path).path == "/mind/memory":
            with publish_conn() as db:
                self._send(200, memory_page(db,
                    parse_qs(urlsplit(self.path).query, keep_blank_values=True),
                    TOKEN, wrap), "text/html; charset=utf-8")
        elif self.path == "/mind/personality":''')
    source = once(
        source, '        if path in ("/mind/personality/apply", "/mind/personality/rollback"):',
        '''        if path == "/mind/memory":
            self._save_memory()
            return
        if path in ("/mind/personality/apply", "/mind/personality/rollback"):''')
    handler = '''    def _save_memory(self):
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= 16384:
                raise ValueError("Memory form size invalid")
            data = parse_qs(self.rfile.read(length).decode("utf-8"),
                            keep_blank_values=True, max_num_fields=12)
            if any(len(values) != 1 for values in data.values()):
                raise ValueError("Duplicate memory form fields")
            if not hmac.compare_digest(data.get("csrf", [""])[0], TOKEN):
                self._error_page(403, "Request blocked", "Invalid CSRF token")
                return
            form = {key: values[0] for key, values in data.items()}
            with publish_conn() as db:
                memory_id = memory_dispatch(db, form)
            self.send_response(303)
            self.send_header("Location", "/mind/memory?edit=" + memory_id)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (ValueError, TypeError, UnicodeError, OSError, sqlite3.Error):
            self._error_page(409, "Memory unchanged",
                             "Reload and check all memory fields, source URL, and current revision")

'''
    source = once(source, '    def _apply_personality(self, path):',
                  handler + '    def _apply_personality(self, path):')
    nav_anchor = '    ("/mind/personality", "Bob\'s Mind · Personality", "Personality and profile staging"),'
    navigation = once(navigation, nav_anchor,
                      nav_anchor + '\n    ("/mind/memory", "Bob\'s Mind · Memory", "Private curated memory manager"),')
    compile(source, "bob-activity-manager", "exec")
    compile(navigation, "navigation_shell.py", "exec")
    return source.encode("utf-8"), navigation.encode("utf-8")


if __name__ == "__main__":
    manager, navigation = build()
    print("PM2 PRIVATE MEMORY FOUNDATION: PASS")
    print("manager_bytes:", len(manager), "navigation_bytes:", len(navigation))
    print("production_modified: NO")
