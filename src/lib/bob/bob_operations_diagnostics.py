"""OC0: Deterministic, read-only explanations for the existing Overview.

Uses recorded counters, actual worker checkpoints, and allowlisted systemd
timer observations. It neither infers agent intent nor creates jobs. No model,
network, credentials, Moltbook calls, private body text, shell, or DB writes.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import re
import subprocess

ACTIVE={"fetching","validating","generating","preflight","sending","verifying"}
TERMINAL={"failed","uncertain","awaiting_verification"}
LABELS={
 "fetching":"Reading public discussions",
 "validating":"Validating a saved job",
 "generating":"Thinking through a request with the local agent",
 "preflight":"Checking the public target",
 "sending":"Submitting an explicitly authorized publication",
 "verifying":"Checking an owner-supplied verification",
}
TIMERS={"scout":"bob-moltbook-scout.timer","publisher":"bob-moltbook-publisher.timer"}
SERVICE_TIMERS={"scout":"Scout timer","publisher":"Publisher timer"}
KNOWN_STATES={"running","ready","idle","inactive","failed","unknown","unavailable","model_missing","listening"}
TIME_MAX=80
TIMESTAMP=re.compile(r"^[A-Za-z0-9 :+.,_()/-]{1,80}$")
MAX_AGE_SECONDS=360

def _date(value):
    try:
        parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError, AttributeError):
        return None

def _time(value):
    return value if isinstance(value,str) and _date(value) else ""

def _when(at):
    return (at or datetime.now(timezone.utc)).astimezone(timezone.utc)

def _recent(worker,now):
    updated=_date(worker.get("updated_at")) if isinstance(worker,dict) else None
    return bool(updated and -60 <= (now-updated).total_seconds() <= MAX_AGE_SECONDS
                and not worker.get("stale"))

def _status(worker,now):
    if not isinstance(worker,dict):
        return None
    stage=worker.get("stage")
    if stage in ACTIVE and _recent(worker,now):
        return "active"
    return None

def _entry(key,state,activity,reason,evidence,when="",href="/logs",
           code="UNKNOWN",next_run=""):
    return dict(key=key,state=state,activity=activity,reason=reason,
                code=code,evidence=evidence,updated_at=_time(when),
                href=href,next_scheduled=next_run)

def _timer_schedules(*,run=subprocess.run):
    """Read only the two known user timers. Return raw systemd wall-clock text.

    These are provider-reported scheduled triggers, NOT rate eligibility;
    invalid/unavailable response becomes unknown rather than an invented time.
    """
    times={}
    for key,unit in TIMERS.items():
        try:
            res=run(["systemctl","--user","show",unit,
                     "--property=NextElapseUSecRealtime","--value"],
                    capture_output=True,text=True,timeout=1.5,check=False)
            value=res.stdout.strip() if res.returncode==0 else ""
            times[key]=value if (value not in ("","n/a","0") and
                                  TIMESTAMP.fullmatch(value)) else ""
        except (OSError, subprocess.TimeoutExpired, TypeError, AttributeError):
            times[key]=""
    return times

def _eligible_time(metrics,key,now):
    values=metrics.get("next_possible_utc") if isinstance(metrics,dict) else None
    raw=values.get(key) if isinstance(values,dict) else None
    timestamp=_date(raw)
    return timestamp if timestamp and timestamp>now+timedelta(seconds=5) else None

def explain(metrics,services,workers,paused,*,at=None,timers=None):
    """Pure policy explainer, no IO. Unknown is a real result, never guessed."""
    now=_when(at)
    info=metrics if isinstance(metrics,dict) else {}
    available=info.get("available") is True
    q=info.get("queues") if available else None
    q=q if isinstance(q,dict) else {}
    sv={str(x.get("name")):x.get("state") for x in (services or [])
        if isinstance(x,dict)}
    by_worker={str(x.get("worker")):x for x in (workers or [])
               if isinstance(x,dict)}
    sched=timers if isinstance(timers,dict) else {}
    def count(key):
        value=q.get(key)
        return value if type(value) is int and value>=0 else None
    def clock(key):
        return sched.get(key,"") if isinstance(sched.get(key),str) else ""
    def checkpoint(key):
        item=by_worker.get(key)
        return item.get("updated_at","") if isinstance(item,dict) else ""
    def active(key):
        item=by_worker.get(key)
        return _status(item,now) if item else None
    def active_result(key,label,href):
        w=by_worker[key]
        stage=w.get("stage")
        return _entry(key,"active",LABELS[stage],f"{label}: verified recent {stage} checkpoint.",
                      "recent_worker_checkpoint",checkpoint(key),href,"WORKER_ACTIVE",
                      clock(key))
    def timer_down(key):
        state=sv.get(SERVICE_TIMERS[key])
        return state in ("inactive","failed","unavailable")
    def timer_reason(key,subject,href):
        state=sv.get(SERVICE_TIMERS[key])
        if state in ("inactive","failed","unavailable"):
            return _entry(key,"blocked",subject+" timer is "+str(state),
                          "The systemd timer is not running. Check services and sanitized logs.",
                          "systemd_unit_state",checkpoint(key),href,"TIMER_DOWN",clock(key))
        return None
    # Scout reports a verified stage, not proven completion of all future runs.
    if paused:
        scout=_entry("scout","blocked","Scout paused",
                     "Global Bob pause is active.", "pause_file",checkpoint("scout"),
                     "/system/status","GLOBAL_PAUSE",clock("scout"))
    elif timer_down("scout"):
        scout=timer_reason("scout","Scout","/logs?service=scout")
    elif active("scout"):
        scout=active_result("scout","Scout","/logs?service=scout")
    elif isinstance(by_worker.get("scout"),dict) and by_worker["scout"].get("stage")=="failed" and _recent(by_worker["scout"],now):
        scout=_entry("scout","blocked","Last Scout attempt failed",
                     "A recent Scout failure was recorded; the next run is not guaranteed.",
                     "recent_worker_checkpoint",checkpoint("scout"),"/logs?service=scout",
                     "RECENT_FAILURE",clock("scout"))
    else:
        scout=_entry("scout","waiting" if sv.get("Scout timer")=="running" else "unknown",
                     "Waiting for Scout timer" if sv.get("Scout timer")=="running" else "Scout scheduling not confirmed",
                     "No active Scout execution is confirmed. Check last run and timer.",
                     "systemd_timer_and_checkpoint",checkpoint("scout"),
                     "/logs?service=scout","NO_ACTIVE_SCOUT",clock("scout"))
    manual=count("manual_queued")
    auto=count("auto_queued")
    queued=count("comments_queued")
    if paused:
        publisher=_entry("publisher","blocked","Comment publishing paused",
                         "Global Bob pause is active.", "pause_file",checkpoint("publisher"),
                         "/manage","GLOBAL_PAUSE",clock("publisher"))
    elif timer_down("publisher"):
        publisher=timer_reason("publisher","Publisher","/logs?service=publisher")
    elif active("publisher"):
        publisher=active_result("publisher","Publisher","/logs?service=publisher")
    elif not available or queued is None:
        publisher=_entry("publisher","unknown","Comment queue unavailable",
                         "No reliable queue count; cause cannot be determined.",
                         "metrics_unavailable",checkpoint("publisher"),"/logs?service=publisher",
                         "NO_METRICS",clock("publisher"))
    elif queued>0:
        due=_eligible_time(info,"comments",now)
        backlog=f"{queued} queued comment"+("s" if queued!=1 else "")+". "
        priority=(f"{manual} manual queued first. " if manual else "")
        if due:
            publisher=_entry("publisher","waiting","Comments awaiting policy eligibility",
                backlog+priority+"Minimum interval or daily budget prevents an attempt until the displayed policy time. This is not a scheduled timer run.",
                "recorded_queue_and_rate_policy",checkpoint("publisher"),
                "/manage?tab=activity&state=queued","RATE_LIMIT",clock("publisher"))
        else:
            publisher=_entry("publisher","waiting","Comments queued; next worker action unconfirmed",
                backlog+priority+"Policy slot may be open, but no current send is confirmed; inspect publisher timer and logs.",
                "recorded_queue_not_process_proof",checkpoint("publisher"),
                "/logs?service=publisher","WAITING_WORKER",clock("publisher"))
    else:
        auto_enabled=info.get("auto_enabled") is True
        msg=("Auto comments are enabled but no comment is queued; an eligible Scout "
             "selection has not been confirmed here." if auto_enabled else
             "Auto comments are disabled and there are no queued comments.")
        publisher=_entry("publisher","idle","No comments queued",msg,
                         "recorded_queue_and_setting",checkpoint("publisher"),
                         "/scout" if auto_enabled else "/scout",
                         "NO_QUEUE" if auto_enabled else "AUTO_DISABLED",clock("publisher"))
    originals=count("originals_queued")
    drafts=count("originals_draft")
    generating=count("generation_queued")
    if paused:
        original=_entry("original","blocked","Original workflow paused",
                        "Global Bob pause is active.", "pause_file",checkpoint("original"),
                        "/originals","GLOBAL_PAUSE")
    elif active("original"):
        original=active_result("original","Original drafting","/originals")
    elif active("original_publish"):
        w=by_worker["original_publish"]
        original=_entry("original","active",LABELS[w["stage"]],
                        "An original-post worker checkpoint is active.",
                        "recent_worker_checkpoint",w.get("updated_at",""),
                        "/originals","WORKER_ACTIVE")
    elif not available or None in (originals,drafts,generating):
        original=_entry("original","unknown","Original workflow records unavailable",
                        "Cannot confirm a draft request, queue or publication outcome.",
                        "metrics_unavailable",checkpoint("original"),"/originals","NO_METRICS")
    elif originals>0:
        due=_eligible_time(info,"originals",now)
        original=_entry("original","waiting","Original post queued",
                        f"{originals} original publication(s) explicitly queued. "+
                        ("Waiting for the policy eligibility time; not a scheduled run." if due
                         else "No sending activity is confirmed; inspect the original publisher."),
                        "recorded_queue_and_policy",checkpoint("original_publish"),
                        "/originals","RATE_LIMIT" if due else "WAITING_WORKER")
    elif generating>0:
        original=_entry("original","waiting","Original drafting requested",
                        f"{generating} generation request(s) queued or running, but no active generation checkpoint is confirmed.",
                        "recorded_request",checkpoint("original"),"/originals","DRAFT_REQUEST_WAITING")
    elif drafts>0:
        original=_entry("original","waiting","Original drafts need owner action",
                        f"{drafts} draft/approved post(s). Publication requires separate owner authorization.",
                        "recorded_draft",checkpoint("original"),"/originals","OWNER_ACTION")
    else:
        original=_entry("original","idle","Original posts are owner-requested",
                        "No draft request or original publication is queued. The daily original-post budget is a cap, not an automatic writing schedule.",
                        "recorded_workflow_and_policy",checkpoint("original"),"/originals","MANUAL_ONLY")
    gw=sv.get("Gateway")
    port=sv.get("Gateway port")
    ollama=sv.get("Ollama")
    if ollama in ("unavailable","model_missing") or gw in ("failed","unavailable") or port=="unavailable":
        dependency=_entry("dependencies","blocked","Local AI dependency needs attention",
                          "Gateway or Ollama reports unavailable or missing model. This is not proof an attempted job failed.",
                          "service_probe","","/system/status","DEPENDENCY_DOWN")
    elif gw=="running" and ollama=="ready" and port=="listening":
        dependency=_entry("dependencies","idle","Gateway and Ollama appear ready",
                          "Services are reachable. Readiness does not mean Bob is thinking or performing a task.",
                          "service_probe","","/system/status","DEPENDENCIES_READY")
    else:
        dependency=_entry("dependencies","unknown","Local AI readiness not confirmed",
                          "One or more service/port observations are missing or ambiguous.",
                          "service_probe","","/system/status","DEPENDENCY_UNKNOWN")
    lanes=[scout,publisher,original,dependency]
    active_lanes=[x for x in lanes if x["state"]=="active"]
    if active_lanes:
        hero=active_lanes[0]
        headline=hero["activity"]
        state="active"
        detail="Verified recent worker checkpoint; live progress is not guaranteed."
    elif publisher["state"]=="waiting" and queued:
        hero=publisher
        headline="Bob has queued comments, but no active send is confirmed"
        state="waiting"
        detail=publisher["reason"]
    elif any(x["state"]=="blocked" for x in lanes):
        hero=next(x for x in lanes if x["state"]=="blocked")
        headline="An operation is blocked or paused"
        state="blocked"
        detail=hero["activity"]+". "+hero["reason"]
    elif any(x["state"]=="unknown" for x in lanes):
        hero=next(x for x in lanes if x["state"]=="unknown")
        headline="Bob's current work is not confirmed"
        state="unknown"
        detail="Available observations do not establish the current activity. "+hero["reason"]
    else:
        hero=scout
        headline="No active work observed"
        state="waiting"
        detail="No active worker checkpoint. A healthy wait is possible; this is not proof of a scheduled task."
    return {"state":state,"headline":headline,"detail":detail[:360],
            "evidence":"Observed status, policy and local queue records (not model inference)",
            "checked_at":now.isoformat(timespec="seconds"),
            "lanes":lanes}

def collect(metrics,services,workers,paused,*,at=None,timer_reader=None):
    reader=timer_reader or _timer_schedules
    try:
        clocks=reader()
    except (ValueError,TypeError,OSError):
        clocks={}
    return explain(metrics,services,workers,paused,at=at,timers=clocks)
