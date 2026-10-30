#!/usr/bin/env python3
"""OC3: authenticated read-only Console GET + sanitized JSON/text and JS.

Pinned to OC2 generated manager; POST/auth/origin/CSRF/publisher code unchanged.
No command routes, write actions, extra ports or unvetted journal access.
"""
from __future__ import annotations
import build_v076_oc2_candidate as prior


def once(code,old,new):
    if code.count(old)!=1:
        raise ValueError("OC3 manager baseline drift: refusing update")
    return code.replace(old,new,1)


def build():
    original,navigation=prior.build()
    code=original.decode("utf-8")
    menu=navigation.decode("utf-8")
    code=once(code,
      "from bob_automation_center import page as automation_page",
      "from bob_automation_center import page as automation_page\n"
      "from bob_diagnostic_console import (page as console_page, "
      "options as console_options, collect as console_collect, "
      "javascript as console_js, export_text as console_export)")
    code=once(code,
      '        elif urlsplit(self.path).path == "/automation":',
      '''        elif urlsplit(self.path).path == "/console":
            self._send(200,console_page(wrap,
                parse_qs(urlsplit(self.path).query[:256],keep_blank_values=True,
                         max_num_fields=7)), "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/api/dashboard/console":
            query=parse_qs(urlsplit(self.path).query[:256],keep_blank_values=True,
                           max_num_fields=7)
            data=console_collect(console_options(query))
            if query.get("format")==["text"]:
                self._send(200,console_export(data),"text/plain; charset=utf-8")
            else:
                self._send(200,json.dumps(data),"application/json")
        elif self.path == "/assets/bob-console.js":
            self._send(200,console_js(),"application/javascript; charset=utf-8")
        elif urlsplit(self.path).path == "/automation":''')
    # Only the console page gets same-origin script & fetch; default remains
    # script-disabled on other non-script routes.
    old='if urlsplit(self.path).path in ("/system/status", "/", "/mind/personality")'
    new='if urlsplit(self.path).path in ("/system/status", "/", "/mind/personality", "/console")'
    code=once(code,old,new)
    menu=once(menu,
      '    ("/automation", "Automation", "Automation controls, actual runs and schedules"),',
      '    ("/automation", "Automation", "Automation controls, actual runs and schedules"),\n'
      '    ("/console", "Console", "Sanitized diagnostic stream from Bob workers and local services"),')
    compile(code,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return code.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    manager,nav=build()
    print("OC3 SAFE CONSOLE CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
