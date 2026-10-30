#!/usr/bin/env python3
"""FM3.2d: launch manual one-friend public focus worker after existing guarded POST.

No changes to authentication, CSRF, Host/Origin checking, publish handlers,
automatic Scout, timers or navigation. Pinned to FM3.2c builder output.
"""
from __future__ import annotations
import build_v075_fm32c_candidate as prior


def once(src,old,new):
    if src.count(old)!=1:
        raise ValueError("FM3.2d manager baseline drift; refusing release build")
    return src.replace(old,new,1)


def build():
    old,nav=prior.build()
    code=old.decode("utf-8")
    code=once(code,
        "interest_ai_worker as friend_interest_ai_worker)",
        "interest_ai_worker as friend_interest_ai_worker, "
        "focus_worker as friend_focus_worker)")
    code=once(code,
        "                    name='bob-friend-interest-ai').start()\n"
        "            self.send_response(303)",
        "                    name='bob-friend-interest-ai').start()\n"
        "            if isinstance(outcome,str) and outcome.startswith('focus-job:'):\n"
        "                threading.Thread(target=friend_focus_worker,\n"
        "                    args=(outcome[10:],publish_conn),daemon=True,\n"
        "                    name='bob-friend-focus').start()\n"
        "            self.send_response(303)")
    compile(code,"bob-activity-manager","exec")
    return code.encode("utf-8"),nav


if __name__=="__main__":
    manager,nav=build()
    print("FM3.2d MANUAL PUBLIC FOCUS CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
