#!/usr/bin/env python3
"""Integrate compact Scout/Activity views onto the reviewed live manager.

Only authenticated GET render routing changes. Existing POST validation,
approval hashes, publishing routes and worker binaries are preserved.
"""
from __future__ import annotations

import build_v072_dashboard_manage_candidate as prior


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("manager baseline changed; refusing compact page build")
    return source.replace(old,new,1)


def build():
    manager, navigation = prior.build()
    source = manager.decode("utf-8")
    source = once(
        source,
        "from bob_dashboard_manage import page as queue_manage_page, apply_batch as queue_manage_apply",
        "from bob_dashboard_manage import page as queue_manage_page, apply_batch as queue_manage_apply\n"
        "from bob_dashboard_compact import scout_page as compact_scout, activity_page as compact_activity")
    scout = '''        elif self.path == "/":
            self._send(200, integrate_existing_html(render(), '/'), "text/html; charset=utf-8")
'''
    scout_new = '''        elif urlsplit(self.path).path == "/":
            with publish_conn() as db:
                self._send(200, compact_scout(
                    db, load_records(), current_status,
                    parse_qs(urlsplit(self.path).query, keep_blank_values=True),
                    TOKEN, wrap), "text/html; charset=utf-8")
'''
    source = once(source,scout,scout_new)
    activity = '''        elif self.path == "/activity":
            self._send(200, integrate_existing_html(activity_page(), '/activity'), "text/html; charset=utf-8")
'''
    activity_new = '''        elif urlsplit(self.path).path == "/activity":
            with publish_conn() as db:
                self._send(200, compact_activity(
                    db, parse_qs(urlsplit(self.path).query, keep_blank_values=True),
                    wrap), "text/html; charset=utf-8")
'''
    source = once(source,activity,activity_new)
    orig = '        elif self.path == "/originals":'
    detail_routes = '''        elif self.path == "/scout/full":
            self._send(200, integrate_existing_html(render(), '/'), "text/html; charset=utf-8")
        elif self.path == "/activity/full":
            self._send(200, integrate_existing_html(activity_page(), '/activity'),
                       "text/html; charset=utf-8")
'''
    source = once(source,orig,detail_routes+orig)
    compile(source,"bob-activity-manager","exec")
    compile(navigation,"navigation_shell.py","exec")
    return source.encode("utf-8"), navigation


if __name__ == "__main__":
    manager, nav = build()
    print("BOB COMPACT SCOUT/ACTIVITY CANDIDATE: PASS")
    print("manager_bytes:", len(manager), "navigation_bytes:", len(nav))
    print("production_modified: NO")
