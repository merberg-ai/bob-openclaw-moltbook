#!/usr/bin/env python3
"""FM4.1: one authenticated read-only Social Memory GET route and nav item.

Pinned to OC4 manager (unchanged by OC4.1); no POST, CSRF, auth, publishing,
worker, timer, or Gateway code modification.
"""
from __future__ import annotations
import build_v076_oc4_candidate as prior

def once(src,old,new):
    if src.count(old)!=1:
        raise ValueError("FM4.1 generated manager baseline drift")
    return src.replace(old,new,1)

def build():
    manager,nav=prior.build()
    code=manager.decode("utf-8")
    menu=nav.decode("utf-8")
    code=once(code,
        "from bob_inactivity import page as inactivity_page",
        "from bob_inactivity import page as inactivity_page\n"
        "from bob_social_memory import page as social_memory_page")
    code=once(code,
        '        elif urlsplit(self.path).path == "/investigate":',
        '        elif urlsplit(self.path).path == "/moltbook/social-memory":\n'
        '            self._send(200,social_memory_page(wrap,\n'
        '                parse_qs(urlsplit(self.path).query[:256],'
        'keep_blank_values=True,max_num_fields=4)),'
        '"text/html; charset=utf-8")\n'
        '        elif urlsplit(self.path).path == "/investigate":')
    menu=once(menu,
        '    ("/moltbook/friends", "Moltbook · Friends", "Private contacts, interests and relationship notes"),',
        '    ("/moltbook/friends", "Moltbook · Friends", "Private contacts, interests and relationship notes"),\n'
        '    ("/moltbook/social-memory", "Moltbook · Social Memory", '
        '"Source-linked private encounters and evolving interests"),')
    compile(code,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return code.encode("utf-8"),menu.encode("utf-8")

if __name__=="__main__":
    m,n=build()
    print("FM4.1 READ-ONLY SOCIAL TIMELINE: PASS")
    print("manager_bytes:",len(m),"navigation_bytes:",len(n))
