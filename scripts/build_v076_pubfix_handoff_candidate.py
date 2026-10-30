#!/usr/bin/env python3
"""Safe publication handoff: add a guarded owner-action to existing manager UI.

Pinned OC3-generated manager only. The POST endpoint, Host/Origin/CSRF rules
and all HTTP handlers stay unchanged; queue_manual owns transition policy.
"""
from __future__ import annotations
import build_v076_oc3_candidate as prior

def once(code,old,new):
    if code.count(old)!=1:
        raise ValueError("publication handoff baseline drift: refusing release build")
    return code.replace(old,new,1)

def build():
    original,nav=prior.build()
    code=original.decode("utf-8")
    code=once(code,
      "queue_manual, now as utc_now",
      "queue_manual, manual_recovery_allowed, now as utc_now")
    code=once(code,
      "        recent_replies = pdb.execute('SELECT author,content,detected_at "
      "FROM published_replies ORDER BY detected_at DESC LIMIT 15').fetchall()",
      "        recoverable = {r['run_id'] for r in records if "
      "r['verified_draft'] and manual_recovery_allowed(pdb,r['run_id'])}\n"
      "        recent_replies = pdb.execute('SELECT author,content,detected_at "
      "FROM published_replies ORDER BY detected_at DESC LIMIT 15').fetchall()")
    code=once(code,
      "        cards.append(f'''<article class=\"card\" id=\"run-{esc(stamp)}\">",
      "        if job and status=='approved' and stamp in recoverable:\n"
      "            publication_html += (\n"
      "              f'<form method=\"post\" action=\"/publish/{stamp}\">'\n"
      "              f'<input type=\"hidden\" name=\"csrf\" value=\"{esc(TOKEN)}\">'\n"
      "              f'<input type=\"hidden\" name=\"digest\" value=\"{esc(r[\"approval_sha256\"])}\">'\n"
      "              '<button type=\"submit\">Queue approved draft manually</button></form>'\n"
      "              '<p class=\"meta\">Automatic publication was stopped before sending. '\n"
      "              'Only this explicit owner action converts it to the manual queue. '\n"
      "              'No automatic retry of a possibly sent comment.</p>')\n"
      "        cards.append(f'''<article class=\"card\" id=\"run-{esc(stamp)}\">")
    compile(code,"bob-activity-manager","exec")
    return code.encode("utf-8"),nav

if __name__=="__main__":
    manager,nav=build()
    print("OWNER APPROVAL TO MANUAL QUEUE RELEASE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("live_services_modified: NO")
