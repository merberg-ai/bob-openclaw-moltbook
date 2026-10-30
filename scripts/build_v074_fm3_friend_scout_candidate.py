#!/usr/bin/env python3
"""FM3: gated friend-scanning toggle and visibility on authenticated dashboard."""
from __future__ import annotations
import build_v074_fm2_discovery_candidate as prior


def once(source,old,new):
    if source.count(old)!=1:
        raise ValueError("FM3 generated Activity Manager baseline drift")
    return source.replace(old,new,1)


def build():
    manager,nav=prior.build()
    src=manager.decode("utf-8")
    menu=nav.decode("utf-8")
    src=once(src,
        "from bob_friend_discovery import (page as discovery_page, "
        "dispatch as discovery_dispatch, profile_lookup, cache_profile, "
        "safe_error as discovery_safe_error)",
        "from bob_friend_discovery import (page as discovery_page, "
        "dispatch as discovery_dispatch, profile_lookup, cache_profile, "
        "safe_error as discovery_safe_error)\n"
        "from bob_friend_scout import (page as friend_scout_page, change as friend_scout_change, "
        "safe_error as friend_scout_safe_error)")
    src=once(src,
        '        elif urlsplit(self.path).path == "/moltbook/discover":',
        '''        elif urlsplit(self.path).path == "/moltbook/friend-scout":
            with publish_conn() as db:
                self._send(200,friend_scout_page(db,TOKEN,wrap,load_records()),
                           "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/moltbook/discover":''')
    src=once(src,
        '        if path == "/moltbook/discover":',
        '''        if path == "/moltbook/friend-scout":
            self._save_friend_scout()
            return
        if path == "/moltbook/discover":''')
    method='''    def _save_friend_scout(self):
        if not self._valid_origin():
            self._error_page(403,"Request blocked","Origin check failed")
            return
        try:
            length=int(self.headers.get("Content-Length","-1"))
            if not 0<length<=2048:
                raise ValueError("Invalid friend scouting form")
            values=parse_qs(self.rfile.read(length).decode("utf-8"),
                            keep_blank_values=True,max_num_fields=6)
            if any(len(v)!=1 for v in values.values()):
                raise ValueError("Invalid friend scouting form")
            if not hmac.compare_digest(values.get("csrf",[""])[0],TOKEN):
                self._error_page(403,"Request blocked","Invalid CSRF token")
                return
            form={k:v[0] for k,v in values.items()}
            with publish_conn() as db:
                friend_scout_change(db,form)
            self.send_response(303)
            self.send_header("Location","/moltbook/friend-scout")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
            self._error_page(409,"Friend scout setting unchanged",friend_scout_safe_error(exc))

'''
    src=once(src,'    def _save_discovery(self):',
             method+'    def _save_discovery(self):')
    src=once(src,
        '"/moltbook/discover" if urlsplit(self.path).path == "/moltbook/discover"',
        '"/moltbook/friend-scout" if urlsplit(self.path).path == "/moltbook/friend-scout" '
        'else "/moltbook/discover" if urlsplit(self.path).path == "/moltbook/discover"')
    anchor='    ("/moltbook/discover", "Moltbook · Discover", "Read-only profiles and owner-reviewed Scout friend proposals"),'
    menu=once(menu,anchor,anchor+'\n'
              '    ("/moltbook/friend-scout", "Moltbook · Friend Scout", '
              '"Opt-in friend-focused scouting and watchlist"),')
    compile(src,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return src.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    m,n=build()
    print("FM3 FRIEND-FOCUSED SCOUT CANDIDATE: PASS")
    print("manager_bytes:",len(m),"navigation_bytes:",len(n))
    print("production_modified: NO")
