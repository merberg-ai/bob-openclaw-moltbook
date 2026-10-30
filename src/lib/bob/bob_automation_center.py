"""OC2: compact, authenticated Automation inventory with existing safe controls.

No systemd mutation, new automation scheduler, new publication authority,
credentials, session content, or browser shell. Read-only observed statuses
come from the OC0 snapshot and private SQLite read-only summaries.
"""
from __future__ import annotations
from html import escape
from pathlib import Path
import sqlite3

from bob_overview import DB, snapshot as overview_snapshot
from bob_friend_scout import CONFIRM as FRIEND_CONFIRM

VIEWS=("all","posting","discovery","system")
GROUPS={"posting":"Posting & replies","discovery":"Scout & social discovery",
        "system":"Agent & dependencies"}
SAFE_STATES=frozenset(("running","ready","listening","idle","inactive","failed",
                        "unknown","unavailable","model_missing","active","waiting",
                        "blocked","paused","completed","queued"))
STYLE="""<style>
.oca{max-width:1100px;margin:auto;display:grid;gap:12px}
.oca p{line-height:1.45}
.oca-muted{font-size:.79rem;color:#abc0d7}
.oca-nav{display:flex;gap:7px;flex-wrap:wrap}
.oca-nav a{border:1px solid #446486;border-radius:9px;padding:8px 11px;
color:#d7eafa;text-decoration:none;font-size:.81rem}
.oca-nav a[aria-current=page]{background:#275b87;color:#fff}
.oca-group{background:linear-gradient(145deg,#152b43,#0e1d31);
border:1px solid #344f70;border-radius:14px;padding:clamp(11px,2vw,18px)}
.oca-group h2{font-size:1.1rem;margin:0 0 9px}
.oca-list{display:grid;gap:7px}
.oca-item{background:#102137;border:1px solid #2d4868;border-radius:11px;
padding:10px 12px;min-width:0}
.oca-main{display:flex;gap:10px;align-items:flex-start;justify-content:space-between}
.oca-title{font-weight:700;font-size:.9rem;overflow-wrap:anywhere}
.oca-sub{font-size:.77rem;color:#a6bed6;margin:3px 0 0}
.oca-pill{font-size:.73rem;font-weight:700;white-space:nowrap;border-radius:999px;
padding:4px 8px;background:#2b3d52;color:#d5e4f6}
.oca-pill[data-tone=on]{background:#19473d;color:#b4f2df}
.oca-pill[data-tone=off]{background:#433924;color:#f0d29c}
.oca-pill[data-tone=error]{background:#4b2731;color:#ffc5d2}
.oca-pill[data-tone=active]{background:#173d60;color:#b6e6ff}
.oca-item details{margin-top:5px}
.oca-item summary{cursor:pointer;color:#b8d8f5;font-size:.76rem;min-height:28px}
.oca-extra{padding-top:7px;border-top:1px solid #2a415e;display:grid;gap:5px}
.oca-extra p{margin:0;font-size:.8rem;color:#c0d0e1;overflow-wrap:anywhere}
.oca-extra a{font-size:.81rem}
.oca-action{display:grid;gap:8px;max-width:480px;margin-top:4px;padding:10px;
border:1px solid #365578;border-radius:9px}
.oca-action label{display:grid;gap:5px;font-size:.82rem}
.oca-action input{width:100%;max-width:100%;box-sizing:border-box;min-height:43px;
border:1px solid #547897;background:#091a2d;color:#fff;border-radius:8px;padding:8px;font:inherit}
.oca-action button{min-height:44px;background:#285d90;border:1px solid #83b4e5;
color:white;border-radius:8px;padding:8px 14px;font:inherit;font-weight:700}
.oca-action button.danger{background:#4e3948}
.oca :is(button,a,input,summary):focus-visible{outline:2px solid #f1c77c;outline-offset:2px}
@media(max-width:470px){.oca-nav a{flex:1 1 auto;text-align:center}
.oca-item{padding:9px}.oca-main{gap:7px}.oca-pill{font-size:.69rem}
.oca-action button{width:100%}}
</style>"""

def e(value):
    return escape(str(value if value is not None else ""),quote=True)

