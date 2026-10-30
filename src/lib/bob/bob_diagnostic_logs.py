"""v0.7.5: bounded, authenticated, read-only diagnostic log viewer.

Combines sanitized allowlisted user-systemd journal observations, SQLite
queue states/events and worker checkpoints. This is NOT raw journal access:
third-party post text, secrets, prompts, paths and arbitrary exception strings
must never reach a browser. No process restart, shell, command input or writes.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from html import escape
from pathlib import Path
from urllib.parse import urlencode
import json
import re
import sqlite3
import subprocess

from bob_job_tracking import read_checkpoints
import bob_publish_common as common

DB=common.DB
SERVICES=("all","scout","publisher","original","original_publish","manager","gateway")
LEVELS=("all","error","warning","info")
SOURCES=("all","jobs","journal","events","checkpoints")
WINDOWS={"24h":1,"7d":7,"30d":30}
UNITS={
    "scout":("bob-moltbook-scout.service",),
    "publisher":("bob-moltbook-publisher.service",),
    "original":("bob-original-worker.service",),
    "original_publish":("bob-original-publisher.service",),
    "manager":("bob-activity-manager.service",),
    "gateway":("openclaw-gateway.service",),
}
MAX_ROWS=120
MAX_QUERY=80
MAX_JOURNAL_BYTES=320000
MAX_JOURNAL_LINES=180
RID=re.compile(r"\b[0-9]{8}T[0-9]{6}Z\b")
HEXID=re.compile(r"\b[0-9a-f]{24}\b")
HTTP=re.compile(r"\b(?:Moltbook )?HTTP (4\d\d|5\d\d)\b",re.I)
EXIT=re.compile(r"\b(?:exit(?:ed)?(?: with)?(?: status)?|status)[\s=:()]+(\d{1,3})\b",re.I)
SAFE_STATE=re.compile(r"^[a-z][a-z0-9_]{0,50}$")
SAFE_ID=re.compile(r"^(?:[0-9]{8}T[0-9]{6}Z|[0-9a-f]{24})$")
KNOWN_REASONS={
 "Integrity validation failed":"Scout draft integrity validation failed",
 "Friend-targeted draft requires manual review":"Friend-targeted reply blocked: manual approval required",
 "Human approval missing or changed":"Human approval missing or changed",
 "Human decision already exists":"An owner review decision already exists",
 "Draft expired":"Draft expired before publication",
 "Already attempted comment on this post":"Possible duplicate reply blocked",
 "Challenge expired":"Verification challenge expired",
 "Verification result unclear; do not retry":"Verification result unconfirmed; do not retry",
 "Moltbook reported unsuccessful write":"Moltbook reported an unsuccessful write; check uncertain status",
 "Moltbook credentials malformed":"Moltbook credentials were rejected (contents hidden)",
 "Credentials file permissions must be 0600":"Credentials file permissions need attention",
}
EVENTS={
 "publish_blocked":"Publication blocked by safety check",
 "publish_queued":"Manual publication queued",
 "auto_queued":"Automatic draft queued",
 "publish_attempt":"Publication attempt started",
 "publication_uncertain":"Publication outcome uncertain; do not retry blindly",
 "verification_failed":"Verification failed",
 "verification_expired":"Verification challenge expired",
 "new_replies":"New reply observation",
 "memory_ai_requested":"AI memory job requested",
 "memory_ai_generated":"AI memory proposals generated",
 "bob_friend_scout_setting":"Friend scouting setting changed",
 "bob_friend_profile_viewed":"Public friend profile inspected",
 "bob_friend_candidate_approve":"Friend candidate approved",
 "bob_friend_candidate_reject":"Friend candidate rejected",
}
CSS="""<style>
.blg{max-width:1180px;margin:auto;display:grid;gap:15px}
.blg-panel{border:1px solid #345372;background:linear-gradient(145deg,#172840,#111e31);
border-radius:14px;padding:clamp(14px,2.4vw,22px)}
.blg h2{font-size:1.16rem;margin:0 0 12px}.blg h3{font-size:1.01rem;margin:0}
.blg-muted{font-size:.86rem;color:#b9cde0;line-height:1.5}
.blg-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px}
.blg label{display:grid;gap:7px;font-weight:650;font-size:.88rem}
.blg input,.blg select{width:100%;min-height:44px;box-sizing:border-box;
border:1px solid #5a7794;background:#0d1d2e;color:#f1f6ff;
border-radius:9px;padding:10px;font:inherit}
.blg button,.blg-action{display:inline-block;min-height:44px;padding:10px 16px;
border:1px solid #85b6e5;border-radius:9px;background:#285f91;color:#fff;
font:inherit;font-weight:700;cursor:pointer;text-decoration:none}
.blg button:focus-visible,.blg input:focus-visible,.blg select:focus-visible,
.blg-action:focus-visible{outline:2px solid #9cd5ff;outline-offset:2px}
.blg-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px}
.blg-item{border:1px solid #395774;background:#102138;border-radius:10px;padding:13px;margin:10px 0}
.blg-head{display:flex;gap:9px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.blg-tag{padding:3px 8px;border-radius:9px;border:1px solid #4d6a87;
font-size:.76rem;color:#d3e2f4}
.blg-error{border-left:4px solid #da7676}.blg-warning{border-left:4px solid #e6bb6b}
.blg-info{border-left:4px solid #6eaaad}
.blg-message{margin:7px 0;line-height:1.48;white-space:pre-wrap;overflow-wrap:anywhere}
.blg-code{font-family:ui-monospace,Consolas,monospace;font-size:.83rem;color:#b9d1ed}
@media(max-width:850px){.blg-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:570px){.blg-grid{grid-template-columns:1fr}.blg button{width:100%}}
</style>"""


def e(value):
    return escape(str(value if value is not None else ""),quote=True)


def options(params):
    """Ignore unknown keys and fail closed to strict bounded UI filters."""
    def one(name,default):
        values=params.get(name,[])
        return values[0] if len(values)==1 and isinstance(values[0],str) else default
    service=one("service","all")
    level=one("level","all")
    source=one("source","all")
    span=one("window","24h")
    query=one("q","").strip()
    return dict(service=service if service in SERVICES else "all",
                level=level if level in LEVELS else "all",
                source=source if source in SOURCES else "all",
                window=span if span in WINDOWS else "24h",
                q=query[:MAX_QUERY] if len(query)<=MAX_QUERY else "")


def reason(message):
    """Only fixed safe diagnostics. Never render arbitrary stored errors."""
    if not isinstance(message,str) or not message.strip():
        return ""
    value=message.strip()
    if value in KNOWN_REASONS:
        return KNOWN_REASONS[value]
    match=HTTP.search(value[:160])
    if match:
        return "Moltbook HTTP "+match.group(1)+" response"
    if re.search(r"(?i)timeout|timed out|deadline exceeded",value[:120]):
        return "Request or model timed out; inspect local service state"
    if re.search(r"(?i)connection refused|unreachable|name resolution",value[:120]):
        return "Network or local service connection unavailable"
    if re.search(r"(?i)requires_grad|inference tensor",value[:120]):
        return "Model pipeline inference error"
    return "Detailed error withheld because it may contain private text; inspect local service journal"


def journal_message(message,unit):
    """Classify, never display arbitrary journal lines or model/private text."""
    if not isinstance(message,str) or len(message)>10000:
        return None
    text=message.strip()
    lower=text.lower()
    if text.startswith("SCOUT ERROR:"):
        summary=reason(text[len("SCOUT ERROR:"):])
        if summary.startswith("Detailed error withheld"):
            if "openclaw agent failed" in lower:
                match=EXIT.search(text)
                summary="OpenClaw Scout agent failed"+(
                    " (exit "+match.group(1)+")" if match else "")
            elif "invalid scout-seen" in lower:
                summary="Scout seen-state file failed validation"
            elif "no intact" in lower:
                summary="No intact Scout retry snapshot available"
            elif "no new" in lower:
                summary="No new Scout posts available"
            else:
                summary="Scout worker reported an error; full details withheld"
        return "error",summary
    if ("main process exited" in lower or
        "failed with result" in lower or
        "failed to start" in lower or "start request repeated too quickly" in lower):
        code=EXIT.search(text)
        return "error","Systemd service failure"+(" (exit "+code.group(1)+")" if code else "")
    if "traceback (most recent call last)" in lower:
        return "error","Python traceback recorded; raw stack output withheld"
    if ("moltbook http " in lower or "preflight failed" in lower or
        "comment send" in lower or "verification failed" in lower):
        summary=reason(text)
        return ("warning" if "preflight failed" in lower else "error"),summary
    # The publisher reports fixed-result summaries on stdout, not private
    # bodies. Only exact known substrings are allowed through.
    known=(
        ("friend-targeted auto reply blocked","Automatic friend reply blocked; manual review required","warning"),
        ("invalid draft blocked","Invalid draft blocked before publication","error"),
        ("human-reviewed auto draft blocked","Automatic draft blocked by human decision","warning"),
        ("duplicate target blocked","Duplicate publication target blocked","warning"),
        ("approval missing; job blocked","Publication blocked: human approval missing","error"),
        ("old draft blocked","Expired draft blocked","warning"),
        ("openclaw agent failed","OpenClaw agent process failed","error"),
        ("no queued publications","Publisher found no queued publication","info"),
        ("direct replies newly detected:","Publisher completed reply observation","info"),
        ("bob paused","Bob is paused","info"),
    )
    for phrase,summary,level in known:
        if phrase in lower:
            return level,summary
    return None


def _time(value):
    try:
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError,TypeError,OverflowError):
        return None


def _add(out,service,level,source,stamp,message,ident=""):
    dt=_time(stamp) if not isinstance(stamp,datetime) else stamp
    if dt is None or level not in LEVELS[1:] or service not in SERVICES[1:]:
        return
    out.append(dict(service=service,level=level,source=source,
                    when=dt,at=dt.isoformat(timespec="seconds"),
                    message=message[:350],id=ident if isinstance(ident,str) and SAFE_ID.fullmatch(ident) else ""))


def _job_rows(db,out):
    specs=(
        ("publisher","publish_jobs","run_id","state","last_error","updated_at"),
        ("original_publish","original_posts","id","state","last_error","updated_at"),
        ("original","original_requests","id","state","error","created_at"),
    )
    for service,table,id_col,state_col,error_col,time_col in specs:
        try:
            rows=db.execute(
                "SELECT "+id_col+","+state_col+","+error_col+","+time_col+
                " FROM "+table+" ORDER BY "+time_col+" DESC LIMIT 100"
            ).fetchall()
        except sqlite3.Error:
            continue
        for ident,state,error,when in rows:
            status=str(state).lower() if isinstance(state,str) else "unknown"
            if status in ("failed","verification_failed","verification_expired","rejected"):
                level="error"
            elif status in ("uncertain","waiting","awaiting_verification","verified_unconfirmed"):
                level="warning"
            else:
                level="info"
            msg=(("Comment" if service=="publisher" else "Original publication"
                  if service=="original_publish" else "Original generation")+
                 " job: "+status[:45])
            detail=reason(error)
            if detail:
                msg+=". "+detail
            _add(out,service,level,"jobs",when,msg,ident)


def _event_rows(db,out):
    try:
        rows=db.execute("SELECT at,kind,details FROM publish_events "
                        "ORDER BY id DESC LIMIT 180").fetchall()
    except sqlite3.Error:
        return
    for stamp,kind,details in rows:
        if not isinstance(kind,str) or not SAFE_STATE.fullmatch(kind):
            continue
        if kind not in EVENTS and not kind.startswith(
            ("memory_ai_","bob_friend_","auto_","publish_","verification_")):
            continue
        level=("error" if any(s in kind for s in ("failed","blocked","uncertain","expired"))
               else "warning" if "waiting" in kind else "info")
        service=("publisher" if any(s in kind for s in ("publish","auto_","verification","new_replies"))
                 else "scout" if "scout" in kind else
                 "original" if "original" in kind else "manager")
        # Event detail may contain arbitrary third-party content. Extract
        # ONLY a safe run ID. Never expose event details verbatim.
        match=RID.search(str(details)[:500]) if isinstance(details,str) else None
        ident=match.group() if match else ""
        label=EVENTS.get(kind,"Recorded event: "+kind.replace("_"," ")[:55])
        _add(out,service,level,"events",stamp,label,ident)


def _db_entries(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        return [],False
    out=[]
    try:
        with sqlite3.connect(path.absolute().as_uri()+"?mode=ro",
                             uri=True,timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            _job_rows(db,out)
            _event_rows(db,out)
        return out,True
    except (sqlite3.Error,OSError,ValueError,TypeError):
        return [],False


def _checkpoint_entries(root=None):
    out=[]
    for r in read_checkpoints(root=root):
        state=r["stage"]
        level="error" if state=="failed" else "warning" if state in (
            "unknown","waiting","uncertain","awaiting_verification") else "info"
        service={"scout":"scout","publisher":"publisher","original":"original",
                 "original_publish":"original_publish"}.get(r["worker"])
        if service:
            _add(out,service,level,"checkpoints",r["updated_at"],
                 r["message"],r["job_id"])
    return out


def _journal_entries(service,since,*,run=subprocess.run):
    # A fixed, allowlisted unit only. No shell, raw journal view, or user
    # controlled command tokens. Read-only; bounded time and result size.
    unit_map={k:v for k,v in UNITS.items()}
    keys=[service] if service!="all" else list(unit_map)
    out=[]
    ok=False
    for key in keys:
        for unit in unit_map[key]:
            args=["journalctl","--user","--unit",unit,"--since",
                  since.strftime("%Y-%m-%d %H:%M:%S UTC"),
                  "--no-pager","--output=json","--quiet","--lines",
                  str(MAX_JOURNAL_LINES)]
            try:
                result=run(args,capture_output=True,timeout=3,check=False)
                if result.returncode!=0 or len(result.stdout)>MAX_JOURNAL_BYTES:
                    continue
                ok=True
                for line in result.stdout.splitlines()[:MAX_JOURNAL_LINES]:
                    if len(line)>12000:
                        continue
                    obj=json.loads(line)
                    if not isinstance(obj,dict) or obj.get("_SYSTEMD_USER_UNIT") not in (unit,None):
                        continue
                    value=journal_message(obj.get("MESSAGE"),unit)
                    if not value:
                        continue
                    us=obj.get("__REALTIME_TIMESTAMP")
                    if not isinstance(us,str) or not us.isdecimal() or len(us)>19:
                        continue
                    dt=datetime.fromtimestamp(int(us)/1_000_000,tz=timezone.utc)
                    if dt<since:
                        continue
                    _add(out,key,value[0],"journal",dt,value[1])
            except (OSError,subprocess.TimeoutExpired,ValueError,TypeError,OverflowError):
                continue
    return out,ok


def collect(opts,*,db_path=None,checkpoint_root=None,journal_runner=None,at=None):
    at=at or datetime.now(timezone.utc)
    since=at-timedelta(days=WINDOWS[opts["window"]])
    all_rows=[]
    sources={}
    if opts["source"] in ("all","jobs","events"):
        db_rows,ok=_db_entries(DB if db_path is None else db_path)
        sources["database"]=ok
        all_rows.extend(row for row in db_rows if opts["source"]=="all" or
                        row["source"]==opts["source"])
    if opts["source"] in ("all","checkpoints"):
        all_rows+=_checkpoint_entries(checkpoint_root)
    if opts["source"] in ("all","journal"):
        rows,ok=_journal_entries(opts["service"],since,run=journal_runner or subprocess.run)
        sources["journal"]=ok
        all_rows+=rows
    filtered=[]
    q=opts["q"].casefold()
    for row in all_rows:
        if row["when"]<since or row["when"]>at+timedelta(minutes=1):
            continue
        if opts["service"]!="all" and row["service"]!=opts["service"]:
            continue
        if opts["level"]!="all" and row["level"]!=opts["level"]:
            continue
        if q and q not in (row["message"]+" "+row["id"]+" "+row["service"]+" "+row["source"]).casefold():
            continue
        filtered.append(row)
    filtered.sort(key=lambda x:(x["when"],x["source"],x["id"]),reverse=True)
    return filtered[:MAX_ROWS],len(filtered),sources


def _select(name,choices,chosen):
    return '<label>'+e(name.title())+'<select name="'+name+'">'+''.join(
        '<option value="'+e(option)+'"'+(" selected" if chosen==option else "")+
        '>'+e(option.replace("_"," ").title())+'</option>' for option in choices)+
        '</select></label>'


def page(wrap,params,*,db_path=None,checkpoint_root=None,journal_runner=None,at=None):
    opts=options(params)
    rows,count,sources=collect(opts,db_path=db_path,
                                checkpoint_root=checkpoint_root,
                                journal_runner=journal_runner,at=at)
    parts=[CSS,'<div class="blg"><section class="blg-panel"><h2>Logs & diagnostics</h2>',
           '<p class="blg-muted">Read-only observations from Bob’s queue, recent '
           'worker checkpoints, selected user-systemd services and recorded events. '
           'Journal output is classified and redacted on the server; this is '
           '<strong>not a raw log viewer</strong>. No API keys, prompts, '
           'private messages, memory text, or arbitrary exceptions are shown. '
           'Times are UTC. No action here retries or publishes anything.</p>',
           '<form method="get" action="/logs"><div class="blg-grid">',
           _select("service",SERVICES,opts["service"]),
           _select("level",LEVELS,opts["level"]),
           _select("source",SOURCES,opts["source"]),
           _select("window",WINDOWS,opts["window"]),'</div>',
           '<div class="blg-bar"><label style="flex:1 1 250px">Search safe messages / job ID'
           '<input name="q" type="search" maxlength="80" value="'+e(opts["q"])+
           '" placeholder="failed, HTTP 429, or run ID"></label>',
           '<button type="submit">Filter logs</button>',
           '<a class="blg-action" href="/logs">Clear filters</a></div></form>',
           '<p class="blg-muted">Showing '+str(len(rows))+' of '+str(count)+
           ' matched entries (maximum '+str(MAX_ROWS)+').</p>']
    if sources.get("database") is False:
        parts.append('<p class="blg-muted">Queue/event database unavailable to the read-only viewer.</p>')
    if sources.get("journal") is False:
        parts.append('<p class="blg-muted">User-systemd journal is unavailable to this service; '
                     'queue events and worker checkpoints may still help.</p>')
    parts.append('</section><section class="blg-panel"><h2>Recent entries</h2>')
    if not rows:
        parts.append('<p class="blg-muted">No entries match these filters. Try '
                     'All services, All levels and a longer time window.</p>')
    for row in rows:
        parts += ['<article class="blg-item blg-'+row["level"]+'">',
                  '<div class="blg-head"><h3>'+e(row["service"].replace("_"," ").title())+
                  '</h3><span class="blg-tag">'+e(row["level"].upper())+
                  '</span><span class="blg-tag">'+e(row["source"])+
                  '</span></div>',
                  '<p class="blg-muted">'+e(row["at"])+'</p>',
                  '<p class="blg-message">'+e(row["message"])+'</p>']
        if row["id"]:
            parts.append('<p class="blg-code">Job/run: '+e(row["id"])+'</p>')
        parts.append('</article>')
    parts += ['</section><section class="blg-panel"><h2>Understanding failures</h2>',
              '<p class="blg-muted">A failed background checkpoint is not always '
              'a failed Moltbook publication. Look for a matching job ID and '
              'database failure reason. For an uncertain send, do NOT retry '
              'blindly: the platform may have accepted it. Entries without '
              'a stored safe diagnostic deliberately omit raw personal or '
              'third-party text.</p></section></div>']
    return wrap("Logs & diagnostics","".join(parts),"/logs")
