#!/usr/bin/env python3
"""Build Settings > Users / Activity Limits on top of the deployed compact UI.

Strict source anchors; this returns bytes only and never installs or publishes.
"""
from __future__ import annotations

import build_v072_compact_candidate as previous


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("unexpected installed dashboard candidate; refusing UI patch")
    return text.replace(old, new, 1)


def build():
    manager, nav = previous.build()
    source = manager.decode("utf-8")
    source = once(
        source,
        "from bob_dashboard_compact import scout_page as compact_scout, activity_page as compact_activity",
        "from bob_dashboard_compact import scout_page as compact_scout, activity_page as compact_activity\n"
        "from bob_activity_limits import overview as limits_overview, users_page as limits_users_page, "
        "activity_page as limits_activity_page, save_limits as limits_save, FIELDS as limits_fields")
    original_route = '''        elif self.path == "/settings":
            self._send(200, self._settings_page(), "text/html; charset=utf-8")
'''
    replacement = '''        elif self.path == "/settings":
            self._send(200, limits_overview(wrap), "text/html; charset=utf-8")
        elif self.path == "/settings/users":
            self._send(200, limits_users_page(self._settings_page), "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/settings/activity-limits":
            query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
            # Preview only; recommendations are never saved through GET.
            preview = query.get("preset") == ["recommended"]
            with publish_conn() as db:
                self._send(200, limits_activity_page(
                    db, TOKEN, wrap, preview=preview), "text/html; charset=utf-8")
'''
    source = once(source, original_route, replacement)
    original_post = '''        if path == "/settings/password":
            self._change_password()
            return
'''
    additional_post = '''        if path == "/settings/activity-limits":
            self._change_activity_limits()
            return
'''
    source = once(source, original_post, original_post + additional_post)
    marker = '    def _change_password(self):'
    handler = '''    def _change_activity_limits(self):
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= 4096:
                raise ValueError("Invalid activity settings form size")
            values = parse_qs(self.rfile.read(length).decode("utf-8"),
                              keep_blank_values=True, max_num_fields=12)
            names = {entry[0] for entry in limits_fields}
            required = names | {"csrf", "confirmation"}
            if set(values) != required or any(len(values[x]) != 1 for x in required):
                raise ValueError("Invalid activity settings fields")
            if not hmac.compare_digest(values["csrf"][0], TOKEN):
                self._error_page(403, "Request blocked", "Invalid CSRF token")
                return
            if values["confirmation"][0] != "APPLY LIMITS":
                raise ValueError("Exact APPLY LIMITS approval is required")
            proposed = {name: values[name][0] for name in names}
            with publish_conn() as db:
                limits_save(db, proposed)
            self.send_response(303)
            self.send_header("Location", "/settings/activity-limits")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (ValueError, UnicodeError, OSError, sqlite3.Error):
            self._error_page(400, "Activity limits unchanged",
                             "Check numeric limits and type APPLY LIMITS exactly")

'''
    source = once(source, marker, handler + marker)
    compile(source, "bob-activity-manager", "exec")
    compile(nav, "navigation_shell.py", "exec")
    return source.encode("utf-8"), nav


if __name__ == "__main__":
    m, nav = build()
    print("BOB ACTIVITY LIMITS CANDIDATE: PASS")
    print("manager_bytes:",len(m),"navigation_bytes:",len(nav))
    print("production_modified: NO")
