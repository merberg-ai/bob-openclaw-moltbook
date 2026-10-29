#!/usr/bin/env python3
"""Correct dashboard POST redirects after Scout moved from / to /scout.

Source-only builder. Exact anchors ensure reviewed approval, authentication,
database, and publishing implementations are otherwise preserved.
"""
from __future__ import annotations

import build_v072_overview_candidate as prior


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("dashboard route baseline changed; refusing redirect patch")
    return source.replace(old, new, 1)


def build():
    manager, navigation = prior.build()
    source = manager.decode("utf-8")
    source = once(source,
        "from bob_overview import page as overview_page, snapshot as overview_snapshot, javascript as overview_javascript",
        "from bob_overview import page as overview_page, snapshot as overview_snapshot, javascript as overview_javascript\n"
        "from bob_dashboard_return import scout_destination, section_for_action")
    # Full legacy Scout history is still an actionable page. It must return
    # to its own route, not silently drop users into the new compact view.
    for action in (
        "/review/{stamp}/{act}", "/publish/{stamp}", "/verify/{stamp}",
        "/autopost/enable", "/autopost/disable",
    ):
        source = once(source,
            'action="' + action + '"><input type="hidden" name="csrf"',
            'action="' + action + '"><input type="hidden" name="return_to" '
            'value="/scout/full"><input type="hidden" name="csrf"')
    # Every Scout action validates its return location before writing to DB.
    source = once(source,
        "            run_id, operation = action.groups()\n",
        "            run_id, operation = action.groups()\n"
        "            destination = scout_destination(params, run_id)\n")
    source = once(source,
        'self.send_header("Location", f"/#run-{run_id}")',
        'self.send_header("Location", destination)')
    source = once(source,
        "            with publish_conn() as db:\n                if mode:\n",
        "            destination = scout_destination(\n"
        "                data, publish.group(1) if publish else challenge.group(1) if challenge else None)\n"
        "            with publish_conn() as db:\n                if mode:\n")
    source = once(source,
        "self.send_header('Location','/')",
        "self.send_header('Location',destination)")
    # Error pages should also return to the section that submitted the form.
    source = once(source,
        '<p><a href="/">Return to Activity Manager</a></p>',
        '<p><a href="{esc(section_for_action(self.path))}">Return to section</a></p>')
    compile(source, "bob-activity-manager", "exec")
    compile(navigation, "navigation_shell.py", "exec")
    return source.encode("utf-8"), navigation


if __name__ == "__main__":
    mgr, nav = build()
    print("BOB POST REDIRECT CANDIDATE: PASS")
    print("manager_bytes:", len(mgr), "navigation_bytes:", len(nav))
    print("production_modified: NO")
