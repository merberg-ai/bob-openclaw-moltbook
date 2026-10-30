#!/usr/bin/env python3
"""FM3.2b: pass bounded GET filters to Friend Scout and retain view after watch POST.

Derives from the installed Logs-era dashboard builder. Never touches auth,
CSRF, Origin, publication/Scout worker code, or navigation. No new imports
beyond an existing installed managed module.
"""
from __future__ import annotations
import build_v075_logs_candidate as prior


def once(source,old,new):
    if source.count(old)!=1:
        raise ValueError("FM3.2b dashboard baseline drift; refusing release build")
    return source.replace(old,new,1)


def build():
    manager,navigation=prior.build()
    src=manager.decode("utf-8")
    src=once(src,
        "safe_error as friend_scout_safe_error)",
        "safe_error as friend_scout_safe_error, "
        "watchlist_location as friend_scout_return_path)")
    src=once(src,
        "friend_scout_page(db,TOKEN,wrap,load_records())",
        "friend_scout_page(db,TOKEN,wrap,load_records(),"
        "parse_qs(urlsplit(self.path).query[:256],keep_blank_values=True))")
    src=once(src,
        'self.send_header("Location","/moltbook/friend-scout")',
        'self.send_header("Location",friend_scout_return_path(self.path))')
    compile(src,"bob-activity-manager","exec")
    return src.encode("utf-8"),navigation


if __name__=="__main__":
    manager,nav=build()
    print("FM3.2b WATCHLIST DASHBOARD CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
