#!/usr/bin/env python3
"""Build reviewed mission-control home page over current Activity Limits release.

Only GET routes, dedicated overview endpoints and nav labels are updated.
Existing POST handlers and publishing code remain untouched.
"""
from __future__ import annotations
import build_v072_activity_limits_candidate as prior


def once(src, old, new):
    if src.count(old) != 1:
        raise ValueError("overview baseline changed: refusing release")
    return src.replace(old, new, 1)


def build():
    manager, navigation = prior.build()
    source = manager.decode("utf-8")
    nav = navigation.decode("utf-8")
    source = once(source,
        "from bob_activity_limits import overview as limits_overview, users_page as limits_users_page, "
        "activity_page as limits_activity_page, save_limits as limits_save, FIELDS as limits_fields",
        "from bob_activity_limits import overview as limits_overview, users_page as limits_users_page, "
        "activity_page as limits_activity_page, save_limits as limits_save, FIELDS as limits_fields\n"
        "from bob_overview import page as overview_page, snapshot as overview_snapshot, javascript as overview_javascript")
    old = '''        elif urlsplit(self.path).path == "/":
            with publish_conn() as db:
                self._send(200, compact_scout(
                    db, load_records(), current_status,
                    parse_qs(urlsplit(self.path).query, keep_blank_values=True),
                    TOKEN, wrap), "text/html; charset=utf-8")
'''
    new = '''        elif urlsplit(self.path).path == "/":
            self._send(200, overview_page(overview_snapshot()), "text/html; charset=utf-8")
        elif self.path == "/api/dashboard/overview":
            self._send(200, json.dumps(overview_snapshot()), "application/json")
        elif self.path == "/assets/bob-overview.js":
            self._send(200, overview_javascript(), "application/javascript; charset=utf-8")
        elif urlsplit(self.path).path == "/scout":
            with publish_conn() as db:
                self._send(200, compact_scout(
                    db, load_records(), current_status,
                    parse_qs(urlsplit(self.path).query, keep_blank_values=True),
                    TOKEN, wrap), "text/html; charset=utf-8")
'''
    source = once(source, old, new)
    # The complete historical Scout report still uses the original renderer,
    # but its wrapper should highlight Scout rather than the Overview landing.
    source = once(source,
        'self._send(200, integrate_existing_html(render(), \'/\'), "text/html; charset=utf-8")',
        'self._send(200, integrate_existing_html(render(), \'/scout\'), "text/html; charset=utf-8")')
    nav = once(nav,
        '    ("/", "Scout & review", "Scout and review"),',
        '    ("/", "Overview", "Live overview"),\n'
        '    ("/scout", "Scout & review", "Scout and review"),')
    compile(source,"bob-activity-manager","exec")
    compile(nav,"navigation_shell.py","exec")
    return source.encode("utf-8"), nav.encode("utf-8")


if __name__ == "__main__":
    manager,nav=build()
    print("BOB OVERVIEW DASHBOARD: CANDIDATE BUILT")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
