#!/usr/bin/env python3
"""FM2 dashboard routes layered on the currently verified FM1 source builder."""
from __future__ import annotations
import build_v074_fm1_friends_candidate as prior


def once(src,old,new):
    if src.count(old)!=1:
        raise ValueError("FM2 dashboard baseline drift")
    return src.replace(old,new,1)


def build():
    manager,nav=prior.build()
    src=manager.decode("utf-8")
    menu=nav.decode("utf-8")
    src=once(src,
        "from bob_friends import page as friends_page, dispatch as friends_dispatch, "
        "safe_error as friends_safe_error",
        "from bob_friends import page as friends_page, dispatch as friends_dispatch, "
        "safe_error as friends_safe_error\n"
        "from bob_friend_discovery import (page as discovery_page, "
        "dispatch as discovery_dispatch, profile_lookup, cache_profile, "
        "safe_error as discovery_safe_error)\n"
        "from urllib.parse import quote")
    src=once(src,
        '        elif urlsplit(self.path).path == "/moltbook/friends":',
        '''        elif urlsplit(self.path).path == "/moltbook/discover":
            with publish_conn() as db:
                self._send(200, discovery_page(db,TOKEN,wrap,
                    parse_qs(urlsplit(self.path).query,keep_blank_values=True),
                    load_records()),"text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/moltbook/friends":''')
    src=once(src,
        '        if path == "/moltbook/friends":',
        '''        if path == "/moltbook/discover":
            self._save_discovery()
            return
        if path == "/moltbook/friends":''')
    method='''    def _save_discovery(self):
        if not self._valid_origin():
            self._error_page(403,"Request blocked","Origin check failed")
            return
        try:
            length=int(self.headers.get("Content-Length","-1"))
            if not 0<length<=8192:
                raise ValueError("Invalid discovery form")
            values=parse_qs(self.rfile.read(length).decode("utf-8"),
                            keep_blank_values=True,max_num_fields=12)
            if any(len(v)!=1 for v in values.values()):
                raise ValueError("Invalid discovery form")
            if not hmac.compare_digest(values.get("csrf",[""])[0],TOKEN):
                self._error_page(403,"Request blocked","Invalid CSRF token")
                return
            form={k:v[0] for k,v in values.items()}
            if form.get("operation")=="lookup":
                if set(form)!={"csrf","operation","handle"}:
                    raise ValueError("Invalid discovery form")
                # One deliberate, anonymous, fixed-host HTTPS GET; NO token,
                # agent tools, username-controlled endpoint, or redirects.
                public_profile=profile_lookup(form["handle"])
                with publish_conn() as db:
                    cache_profile(db,public_profile)
                destination="/moltbook/discover?profile="+quote(public_profile["handle"])
            else:
                with publish_conn() as db:
                    discovery_dispatch(db,form)
                destination="/moltbook/discover"
            self.send_response(303)
            self.send_header("Location",destination)
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
            self._error_page(409,"Friend discovery unchanged",discovery_safe_error(exc))

'''
    src=once(src,'    def _save_friend(self):',method+'    def _save_friend(self):')
    src=once(src,
        '"/moltbook/friends" if urlsplit(self.path).path == "/moltbook/friends"',
        '"/moltbook/discover" if urlsplit(self.path).path == "/moltbook/discover" '
        'else "/moltbook/friends" if urlsplit(self.path).path == "/moltbook/friends"')
    anchor='    ("/moltbook/friends", "Moltbook · Friends", "Private contacts, interests and relationship notes"),'
    menu=once(menu,anchor,anchor+'\n'
              '    ("/moltbook/discover", "Moltbook · Discover", '
              '"Read-only profiles and owner-reviewed Scout friend proposals"),')
    compile(src,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return src.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    m,n=build()
    print("FM2 PUBLIC PROFILE AND FRIEND REVIEW CANDIDATE: PASS")
    print("manager_bytes:",len(m),"navigation_bytes:",len(n))
    print("production_modified: NO")
