#!/usr/bin/env python3
"""OC2: add one authenticated Automation GET page to accepted FM3 manager.

All POST, auth, CSRF, Host/Origin and publication methods are byte-identical
to the final FM3.2d candidate. Toggle forms submit to pre-existing handlers.
"""
from __future__ import annotations
import build_v075_fm32d_candidate as prior


def once(text,old,new):
    if text.count(old)!=1:
        raise ValueError("OC2 manager baseline drift: refusing release build")
    return text.replace(old,new,1)


def build():
    original,navigation=prior.build()
    code=original.decode("utf-8")
    menu=navigation.decode("utf-8")
    code=once(code,
      "from bob_diagnostic_logs import page as diagnostics_page",
      "from bob_diagnostic_logs import page as diagnostics_page\n"
      "from bob_automation_center import page as automation_page")
    code=once(code,
      '        elif urlsplit(self.path).path == "/logs":',
      '        elif urlsplit(self.path).path == "/automation":\n'
      '            self._send(200,automation_page(TOKEN,wrap,\n'
      '                parse_qs(urlsplit(self.path).query[:128],keep_blank_values=True)),\n'
      '                "text/html; charset=utf-8")\n'
      '        elif urlsplit(self.path).path == "/logs":')
    menu=once(menu,
      '    ("/", "Overview", "Live overview"),',
      '    ("/", "Overview", "Live overview"),\n'
      '    ("/automation", "Automation", "Automation controls, actual runs and schedules"),')
    compile(code,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return code.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    manager,nav=build()
    print("OC2 AUTOMATION CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