def _db_data(path=DB):
    """Fixed schema/queries, bounded rows, no mutations, no raw content."""
    data={"available":False,"auto":None,"friends":None,"events":{},
          "comment":None,"auto_comment":None,"original":None,
          "draft":None,"focus":None,"interest":None}
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        return data
    try:
        with sqlite3.connect(path.absolute().as_uri()+"?mode=ro",uri=True,timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            data["available"]=True
            rows=db.execute("SELECT name,value FROM publish_settings WHERE name IN "
                            "('auto_enabled','bob_friend_scout_enabled')").fetchall()
            settings=dict(rows)
            for key,setting in (("auto","auto_enabled"),
                                ("friends","bob_friend_scout_enabled")):
                value=settings.get(setting,"0")
                data[key]=value=="1" if value in ("0","1") else None
            events=db.execute("SELECT at,kind FROM publish_events "
                              "ORDER BY id DESC LIMIT 200").fetchall()
            for stamp,kind in events:
                if kind in ("auto_enabled","auto_disabled",
                            "bob_friend_scout_setting","new_replies"):
                    data["events"].setdefault(kind,str(stamp)[:40])
            def existing(table):
                return bool(db.execute("SELECT 1 FROM sqlite_master WHERE "
                                       "type='table' AND name=?",(table,)).fetchone())
            jobs=(
                ("comment","publish_jobs","state","updated_at",""),
                ("auto_comment","publish_jobs","state","updated_at",
                 " WHERE mode='auto'"),
                ("original","original_posts","state","updated_at",""),
                ("draft","original_requests","state","created_at",""),
                ("focus","bob_friend_focus_jobs","status","updated_at",""),
                ("interest","bob_friend_ai_jobs","status","updated_at",""),
            )
            for key,table,state,when,where in jobs:
                if existing(table):
                    row=db.execute("SELECT "+state+","+when+" FROM "+table+
                                   where+" ORDER BY "+when+" DESC LIMIT 1").fetchone()
                    if row:
                        data[key]={"state":str(row[0])[:32],"at":str(row[1])[:40]}
    except (sqlite3.Error,OSError,TypeError,ValueError):
        return {**data,"available":False,"auto":None,"friends":None,
                "events":{},"comment":None,"auto_comment":None,
                "original":None,"draft":None,"focus":None,"interest":None}
    return data

def inventory(observed,local):
    """One registry; mode and permission never inferred from service health."""
    services={x.get("name"):x.get("state") for x in observed.get("services",[])
              if isinstance(x,dict)}
    workers={x.get("worker"):x for x in observed.get("workers",[])
             if isinstance(x,dict)}
    metrics=observed.get("metrics") or {}
    queues=metrics.get("queues") or {}
    lanes={x.get("key"):x for x in (observed.get("operations") or {}).get("lanes",[])
           if isinstance(x,dict)}
    global_paused=observed.get("paused") is True
    def last(key,checkpoint_key=None,event=None):
        row=local.get(key)
        if row:
            return str(row["state"])+" · "+str(row["at"])
        ck=workers.get(checkpoint_key or key)
        if ck and ck.get("updated_at"):
            return "Checkpoint "+str(ck.get("stage","unknown"))+" · "+str(ck["updated_at"])
        if event and local.get("events",{}).get(event):
            return "Setting changed · "+str(local["events"][event])
        return "No recorded action"
    def unit(name):
        return str(services.get(name) or "unknown")
    def next_run(key):
        return str(lanes.get(key,{}).get("next_scheduled") or "Not reported")
    def item(category,key,title,mode,setting,state,summary,history,scheduled,href):
        return dict(category=category,key=key,title=title,mode=mode,
                    setting=setting,state=state,summary=summary,
                    history=history,scheduled=scheduled,href=href)
    # Display state is effective runtime/permission, not just the saved toggle.
    if local["auto"] is None: auto="unknown"
    elif not local["auto"]: auto="off"
    elif global_paused: auto="paused"
    else: auto="on"
    if local["friends"] is None: friends="unknown"
    elif not local["friends"]: friends="off"
    elif global_paused: friends="paused"
    else: friends="on"
    rows=[
      item("posting","auto","Automatic comments","Owner opt-in",
           "Enabled" if local["auto"] else "Disabled" if local["auto"] is False else "Unknown",
           auto,"New eligible global Scout drafts only; manual replies have priority.",
           last("auto_comment",event="auto_enabled"),next_run("publisher"),"/scout"),
      item("posting","publisher","Publisher timer","Scheduled worker","Systemd-managed",
           unit("Publisher timer"),"Processes approved/eligible comments; never guarantees publication.",
           last("comment","publisher"),next_run("publisher"),"/logs?service=publisher"),
      item("posting","reply","Reply observation","Within publisher timer","No separate toggle",
           unit("Publisher timer"),"Checks for replies during publisher runs; not its own scheduler.",
           "Last reply event: "+str(local.get("events",{}).get("new_replies") or "Not recorded"),
           next_run("publisher"),"/activity"),
      item("posting","original","Original post drafts","Manual request","No automation",
           "manual","Draft, review, approve, then explicitly queue publication.",
           last("original","original_publish"),"Not scheduled by this setting","/originals"),
      item("posting","draft","Original draft worker","On-demand worker","No automation",
           "manual","Runs only if an original draft was requested.",
           last("draft","original"),"Not reported","/originals"),
      item("discovery","scout","Scout timer","Scheduled worker","Systemd-managed",
           unit("Scout timer"),"Collects bounded public discussions for Bob to review.",
           last("scout","scout"),next_run("scout"),"/logs?service=scout"),
      item("discovery","friends","Friend-focused Scout","Owner opt-in",
           "Enabled" if local["friends"] else "Disabled" if local["friends"] is False else "Unknown",
           friends,"Adds at most two watched active friends to an existing Scout run.",
           last("none",event="bob_friend_scout_setting"),next_run("scout"),
           "/moltbook/friend-scout"),
      item("discovery","focus","Manual friend inspection","On-demand, confirmed",
           "No automatic timer","manual","One public profile and at most two posts per confirmed request.",
           last("focus"),"Not scheduled","/moltbook/friend-scout"),
      item("discovery","interest","Local tentative interests","On-demand Ollama",
           "No automatic timer","manual","Owner requests local model ideas, then separately reviews them.",
           last("interest"),"Not scheduled","/moltbook/friend-scout"),
      item("system","gateway","OpenClaw Gateway","Service","Systemd-managed",
           unit("Gateway"),"Process state does not prove agent activity.",
           "Status at "+str(observed.get("checked_at") or "unknown"),
           "Service, not a scheduled task","/system/status"),
      item("system","ollama","Local Ollama","Dependency","Readiness probe",
           unit("Ollama"),"Model availability does not prove generation is running.",
           "Status at "+str(observed.get("checked_at") or "unknown"),
           "On demand","/system/status")
    ]
    if global_paused:
        for row in rows:
            if row["key"] in ("auto","friends"):
                row["summary"]="Global Bob pause overrides this setting. "+row["summary"]
    return rows

def _toggle(key,enabled,csrf):
    if key=="auto":
        if enabled is None:
            return ""
        endpoint="/autopost/disable" if enabled else "/autopost/enable"
        parts=['<form class="oca-action" method="post" action="'+endpoint+'">',
               '<input type="hidden" name="csrf" value="'+e(csrf)+'">']
        if not enabled:
            parts += ['<label>Type ENABLE AUTO to enable<input name="confirmation" '
                      'maxlength="24" autocomplete="off" required></label>',
                      '<p class="oca-muted">Only future eligible non-friend Scout drafts may auto-queue.</p>']
        else:
            parts.append('<p class="oca-muted">Disabling also cancels queued '
                         'automatic comments, but never manual jobs.</p>')
        parts.append('<button type="submit"'+(' class="danger"' if enabled else '')+'>'+
                     ('Disable automatic comments' if enabled else 'Enable automatic comments')+
                     '</button></form>')
        return "".join(parts)
    if key=="friends":
        if enabled is None:
            return ""
        parts=['<form class="oca-action" method="post" action="/moltbook/friend-scout">',
               '<input type="hidden" name="csrf" value="'+e(csrf)+'">',
               '<input type="hidden" name="expected" value="'+("1" if enabled else "0")+'">',
               '<input type="hidden" name="enabled" value="'+("0" if enabled else "1")+'">']
        if enabled:
            parts.append('<input type="hidden" name="confirmation" value="">')
        else:
            parts.append('<label>Type '+FRIEND_CONFIRM+
                         ' to enable<input name="confirmation" autocomplete="off" '
                         'maxlength="40" required></label>')
        parts.append('<button type="submit"'+(' class="danger"' if enabled else '')+'>'+
                     ('Disable friend-focused scouting' if enabled else
                      'Enable friend-focused scouting')+'</button></form>')
        return "".join(parts)
    return ""

def _safe_state(state):
    return state if state in SAFE_STATES or state in ("on","off","manual","paused") else "unknown"

def page(csrf,wrap,params=None,*,observed=None,local=None):
    """Only authenticated manager GET can reach; existing POST handlers own writes."""
    opts=params or {}
    requested=opts.get("view",["all"])
    view=requested[0] if isinstance(requested,list) and len(requested)==1 and requested[0] in VIEWS else "all"
    observed=observed if observed is not None else overview_snapshot()
    local=local if local is not None else _db_data()
    rows=inventory(observed,local)
    parts=[STYLE,'<div class="oca"><div class="oca-group">',
           '<h2>Automation Center</h2>',
           '<p class="oca-muted">The setting, worker health and next scheduled '
           'trigger are separate facts. Read-only service state is not proof of '
           'a completed run. Manual tasks do not gain automatic permissions.</p>',
           '<nav class="oca-nav" aria-label="Automation categories">']
    for slug,label in (("all","All"),("posting","Posting"),
                       ("discovery","Discovery"),("system","System")):
        parts.append('<a href="/automation'+("?view="+slug if slug!="all" else "")+
                     '"'+(' aria-current="page"' if slug==view else '')+
                     '>'+e(label)+'</a>')
    parts += ['</nav><p class="oca-muted">Observed at '+
              e(observed.get("checked_at") or "unknown")+
              ' · <a href="/automation">Refresh</a> · <a href="/logs">Logs</a></p>',
              '</div>']
    if not local.get("available"):
        parts.append('<p class="oca-muted">Private queue/settings database unavailable. '
                     'Saved toggle state is unknown; actions are hidden.</p>')
    if observed.get("paused"):
        parts.append('<p class="oca-muted">Global Bob pause is active and overrides '
                     'enabled automation settings. This page cannot bypass it.</p>')
    for category,title in GROUPS.items():
        if view not in ("all",category):
            continue
        parts += ['<section class="oca-group"><h2>'+e(title)+'</h2>',
                  '<div class="oca-list">']
        for item in rows:
            if item["category"]!=category:
                continue
            state=_safe_state(item["state"])
            tone=("on" if state in ("running","on","ready","listening") else
                  "error" if state in ("failed","unavailable","model_missing") else
                  "active" if state=="active" else "off" if state in ("off","inactive","paused")
                  else "quiet")
            parts += ['<article class="oca-item"><div class="oca-main"><div>',
                      '<div class="oca-title">'+e(item["title"])+'</div>',
                      '<p class="oca-sub">'+e(item["mode"])+' · '+
                      e(item["setting"])+'</p></div>',
                      '<span class="oca-pill" data-tone="'+tone+'">'+e(state)+'</span>',
                      '</div><details><summary>Details &amp; controls</summary>',
                      '<div class="oca-extra"><p>'+e(item["summary"])+'</p>',
                      '<p>Last known: '+e(item["history"])+'</p>',
                      '<p>Next systemd run: '+e(item["scheduled"])+'</p>',
                      '<a href="'+e(item["href"])+'">Open related section</a>']
            if item["key"] in ("auto","friends") and local.get("available"):
                parts.append(_toggle(item["key"],local.get(item["key"]),csrf))
            parts.append('</div></details></article>')
        parts.append('</div></section>')
    parts += ['<p class="oca-muted">No service/timer enable, restart, manual '
              'publication or shell commands exist here. Existing safety and '
              'owner-approval checks still apply.</p></div>']
    return wrap("Automation","".join(parts),"/automation")
