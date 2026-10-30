#!/usr/bin/env python3
"""Add a read-only filtered /logs page to the verified FM3 Activity Manager."""
from __future__ import annotations
import build_v074_fm3_friend_scout_candidate as prior


def once(source,old,new):
    if source.count(old)!=1:
        raise ValueError("Logs dashboard baseline drift; refusing generated files")
    return source.replace(old,new,1)


def build():
    manager,navigation=prior.build()
    src=manager.decode("utf-8")
    menu=navigation.decode("utf-8")
    src=once(
        src,
        "from bob_friend_scout import (page as friend_scout_page, change as friend_scout_change, "
        "safe_error as friend_scout_safe_error)",
        "from bob_friend_scout import (page as friend_scout_page, change as friend_scout_change, "
        "safe_error as friend_scout_safe_error)\n"
        "from bob_diagnostic_logs import page as diagnostics_page")
    src=once(
        src,
        '        elif urlsplit(self.path).path == "/moltbook/friend-scout":',
        '''        elif urlsplit(self.path).path == "/logs":
            self._send(200, diagnostics_page(wrap,
                parse_qs(urlsplit(self.path).query,keep_blank_values=True)),
                "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/moltbook/friend-scout":''')
    # This page is GET only. All previous writes and authorization handlers
    # remain byte/AST-identical; the old authenticated dispatch remains first.
    src=once(
        src,
        '"/moltbook/friend-scout" if urlsplit(self.path).path == "/moltbook/friend-scout"',
        '"/logs" if urlsplit(self.path).path == "/logs" '
        'else "/moltbook/friend-scout" if urlsplit(self.path).path == "/moltbook/friend-scout"')
    nav_anchor='    ("/moltbook/friend-scout", "Moltbook · Friend Scout", "Opt-in friend-focused scouting and watchlist"),'
    menu=once(menu,nav_anchor,nav_anchor+'\n'
              '    ("/logs", "Logs", "Filter worker failures, job reasons and redacted system journals"),')
    compile(src,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return src.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    m,n=build()
    print("BOB FILTERED LOGS CANDIDATE: PASS")
    print("manager_bytes:",len(m),"navigation_bytes:",len(n))
    print("production_modified: NO")
