#!/usr/bin/env python3
"""PM1 staged Personality Lab integration over installed v0.7.2 redirects1.

Add one authenticated dashboard GET, one scoped POST, one static JS route,
and one navigation item. Only owner-staged profile metadata is persisted.
"""
from __future__ import annotations
import build_v072_post_redirect_candidate as prior


def once(code, anchor, replacement):
    if code.count(anchor)!=1:
        raise ValueError("PM1 baseline drift: refusing to build manager")
    return code.replace(anchor,replacement,1)


def build():
    manager, navigation = prior.build()
    source = manager.decode("utf-8")
    nav = navigation.decode("utf-8")
    source = once(source,
        "from bob_dashboard_return import scout_destination, section_for_action",
        "from bob_dashboard_return import scout_destination, section_for_action\n"
        "from bob_personality import page as personality_page, javascript as personality_js, "
        "store_profile as personality_store, KEYS as personality_keys")
    source = once(source,
        '''        elif urlsplit(self.path).path == "/scout":
            with publish_conn() as db:
                self._send(200, compact_scout(''',
        '''        elif self.path == "/mind/personality":
            with publish_conn() as db:
                self._send(200, personality_page(db, TOKEN, wrap), "text/html; charset=utf-8")
        elif self.path == "/assets/bob-personality.js":
            self._send(200, personality_js(), "application/javascript; charset=utf-8")
        elif urlsplit(self.path).path == "/scout":
            with publish_conn() as db:
                self._send(200, compact_scout(''')
    source = once(source,
        '''        if path == "/settings/activity-limits":
            self._change_activity_limits()
            return''',
        '''        if path == "/mind/personality":
            self._save_personality()
            return
        if path == "/settings/activity-limits":
            self._change_activity_limits()
            return''')
    method = '''    def _save_personality(self):
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= 4096:
                raise ValueError("Invalid profile form size")
            form = parse_qs(self.rfile.read(length).decode("utf-8"),
                            keep_blank_values=True, max_num_fields=12)
            if any(len(values)!=1 for values in form.values()):
                raise ValueError("Duplicate profile field")
            if not hmac.compare_digest(form.get("csrf", [""])[0], TOKEN):
                self._error_page(403, "Request blocked", "Invalid CSRF token")
                return
            action = form.get("mode", [""])[0]
            if action == "save":
                if set(form) != set(personality_keys) | {"csrf", "mode"}:
                    raise ValueError("Unexpected personality fields")
                values = {key:form[key][0] for key in personality_keys}
                with publish_conn() as db:
                    personality_store(db, values)
            elif action == "restore":
                if set(form) != {"csrf","mode","revision"}:
                    raise ValueError("Unexpected restore fields")
                with publish_conn() as db:
                    personality_store(db, None, restore_id=form["revision"][0])
            else:
                raise ValueError("Unknown personality action")
            self.send_response(303)
            self.send_header("Location", "/mind/personality")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (ValueError, TypeError, UnicodeError, OSError, sqlite3.Error):
            self._error_page(400, "Personality unchanged",
                             "Check that each slider is 0–100 in steps of five and reload the page")

'''
    source = once(source, '    def _change_activity_limits(self):',
                  method+'    def _change_activity_limits(self):')
    source = once(source,
        '<p><a href="{esc(section_for_action(self.path))}">Return to section</a></p>',
        '<p><a href="{esc("/mind/personality" if urlsplit(self.path).path == "/mind/personality" else section_for_action(self.path))}">Return to section</a></p>')
    nav = once(nav,
        '    ("/settings", "Settings", "Settings"),',
        '    ("/mind/personality", "Bob\\'s Mind · Personality", "Personality and profile staging"),\n'
        '    ("/settings", "Settings", "Settings"),')
    compile(source,"bob-activity-manager","exec")
    compile(nav,"navigation_shell.py","exec")
    return source.encode("utf-8"),nav.encode("utf-8")


if __name__=="__main__":
    manager,nav=build()
    print("PM1 PERSONALITY LAB CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
