#!/usr/bin/env python3
"""Build compact queue management on top of the installed v0.7.2 manager.

This builder only changes the manager's GET/POST routing, adds the management
module import and a navigation entry. Existing single-item routes and
publisher workers are untouched. Source is not installed by this script.
"""
from __future__ import annotations

import build_v072_publication_truth_candidate as previous


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("dashboard baseline changed: refusing queue integration")
    return text.replace(old, new, 1)


def build():
    manager, navigation = previous.build()
    source = manager.decode("utf-8")
    nav = navigation.decode("utf-8")
    source = once(
        source,
        "from bob_status_view import page as status_page, javascript as status_javascript",
        "from bob_status_view import page as status_page, javascript as status_javascript\n"
        "from bob_dashboard_manage import page as queue_manage_page, apply_batch as queue_manage_apply")
    source = once(source, "from urllib.parse import parse_qs, urlsplit",
                  "from urllib.parse import parse_qs, urlsplit, urlencode")
    get_anchor = '        elif self.path == "/originals":'
    get_route = '''        elif urlsplit(self.path).path == "/manage":
            with publish_conn() as db:
                self._send(200, queue_manage_page(
                    db, load_records(), current_status,
                    parse_qs(urlsplit(self.path).query, keep_blank_values=True),
                    TOKEN, wrap), "text/html; charset=utf-8")
'''
    source = once(source, get_anchor, get_route + get_anchor)
    post_anchor = '        path = urlsplit(self.path).path\n'
    post_route = '''        path = urlsplit(self.path).path
        if path == "/manage/bulk":
            self._handle_manage_bulk()
            return
'''
    source = once(source, post_anchor, post_route)
    method_anchor = '    def _handle_original(self, path):'
    new_method = '''    def _handle_manage_bulk(self):
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= 8192:
                raise ValueError("Invalid selection size")
            data = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            if len(data.get("csrf", [])) != 1 or not hmac.compare_digest(data["csrf"][0], TOKEN):
                self._error_page(403, "Request blocked", "Invalid CSRF token")
                return
            for key in ("tab", "operation", "confirmation"):
                if len(data.get(key, [])) != 1:
                    raise ValueError("Missing or duplicate bulk field")
            tab = data["tab"][0]
            operation = data["operation"][0]
            selected = data.get("selected", [])
            confirmation = data["confirmation"][0]
            with publish_conn() as db:
                changed = queue_manage_apply(db, load_records(), current_status,
                                             tab, operation, selected, confirmation)
                db.commit()
            # Only locally constructed, bounded filter values are returned.
            state = data.get("state", ["all"])[0][:36]
            show = data.get("show", ["active"])[0][:12]
            search = data.get("q", [""])[0][:64]
            pg = data.get("page", ["1"])[0][:4]
            if not re.fullmatch(r"[a-z_ ]{1,36}", state): state = "all"
            if show not in ("active", "archived", "all"): show = "active"
            if not re.fullmatch(r"[1-9][0-9]{0,3}", pg): pg = "1"
            location = "/manage?" + urlencode(dict(tab=tab, state=state,
                                                   show=show, q=search,
                                                   page=pg))
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (ValueError, UnicodeError, sqlite3.Error, OSError) as exc:
            self._error_page(409, "Bulk action not completed",
                             "No selections changed. " + str(exc)[:160])

'''
    source = once(source, method_anchor, new_method + method_anchor)
    nav_anchor = '    ("/originals", "Original posts", "Original posts"),'
    nav = once(nav, nav_anchor, nav_anchor + '\n    ("/manage", "Manage queues", "Manage queues"),')
    compile(source, "bob-activity-manager", "exec")
    compile(nav, "navigation_shell.py", "exec")
    return source.encode("utf-8"), nav.encode("utf-8")


if __name__ == "__main__":
    manager, nav = build()
    print("BOB QUEUE MANAGEMENT CANDIDATE: PASS")
    print("manager_bytes:", len(manager), "navigation_bytes:", len(nav))
    print("production_modified: NO")
