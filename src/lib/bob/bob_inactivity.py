"""OC4: read-only, evidence-grounded "Why no activity?" investigator.

No Moltbook network calls, no new worker execution, no shell, no hidden
publication, no raw drafts or arbitrary stored error text. Fixed bounded
queries against existing private publication SQLite DB. A saved decision is
not necessarily a successful post, and a queued job is not an active worker.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from html import escape
from pathlib import Path
import re
import sqlite3

from bob_overview import snapshot as overview_snapshot
from bob_publish_common import DB, manual_recovery_allowed

SOURCE_LANES=("publisher","scout","original","dependencies")
RUN=re.compile(r"\d{8}T\d{6}Z\Z")
SKIP=re.compile(r"code=([A-Z_]{3,36})(?: run=(\d{8}T\d{6}Z))?\Z")
SKIP_CODES={
    "NO_QUEUE": "Publisher found no queued comment",
    "AUTO_DISABLED": "Automatic comments are disabled",
    "RATE_OR_BUDGET": "Publisher was held by a rate or daily-budget policy",
    "GLOBAL_PAUSE": "Global pause prevented comment publication",
    "PREFLIGHT_FAILED": "Public-target preflight did not complete",
    "MANUAL_APPROVAL_CHANGED": "Manual approval was missing or had changed",
    "AUTO_REVIEW_BLOCKED": "Automatic comment was blocked by an existing owner decision",
    "FRIEND_PROTECTED": "Automatic friend-targeted comment was blocked",
    "INTEGRITY_BLOCKED": "Saved draft failed integrity checks",
    "DRAFT_EXPIRED": "Saved comment draft expired",
    "DUPLICATE": "A previous publication attempt exists for that target",
    "STALE_CLAIM": "Publisher discarded a stale job or owner decision",
}
REVIEW_BLOCK=frozenset(("Human decision already exists",
                        "Friend-targeted draft requires manual review"))
MAX_JOBS=150
MAX_EVENTS=80
MAX_BLOCKS=3
MAX_HANDOFF_CHECKS=25
MAX_LINKS=3
CSS="""<style>
.bi{max-width:1090px;margin:auto;display:grid;gap:12px}
.bi-panel{background:linear-gradient(145deg,#162b43,#0e1b2e);border:1px solid #365575;
border-radius:14px;padding:clamp(12px,2vw,19px);min-width:0}
.bi h2{font-size:1.12rem;margin:0 0 7px}
.bi-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.bi-card{background:#102139;border:1px solid #2c4b6b;border-radius:11px;padding:12px;min-width:0}
.bi-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.bi-head strong{font-size:.95rem}
.bi-pill{border-radius:99px;background:#263b51;color:#e1edfb;font-size:.75rem;
font-weight:700;padding:4px 8px;white-space:nowrap}
.bi-pill[data-state=blocked]{background:#512e32;color:#ffe2df}
.bi-pill[data-state=waiting]{background:#514122;color:#f7dc9a}
.bi-pill[data-state=idle]{background:#214a41;color:#b7efdf}
.bi-pill[data-state=unknown]{background:#334253;color:#e0e8f2}
.bi-muted{color:#aac2dc;font-size:.8rem;line-height:1.5;overflow-wrap:anywhere}
.bi-line{font-size:.84rem;line-height:1.48;margin:9px 0;overflow-wrap:anywhere}
.bi-reasons{display:grid;gap:7px;margin-top:11px}
.bi-reason{padding:9px;border-radius:9px;border:1px solid #365572;background:#11273e}
.bi-reason b{font-size:.78rem;display:block}
.bi-reason p{margin:3px 0 0;font-size:.79rem;line-height:1.45}
.bi-code{font-size:.7rem;color:#8fb0cd;font-family:ui-monospace,Consolas,monospace}
.bi a{color:#a6d9ff;font-size:.8rem}
.bi-links{display:flex;flex-wrap:wrap;gap:13px}
.bi details summary{cursor:pointer;min-height:29px;color:#bad8f2;font-size:.8rem}
.bi :is(a,summary):focus-visible{outline:2px solid #f5cb86;outline-offset:2px}
@media(max-width:700px){.bi-grid{grid-template-columns:1fr}.bi-card{padding:10px}}
</style>"""

def e(value):
    return escape(str(value if value is not None else ""),quote=True)

def _date(s):
    try:
        t=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return t.astimezone(timezone.utc) if t.tzinfo else None
    except (ValueError,OverflowError,TypeError,AttributeError):
        return None

def _source(when):
    stamp=_date(when)
    return stamp.isoformat(timespec="seconds") if stamp else "Policy / historical summary"

def _reason(code,title,detail,source="",href="/logs"):
    return dict(code=code,title=title,detail=detail,source=_source(source),href=href)

def _blank():
    return {"available":False,"comments":[],"events":[],"last_attempt":"",
            "last_success":"","last_outcome":"","last_skip":None,
            "reviewed":{"approved":0,"rejected":0,"unknown":0},
            "queue":{"manual":0,"auto":0},
            "approved_blocked":0,"rejected_blocked":0,"undecided_blocked":0,
            "sent_or_uncertain":0,"oldest_manual":"","oldest_auto":"",
            "job_window":{"oldest":"","newest":"","inspected":0},
            "latest_review_block":{"approved":"","rejected":"","unknown":""},
            "manual_handoff":{"checked":0,"verified":0,"run_ids":[]}}

def read_private(path=DB,*,at=None):
    """Read-only bounded evidence. Never select arbitrary error or draft text."""
    out=_blank()
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        return out
    try:
        with sqlite3.connect(path.absolute().as_uri()+"?mode=ro",
                             uri=True,timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            # Inspect only known enums and hash equality. No raw text is
            # returned to a dashboard/API response.
            rows=db.execute(
                "SELECT j.run_id,j.mode,j.state,j.last_error,j.created_at,"
                "j.updated_at,j.attempted_at,j.comment_id,j.approval_sha256,"
                "j.challenge_code,j.challenge_text,j.challenge_expires_at,"
                "j.verify_answer,d.status,d.draft_sha256 "
                "FROM publish_jobs j LEFT JOIN decisions d ON d.run_id=j.run_id "
                "ORDER BY j.updated_at DESC LIMIT ?",(MAX_JOBS,)).fetchall()
            out["available"]=True
            out["job_window"]["inspected"]=len(rows)
            for (rid,mode,state,error,created,updated,attempted,comment,digest,
                 challenge_code,challenge_text,challenge_expiry,verify_answer,
                 decision,decision_hash) in rows:
                if mode not in ("auto","manual") or not isinstance(state,str):
                    continue
                updated_time=_date(updated)
                if updated_time:
                    period=out["job_window"]
                    for field,earliest in (("oldest",True),("newest",False)):
                        previous=_date(period[field])
                        if previous is None or (updated_time<previous if earliest
                                                   else updated_time>previous):
                            period[field]=updated_time.isoformat(timespec="seconds")
                if state=="queued":
                    out["queue"][mode]+=1
                    key="oldest_"+mode
                    when=_date(created)
                    previous=_date(out[key])
                    if when and (previous is None or when<previous):
                        out[key]=when.isoformat(timespec="seconds")
                if attempted:
                    when=_date(attempted)
                    prev=_date(out["last_attempt"])
                    if when and (prev is None or when>prev):
                        out["last_attempt"]=when.isoformat(timespec="seconds")
                if state=="published" and isinstance(comment,str) and comment:
                    when=_date(updated)
                    prev=_date(out["last_success"])
                    if when and (prev is None or when>prev):
                        out["last_success"]=when.isoformat(timespec="seconds")
                if state in ("uncertain","sending","published","awaiting_verification",
                             "verification_failed","verification_expired","verifying",
                             "verified_unconfirmed"):
                    out["sent_or_uncertain"]+=1
                untouched=all(v is None for v in (
                    attempted,comment,challenge_code,challenge_text,
                    challenge_expiry,verify_answer))
                if mode=="auto" and state=="failed" and error in REVIEW_BLOCK and untouched:
                    classification=("approved" if decision=="approved" and decision_hash==digest
                                    else "rejected" if decision=="rejected" and decision_hash==digest
                                    else "unknown")
                    if classification=="approved":
                        out["approved_blocked"]+=1
                        # No unchecked assumption that a historic DB row is
                        # still source-verified or actionable. The same vetted
                        # helper backs the existing owner Publish button.
                        handoff=out["manual_handoff"]
                        if handoff["checked"]<MAX_HANDOFF_CHECKS and RUN.fullmatch(str(rid)):
                            handoff["checked"]+=1
                            try:
                                if manual_recovery_allowed(db,rid):
                                    handoff["verified"]+=1
                                    if len(handoff["run_ids"])<MAX_LINKS:
                                        handoff["run_ids"].append(rid)
                            except (sqlite3.Error,OSError,TypeError,ValueError):
                                pass
                    elif classification=="rejected":
                        out["rejected_blocked"]+=1
                    else:
                        out["undecided_blocked"]+=1
                    prior=_date(out["latest_review_block"][classification])
                    if updated_time and (prior is None or updated_time>prior):
                        out["latest_review_block"][classification]=updated_time.isoformat(timespec="seconds")
                if mode=="auto" and state=="queued" and decision in ("approved","rejected") and decision_hash==digest:
                    out["reviewed"][decision]+=1
            events=db.execute(
                "SELECT at,details FROM publish_events WHERE kind='publisher_skip' "
                "ORDER BY id DESC LIMIT ?",(MAX_EVENTS,)).fetchall()
            now=at or datetime.now(timezone.utc)
            now=now.astimezone(timezone.utc)
            for stamp,details in events:
                match=SKIP.fullmatch(details) if isinstance(details,str) else None
                dt=_date(stamp)
                if not match or match[1] not in SKIP_CODES or not dt:
                    continue
                if dt>now+timedelta(minutes=1) or now-dt>timedelta(days=7):
                    continue
                if out["last_skip"] is None:
                    out["last_skip"]={"code":match[1],"at":dt.isoformat(timespec="seconds"),
                                     "run_id":match[2] or ""}
                    break
    except (sqlite3.Error,OSError,ValueError,TypeError):
        return _blank()
    return out

def _lane(observed,key):
    return next((v for v in (observed.get("operations") or {}).get("lanes",[])
                 if isinstance(v,dict) and v.get("key")==key),{})

def explain(observed,history,*,at=None):
    """Deterministic one-screen explanation with uncertainty and evidence types."""
    now=at or datetime.now(timezone.utc)
    metrics=observed.get("metrics") or {}
    usage=metrics.get("usage") or {}
    limits=metrics.get("limits") or {}
    q=metrics.get("queues") or {}
    available=history.get("available") and metrics.get("available") is True
    paused=observed.get("paused") is True
    def safe_num(d,key):
        v=d.get(key)
        return v if type(v)==int and v>=0 else None
    count=safe_num(q,"comments_queued")
    manual=safe_num(q,"manual_queued")
    auto=safe_num(q,"auto_queued")
    scout=_lane(observed,"scout")
    publisher=_lane(observed,"publisher")
    original=_lane(observed,"original")
    lines=[]
    def section(key,title,lane,summary,items,href):
        return {"key":key,"title":title,"state":lane.get("state","unknown"),
                "summary":summary,"reasons":items[:MAX_BLOCKS],"href":href}
    # Manual queue / actual delivery.
    reasons=[]
    if paused:
        reasons.append(_reason("GLOBAL_PAUSE","Global pause","Publisher is paused; queued work is not being sent.","","/system/status"))
    if publisher.get("code")=="TIMER_DOWN":
        reasons.append(_reason("TIMER_DOWN","Publisher timer inactive",
                              "The timer must run before any queued job can be evaluated.","","/system/status"))
    if publisher.get("code")=="RATE_LIMIT":
        reasons.append(_reason("RATE_LIMIT","Policy eligibility, not a scheduled run",
                    "Earliest permitted comment time is not the systemd timer's next trigger.",
                    "", "/settings/activity-limits"))
    if available and manual and manual>0:
        reasons.append(_reason("MANUAL_BACKLOG",f"{manual} manually queued",
            "Manual comments have priority; queued does not mean sending. Inspect last worker activity and policy.",
            history.get("oldest_manual",""),"/manage"))
    if history.get("last_skip"):
        skip=history["last_skip"]
        age=(now-_date(skip["at"])).total_seconds() if _date(skip["at"]) else 999999
        if 0<=age<86400:
            reasons.append(_reason(skip["code"],"Last recorded publisher skip",
                SKIP_CODES[skip["code"]],skip["at"],"/console?service=publisher"))
    if not available:
        reasons.append(_reason("EVIDENCE_UNAVAILABLE","Publication evidence missing",
                     "Source data cannot establish a specific blocker.","","/logs?service=publisher"))
    if not reasons:
        reasons.append(_reason("NOT_CONFIRMED","No definite blocker observed",
                     "No active publication is proven. A timer may simply be waiting.",
                     "", "/logs?service=publisher"))
    summary=(f"{count} queued, {manual} manual" if available and count is not None
             and manual is not None else "Queue state unconfirmed")
    lines.append(section("publisher","Queued comments",publisher,summary,reasons,"/manage"))
    # Auto comments: review collision vs approval vs rejection are distinct.
    reasons=[]
    if metrics.get("auto_enabled") is False:
        reasons.append(_reason("AUTO_DISABLED","Automatic comments off",
                    "No automatic publication is permitted by the current switch.","","/automation"))
    if paused:
        reasons.append(_reason("GLOBAL_PAUSE","Global pause","Automatic posting is paused.","","/system/status"))
    if available:
        yes=history.get("approved_blocked",0)
        no=history.get("rejected_blocked",0)
        unknown=history.get("undecided_blocked",0)
        if yes:
            handoff=history.get("manual_handoff") or {}
            checked=handoff.get("checked",0)
            verified=handoff.get("verified",0)
            reasons.append(_reason("AUTO_APPROVED_HANDOFF",
                f"{yes} historical approved auto job(s) blocked",
                f"{verified} of {checked} inspected against current saved sources "
                "have a verified owner-controlled handoff; historical approval "
                "alone is not a new publication authorization. Check Scout "
                "for the explicit manual queue action; age, rate and duplicate "
                "checks still apply.",
                history.get("latest_review_block",{}).get("approved",""),"/scout"))
        if no:
            reasons.append(_reason("AUTO_REJECTED",f"{no} rejected auto draft(s) blocked",
                "Your rejection was respected. These are not awaiting approval and must not publish.",
                history.get("latest_review_block",{}).get("rejected",""), "/scout"))
        if unknown:
            reasons.append(_reason("REVIEW_UNCONFIRMED",f"{unknown} reviewed job(s) need checking",
                "The saved job reports a review block, but the stored decision is missing or does not match the draft.",
                history.get("latest_review_block",{}).get("unknown",""), "/scout"))
        if history["reviewed"].get("approved"):
            reasons.append(_reason("QUEUED_AUTO_APPROVED","Approved auto queue needs manual review",
                "An automatic queued job has an approval; automatic posting must not bypass it.",
                "", "/scout"))
        if auto==0 and metrics.get("auto_enabled") is True and not yes and not no:
            reasons.append(_reason("NO_AUTO_JOB","No automatic jobs queued",
                "Enabled does not mean scheduled posts. Scout may have produced no eligible draft; the cause is not established.",
                "", "/logs?service=scout"))
    if not reasons:
        reasons.append(_reason("AUTO_UNKNOWN","Automatic activity not established",
            "Check Scout selections, review decisions and publisher events.","","/scout"))
    window=history.get("job_window") or {}
    span=(" · history "+str(window.get("oldest"))[:10]+" to "+
          str(window.get("newest"))[:10]+" UTC" if window.get("oldest")
          and window.get("newest") else " · history range unavailable")
    auto_summary=(("Auto queue: "+str(auto) if auto is not None
                   else "Auto queue not reported")+
                  span+" · up to "+str(MAX_JOBS)+" recent jobs inspected")
    lines.append(section("auto","Automatic comments",
                  publisher,auto_summary,reasons,"/automation"))
    # Original posting is explicitly owner requested.
    reasons=[]
    drafted=safe_num(q,"originals_draft")
    submitted=safe_num(q,"originals_queued")
    generating=safe_num(q,"generation_queued")
    if original.get("code")=="MANUAL_ONLY" and available:
        reasons.append(_reason("MANUAL_ONLY","No automatic original-post authoring",
            "A daily limit is a safety cap, not an original-post schedule. You must request drafting and authorize publication.",
            "", "/originals"))
    elif drafted:
        reasons.append(_reason("OWNER_ACTION","Original drafts need owner action",
            f"{drafted} draft/approved original(s) await an explicit owner workflow step.","","/originals"))
    elif submitted:
        reasons.append(_reason("ORIGINAL_QUEUED","Original publication queued",
            f"{submitted} original publication(s) were explicitly queued; check status, timer and policy.","","/originals"))
    elif generating:
        reasons.append(_reason("DRAFT_PENDING","Original draft request pending",
            "A draft request is queued or running, but completion is not guaranteed.","","/originals"))
    if not reasons:
        reasons.append(_reason("ORIGINAL_UNCONFIRMED","Original activity status uncertain",
                       "See the dedicated Original Posts page for evidence.","","/originals"))
    lines.append(section("original","Original posts",original,
        "Attempted: "+str(usage.get("originals","unknown"))+" / "+
        str(limits.get("original_daily","unknown")),reasons,"/originals"))
    reasons=[]
    if scout.get("code")=="TIMER_DOWN":
        reasons.append(_reason("SCOUT_TIMER_DOWN","Scout timer inactive",
                       "No further scheduled Scout run is confirmed.","","/system/status"))
    elif scout.get("code")=="RECENT_FAILURE":
        reasons.append(_reason("RECENT_SCOUT_FAILURE","Last Scout attempt failed",
                       "Look at classified Scout errors; no new candidate is guaranteed.","","/logs?service=scout"))
    else:
        reasons.append(_reason("SCOUT_INCOMPLETE_EVIDENCE","Scout work is separate from publication",
                    "An observed Scout run or draft is not evidence of an actual published comment.",
                    scout.get("updated_at",""),"/logs?service=scout"))
    lines.append(section("scout","Scout discovery",scout,
         scout.get("activity","Scout state unconfirmed"),reasons,"/moltbook/friend-scout"))
    return {"checked_at":now.isoformat(timespec="seconds"),
            "available":bool(available),"sections":lines,
            "last_attempt":history.get("last_attempt") or "",
            "last_success":history.get("last_success") or "",
            "last_skip":history.get("last_skip"),
            "policy_next":(metrics.get("next_possible_utc") or {}).get("comments") or "",
            "scheduled_next":publisher.get("next_scheduled") or "",
            "scout_checkpoint":scout.get("updated_at") or "",
            "scout_activity":scout.get("activity") or "Not confirmed",
            "handoff_links":(history.get("manual_handoff") or {}).get("run_ids",[])[:MAX_LINKS],
            "handoff_verified":(history.get("manual_handoff") or {}).get("verified",0),
            "publisher_last_skip":history.get("last_skip"),
            "notice":"Reason codes are deterministic local observations, not a model's guess. "
                     "A saved approval does not mean a comment was sent."}

def collect(*,path=DB,observer=None,at=None):
    snap=(observer or overview_snapshot)()
    history=read_private(path,at=at)
    return explain(snap,history,at=at)

def page(wrap,*,data=None):
    item=data if data is not None else collect()
    parts=[CSS,'<div class="bi"><section class="bi-panel"><h2>Why no activity?</h2>',
           '<p class="bi-muted">'+e(item["notice"])+'</p>',
           '<div class="bi-links"><a href="/automation">Automation</a>',
           '<a href="/console">Console</a><a href="/logs">Logs</a>',
           '<a href="/investigate">Refresh evidence</a></div>',
           '<p class="bi-muted">Checked '+e(item["checked_at"])+
           ' · no actions or retries are performed here.</p></section>',
           '<section class="bi-panel"><h2>Last activity &amp; timing</h2>',
           '<p class="bi-line">Most recent Scout checkpoint: <b>'+
           e(item.get("scout_checkpoint") or "Not recorded")+'</b> · '+
           e(item.get("scout_activity") or "Status unconfirmed")+'</p>',
           '<p class="bi-line">Last publisher evaluation: <b>'+
           e((item.get("publisher_last_skip") or {}).get("at") or
             "No recent safe skip record")+'</b> · '+
           e((item.get("publisher_last_skip") or {}).get("code") or
             "No recorded skip")+'</p>',
           '<p class="bi-line">Last recorded attempt: <b>'+
           e(item["last_attempt"] or "Not recorded")+'</b></p>',
           '<p class="bi-line">Last API-acknowledged publication: <b>'+
           e(item["last_success"] or "Not recorded in recent inspected jobs")+'</b></p>',
           '<p class="bi-line">Next systemd publisher trigger: <b>'+
           e(item["scheduled_next"] or
             "Not reported by systemd; check Automation / timer state")+'</b></p>',
           '<p class="bi-line">Earliest policy-permitted comment: <b>'+
           e(item["policy_next"] or "Not reported")+'</b> (not scheduled)</p>',
           '<p class="bi-muted">API acknowledgement is not independent proof that '
           'a public reader can see the comment. No automatic retry of uncertain sends.</p>',
           '</section><div class="bi-grid">']
    for section in item["sections"]:
        state=section["state"] if section["state"] in (
            "active","waiting","blocked","idle","unknown") else "unknown"
        parts += ['<section class="bi-card"><div class="bi-head"><strong>'+
                  e(section["title"])+'</strong><span class="bi-pill" data-state="'+state+
                  '">'+state+'</span></div><p class="bi-muted">'+
                  e(section["summary"])+'</p><div class="bi-reasons">']
        for reason in section["reasons"]:
            parts += ['<div class="bi-reason"><b>'+e(reason["title"])+'</b>',
                      '<p>'+e(reason["detail"])+'</p>',
                      '<span class="bi-code">'+e(reason["code"])+
                      ' · '+e(reason["source"])+'</span></div>']
        parts += ['</div><p class="bi-line"><a href="'+e(section["href"])+
                  '">Inspect supporting records</a></p></section>']
    if item.get("handoff_links"):
        parts += ['<section class="bi-panel"><h2>Source-verified manual handoffs</h2>',
                  '<p class="bi-muted">These historical jobs still pass the '
                  'read-only saved-source check. Links open owner review; '
                  'nothing is sent or queued from this page. '
                  'The publisher will still enforce age, rate and duplicate safety checks.</p>',
                  '<div class="bi-links">']
        for rid in item["handoff_links"][:MAX_LINKS]:
            if RUN.fullmatch(str(rid)):
                parts.append('<a href="/scout#run-'+e(rid)+'">Review '+e(rid)+'</a>')
        parts.append('</div></section>')
    parts += ['</div></div>']
    return wrap("Why no activity?","".join(parts),"/investigate")
