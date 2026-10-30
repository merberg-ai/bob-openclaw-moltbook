#!/usr/bin/env python3
"""OC4 adds a read-only investigation route and navigation to pubfix manager.

No existing authentication, CSRF, publishing, timer or POST behavior changes.
"""
from __future__ import annotations
import build_v076_pubfix_handoff_candidate as prior

def once(src,old,new):
    if src.count(old)!=1:
        raise ValueError("OC4 manager drift; refuse release build")
    return src.replace(old,new,1)

def build():
    code,nav=prior.build()
    code=code.decode("utf-8")
    nav=nav.decode("utf-8")
    code=once(code,
        "from bob_automation_center import page as automation_page",
        "from bob_automation_center import page as automation_page\n"
        "from bob_inactivity import page as inactivity_page")
    code=once(code,
        '        elif urlsplit(self.path).path == "/automation":',
        '        elif urlsplit(self.path).path == "/investigate":\n'
        '            self._send(200,inactivity_page(wrap),"text/html; charset=utf-8")\n'
        '        elif urlsplit(self.path).path == "/automation":')
    nav=once(nav,
        '    ("/automation", "Automation", "Automation controls, actual runs and schedules"),',
        '    ("/automation", "Automation", "Automation controls, actual runs and schedules"),\n'
        '    ("/investigate", "Why no activity?", "Evidence-backed queue, Scout and publisher diagnostics"),')
    compile(code,"bob-activity-manager","exec")
    compile(nav,"navigation_shell.py","exec")
    return code.encode("utf-8"),nav.encode("utf-8")

if __name__=="__main__":
    a,b=build()
    print("OC4 READ-ONLY INVESTIGATOR: PASS")
    print("manager_bytes",len(a),"nav_bytes",len(b))
