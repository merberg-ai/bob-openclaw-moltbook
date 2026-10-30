#!/usr/bin/env python3
"""FM3.2c: authenticated local-only Friend Scout AI job launcher.

Patch ONLY the verified FM3.2b manager builder output. Existing Basic auth,
Origin, Host, CSRF and six-field form limits run before generation can start.
Worker starts after queued DB transaction commits; dashboard remains responsive.
"""
from __future__ import annotations
import build_v075_fm32b_candidate as prior


def once(text,old,new):
    if text.count(old)!=1:
        raise ValueError("FM3.2c manager baseline drift; refusing release build")
    return text.replace(old,new,1)


def build():
    manager,nav=prior.build()
    code=manager.decode("utf-8")
    code=once(code,
        "watchlist_location as friend_scout_return_path)",
        "watchlist_location as friend_scout_return_path, "
        "interest_ai_worker as friend_interest_ai_worker)")
    code=once(code,
        "                friend_scout_change(db,form)\n"
        "            self.send_response(303)",
        "                outcome=friend_scout_change(db,form)\n"
        "            if isinstance(outcome,str) and outcome.startswith('ai-job:'):\n"
        "                threading.Thread(target=friend_interest_ai_worker,\n"
        "                    args=(outcome[7:],publish_conn),daemon=True,\n"
        "                    name='bob-friend-interest-ai').start()\n"
        "            self.send_response(303)")
    compile(code,"bob-activity-manager","exec")
    return code.encode("utf-8"),nav


if __name__=="__main__":
    manager,nav=build()
    print("FM3.2c LOCAL INTEREST AI CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
