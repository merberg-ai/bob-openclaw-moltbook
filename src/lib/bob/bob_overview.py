"""Bob Overview: bounded authenticated read-only telemetry + responsive dashboard.

Counters are recorded SQLite facts. Gauges mean DAILY BUDGET CONSUMED only;
spinners mean a recent ACTIVE checkpoint, never guessed task progress.
No credentials, private prompt text, Moltbook writes, or DB migrations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import json
import sqlite3

from bob_live_status import snapshot as live_status
from bob_activity_limits import summary as limit_summary, last_attempt
from bob_operations_diagnostics import collect as operations_collect
from navigation_shell import wrap

DB = Path.home() / ".config/moltbook/activity-queue.sqlite3"
PAUSED = Path.home() / ".config/bob-system/paused"
BUSY = frozenset(("fetching", "validating", "generating", "preflight", "sending", "verifying"))
GOOD = frozenset(("running", "ready", "listening", "completed"))
BAD = frozenset(("failed", "unavailable", "error", "model_missing"))
KEYS = ("scout", "publisher", "original", "original_publish")
WORKERS = {"scout": "Scout", "publisher": "Comment publisher",
           "original": "Original drafting", "original_publish": "Original publisher"}


def _group(db, table, field="state"):
    if table not in ("publish_jobs", "original_posts", "original_requests"):
        raise ValueError("unsupported queue source")
    return {str(s): int(n) for s,n in db.execute(
        f"SELECT {field}, COUNT(*) FROM {table} GROUP BY {field}") if s is not None}


def _next_possible(now, used, cap, prior, gap):
    """Local policy earliest rate slot; NOT a scheduled worker run."""
    slot = now
    if used >= cap:
        slot = (now + timedelta(days=1)).replace(hour=0, minute=0,
                                                   second=0, microsecond=0)
    if prior is not None:
        slot = max(slot, prior + timedelta(minutes=gap))
    return slot.astimezone(timezone.utc).isoformat(timespec="seconds")


def recorded(path=DB, *, at=None):
    now = at or datetime.now(timezone.utc)
    empty = {"available": False, "limits": None, "usage": None, "queues": None,
             "recent_events": [], "next_possible_utc": None, "auto_enabled": None}
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return empty
    try:
        with sqlite3.connect(path.as_uri()+"?mode=ro", uri=True, timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            totals = limit_summary(db, at=now)
            limits = totals["limits"]
            comments = _group(db, "publish_jobs")
            originals = _group(db, "original_posts")
            requests = _group(db, "original_requests")
            modes = {str(mode): int(n) for mode,n in db.execute(
                "SELECT mode, COUNT(*) FROM publish_jobs WHERE state='queued' GROUP BY mode")}
            visible = db.execute(
                "SELECT COUNT(*) FROM original_posts WHERE visible=1").fetchone()[0]
            replies = db.execute("SELECT COUNT(*) FROM published_replies").fetchone()[0]
            original_replies = db.execute(
                "SELECT COUNT(*) FROM original_post_replies").fetchone()[0]
            auto = db.execute(
                "SELECT value FROM publish_settings WHERE name='auto_enabled'").fetchone()
            events = [{"at": str(at)[:35], "kind": str(kind)[:70]}
                      for at,kind in db.execute(
                          "SELECT at,kind FROM publish_events ORDER BY id DESC LIMIT 7")]
            comment_prior = last_attempt(db,"publish_jobs")
            original_prior = last_attempt(db,"original_posts")
        return {
            "available": True,
            "limits": limits,
            "usage": {"comments": totals["comment_used"], "auto": totals["auto_used"],
                      "originals": totals["original_used"]},
            "queues": {
                "comments_queued": int(comments.get("queued",0)),
                "manual_queued": int(modes.get("manual",0)),
                "auto_queued": int(modes.get("auto",0)),
                "comments_api_ack": int(comments.get("published",0)),
                "comments_uncertain": int(comments.get("uncertain",0) +
                                          comments.get("verified_unconfirmed",0)),
                "comments_verification": int(comments.get("awaiting_verification",0)),
                "originals_draft": int(originals.get("draft",0) +
                                        originals.get("approved",0)),
                "originals_queued": int(originals.get("queued",0)),
                "originals_api_ack": int(originals.get("published",0)),
                "originals_public_visible": int(visible),
                "originals_uncertain": int(originals.get("uncertain",0)),
                "generation_queued": int(requests.get("queued",0) +
                                         requests.get("running",0)),
                "replies_observed": int(replies + original_replies),
            },
            "auto_enabled": bool(auto and auto[0]=="1"),
            "recent_events": events,
            "next_possible_utc": {
                "comments": _next_possible(now,totals["comment_used"],
                    limits["comment_daily"],comment_prior,limits["comment_gap_minutes"]),
                "originals": _next_possible(now,totals["original_used"],
                    limits["original_daily"],original_prior,limits["original_gap_minutes"]),
            },
        }
    except (sqlite3.Error, ValueError, OSError, TypeError, KeyError):
        return empty


def snapshot(*, path=DB):
    status = live_status()
    data = recorded(path)
    pause = PAUSED.exists() and not PAUSED.is_symlink()
    ops=operations_collect(data,status["services"],status["workers"],pause)
    return {
        "operations": ops,
        "checked_at": status["checked_at"],
        "paused": pause,
        "services": status["services"][:12],
        "workers": status["workers"][:4],
        "queues_observed": bool(status["queue"]["available"]),
        "jobs": status["queue"]["jobs"][:6],
        "metrics": data,
        "note": "Recorded attempts, not successful posts. Processes do not imply job success. Spinners only indicate recent active worker checkpoints.",
    }


def esc(s):
    return escape(str(s if s is not None else ""), quote=True)


def pct(used, cap):
    return max(0, min(100, round(100 * used / cap))) if type(cap)==int and cap>0 and type(used)==int else 0


def tone(stage):
    if stage in BUSY: return "busy"
    if stage in GOOD: return "good"
    if stage in BAD: return "bad"
    if stage in ("paused", "waiting", "awaiting_verification", "uncertain"): return "warn"
    return "quiet"


STYLE = """<style>
.bo{--bo-blue:#66b7ff;--bo-mint:#6ee4d3;--bo-gold:#f4c578;--bo-pink:#d6a2ff;
 max-width:1150px;margin:auto;display:grid;gap:16px}
.bo *{box-sizing:border-box}
.bo-sub{color:#afc4dc;font-size:.88rem;line-height:1.5;margin:5px 0}
.bo button:focus-visible{outline:3px solid #ffe099;outline-offset:3px}
.bo-panel{background:linear-gradient(155deg,#172a40,#101d31);border:1px solid #2f4a69;
 border-radius:17px;padding:clamp(15px,2.5vw,22px);min-width:0}
.bo-panel-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:baseline;margin-bottom:14px}
.bo-panel h2{font-size:1.15rem;margin:0}
.bo-muted{color:#9fb6d0;font-size:.82rem}
.bo-caps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.bo-cap{background:#112137;border:1px solid #304f6c;border-radius:14px;padding:15px 11px;
 text-align:center;min-width:0}
.bo-ring{--progress:0%;--ring:#6fbaff;position:relative;margin:0 auto 8px;width:112px;height:112px;
 border-radius:50%;background:conic-gradient(var(--ring) var(--progress),#2c435e var(--progress));
 display:grid;place-items:center}
.bo-ring:before{content:"";position:absolute;inset:10px;border-radius:50%;background:#112137}
.bo-ring .bo-number{z-index:1;font-size:1.35rem;font-weight:800;font-variant-numeric:tabular-nums}
.bo-ring .bo-number small{font-size:.79rem;font-weight:600;color:#a9c0da}
.bo-cap b{display:block;font-size:.9rem;margin:4px 0}
.bo-cap p{font-size:.76rem;color:#a6bad2;margin:3px 0;line-height:1.5}
.bo-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.bo-facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.bo-fact{background:#101f32;border:1px solid #314c6a;border-radius:12px;padding:13px}
.bo-fact span{display:block;font-size:.77rem;color:#a9c0d8;line-height:1.4}
.bo-fact b{display:block;font-size:1.55rem;line-height:1.35;font-variant-numeric:tabular-nums}
.bo-fact a{font-size:.76rem;line-height:1.4}
.bo-list{display:grid;gap:8px}
.bo-row{display:flex;justify-content:space-between;align-items:center;gap:10px;
 background:#101f32;border:1px solid #304760;border-radius:11px;padding:10px 12px;min-width:0}
.bo-row>span:first-child{min-width:0;overflow-wrap:anywhere;font-weight:650;font-size:.87rem}
.bo-pill{display:inline-flex;align-items:center;gap:6px;border-radius:99px;
 padding:5px 10px;background:#263b53;color:#d4e0ee;font-size:.77rem;font-weight:700;white-space:nowrap}
.bo-pill[data-tone=good]{background:#1a463b;color:#a8f6dc}
.bo-pill[data-tone=bad]{background:#542a37;color:#ffc1ce}
.bo-pill[data-tone=warn]{background:#4a391f;color:#f7d79c}
.bo-pill[data-tone=busy]{background:#193e5b;color:#a9dcff}
.bo-pill[data-tone=busy]:before{content:"";border-radius:50%;width:10px;height:10px;
 border:2px solid #8dcfff;border-top-color:transparent;animation:bo-spin .95s linear infinite}
@keyframes bo-spin{to{transform:rotate(360deg)}}
.bo-progress{height:7px;border-radius:5px;background:#2a425f;overflow:hidden;margin:10px 0 4px}
.bo-progress>span{display:block;height:100%;width:0;background:linear-gradient(90deg,#338de8,#6ee4d3);
 border-radius:5px;transition:width .4s ease}
.bo-worker small{display:block;color:#9eb5d0;font-size:.75rem;overflow-wrap:anywhere;margin-top:4px}
.bo-events{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.bo-events li{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;
 border-bottom:1px solid #293d56;padding:7px 0;font-size:.85rem}
.bo-events li:last-child{border-bottom:0}
.bo-action{background:#234b74;border:1px solid #6e9fcd;color:#fff;padding:10px 16px;
 min-height:44px;border-radius:10px;font:inherit;cursor:pointer}
.bo-alert{border-left:3px solid #e9b575;padding:8px 12px;background:#49382144;
 color:#f3d9af;font-size:.86rem;line-height:1.5}
.bo-now{border-color:#3b618a;background:radial-gradient(circle at 95% 0%,#24517b88 0%,transparent 45%),linear-gradient(145deg,#152c47,#0b172a)}
.bo-now-top{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.bo-now-headline{font-size:1.03rem;font-weight:800;line-height:1.35;margin:8px 0 3px}
.bo-now-detail{color:#c2d6ea;font-size:.78rem;line-height:1.4;overflow-wrap:anywhere;margin:3px 0 8px}
.bo-now-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}
.bo-now-lane{background:#0d2036;border:1px solid #345575;border-radius:11px;padding:8px;min-width:0}
.bo-now-lane b{font-size:.8rem;display:block;margin-bottom:3px}
.bo-now-lane p{font-size:.74rem;color:#bfd0e3;overflow-wrap:anywhere;line-height:1.35;margin:3px 0}
.bo-now-lane small{font-size:.72rem;color:#a5bdd7;overflow-wrap:anywhere;display:block}
.bo-now-lane a{font-size:.75rem}
.bo-now :is(details) summary{cursor:pointer;color:#a8cbea;font-size:.73rem;padding:4px 0}
.bo-now :is(details) summary:focus-visible{outline:2px solid #eac873;outline-offset:2px}
.bo-now-why{margin-bottom:8px}
.bo-now .bo-muted{font-size:.73rem;margin:7px 0 0}
.bo-now-dot{width:9px;height:9px;display:inline-block;background:#8191a5;border-radius:50%;margin-right:7px;vertical-align:middle}
.bo-now-dot[data-tone=active]{background:#55c8ff;box-shadow:0 0 0 4px #55c8ff22;animation:bo-beat 1.4s ease-in-out infinite}
.bo-now-dot[data-tone=blocked]{background:#f7a8a8}
.bo-now-dot[data-tone=waiting]{background:#f0ce85}
.bo-now-dot[data-tone=idle]{background:#86ddbd}
@keyframes bo-beat{50%{box-shadow:0 0 0 8px #55c8ff00}}
@media(max-width:820px){.bo-now-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:370px){.bo-now-grid{grid-template-columns:1fr}}
.bo[aria-busy=true] .bo-action{opacity:.65}
@media(max-width:740px){.bo-grid{grid-template-columns:1fr}.bo-caps{gap:7px}
 .bo-cap{padding:12px 6px}.bo-ring{width:88px;height:88px}
 .bo-ring:before{inset:8px}.bo-ring .bo-number{font-size:1.06rem}
 .bo-ring .bo-number small{font-size:.68rem}}
@media(max-width:370px){.bo-ring{width:72px;height:72px}.bo-ring:before{inset:7px}
 .bo-ring .bo-number{font-size:.93rem}.bo-ring .bo-number small{font-size:.62rem}
 .bo-cap b{font-size:.79rem}}
@media(prefers-reduced-motion:reduce){.bo *{animation:none!important;transition:none!important}}
</style>"""


JS = r"""'use strict';
(() => {
  const root = document.getElementById('bob-overview');
  if (!root) return;
  const id = (s) => document.getElementById('bo-' + s);
  const jobs = id('jobs'), services = id('services'), workers = id('workers'), events = id('events');
  let inflight = false;
  const active = new Set(['fetching','validating','generating','preflight','sending','verifying']);
  const good = new Set(['running','ready','listening','completed']);
  const bad = new Set(['failed','unavailable','error','model_missing']);
  function tone(s) {
    if (active.has(s)) return 'busy';
    if (good.has(s)) return 'good';
    if (bad.has(s)) return 'bad';
    if (['paused','waiting','awaiting_verification','uncertain'].includes(s)) return 'warn';
    return 'quiet';
  }
  const txt = (n,v) => { const el = id(n); if (el) el.textContent = String(v); };
  function pill(s) {
    const x = document.createElement('span');
    x.className = 'bo-pill';
    x.dataset.tone = tone(s);
    x.textContent = s;
    return x;
  }
  function row(parent,label,status,detail) {
    const el = document.createElement('div');
    el.className = 'bo-row';
    const a = document.createElement('span');
    a.textContent = label;
    el.append(a, pill(status));
    if (detail) {
      const note = document.createElement('small');
      note.textContent = detail;
      note.className = 'bo-muted';
      a.append(document.createElement('br'),note);
    }
    parent.append(el);
  }
  function cap(name,used,max) {
    const goodUsed = Number.isSafeInteger(used) && used >= 0 ? used : null;
    const valid = Number.isSafeInteger(max) && max >= 0 && goodUsed !== null;
    const number = id('budget-'+name);
    if (number) number.textContent = valid ? (max === 0 ? 'Disabled' : used + ' / ' + max) : 'Unknown';
    const ring = id('ring-'+name);
    const percent = valid && max > 0 ? Math.max(0,Math.min(100,Math.round(used / max * 100))) : 0;
    if (ring) {
      ring.style.setProperty('--progress',percent+'%');
      ring.setAttribute('aria-label',name+' budget '+(valid ? max === 0 ? 'disabled' : percent+' percent consumed' : 'unknown'));
    }
    const bar = id('bar-'+name);
    if (bar) bar.style.width = percent+'%';
  }
  function draw(d) {
    if (!d || !Array.isArray(d.services) || !Array.isArray(d.workers) || !d.metrics) throw Error('Invalid snapshot');
    const m=d.metrics;
    if (!m.available || !m.limits || !m.usage || !m.queues) {
      ['comments','auto','originals'].forEach(n=>cap(n,null,null));
      txt('metrics-state','Metrics unavailable; no counts inferred');
      ['comments-queued','manual-queued','auto-queued','originals-draft','originals-queued','api-ack','public-originals','replies','uncertain','generating'].forEach(n=>txt(n,'—'));
      txt('next-comment','Unknown');
      txt('next-original','Unknown');
      events.replaceChildren(document.createTextNode('Recent events unavailable.'));
    } else {
      txt('metrics-state',m.auto_enabled ? 'Auto comments enabled' : 'Auto comments disabled');
      cap('comments',m.usage.comments,m.limits.comment_daily);
      cap('auto',m.usage.auto,m.limits.comment_auto_daily);
      cap('originals',m.usage.originals,m.limits.original_daily);
      const q=m.queues;
      const fields={'comments-queued':q.comments_queued,'manual-queued':q.manual_queued,
        'auto-queued':q.auto_queued,'originals-draft':q.originals_draft,
        'originals-queued':q.originals_queued,'api-ack':q.comments_api_ack,
        'public-originals':q.originals_public_visible,'replies':q.replies_observed,
        'uncertain':q.comments_uncertain+q.originals_uncertain,'generating':q.generation_queued};
      Object.entries(fields).forEach(([key,value])=>txt(key,value));
      txt('next-comment',new Date(m.next_possible_utc.comments).toLocaleString());
      txt('next-original',new Date(m.next_possible_utc.originals).toLocaleString());
      events.replaceChildren();
      (Array.isArray(m.recent_events)?m.recent_events:[]).slice(0,7).forEach(x=>{
        const li=document.createElement('li');
        const strong=document.createElement('strong');
        strong.textContent=String(x.kind||'Event');
        const small=document.createElement('span');
        small.textContent=String(x.at||'');
        small.className='bo-muted';
        li.append(strong,small);
        events.append(li);
      });
      if (!events.childElementCount) events.textContent='No recorded events yet.';
    }
    const ops=d.operations;
    if (ops && Array.isArray(ops.lanes)) {
      txt('now-headline',String(ops.headline||'Current activity unconfirmed'));
      txt('now-detail',String(ops.detail||'No verified activity explanation available.'));
      txt('now-checked',String(ops.checked_at||'Unknown'));
      const overall=id('now-state');
      if(overall){overall.textContent=String(ops.state||'unknown');overall.dataset.tone=String(ops.state||'unknown');}
      const current=id('now-lanes');
      if(current){
        const expanded=new Set(Array.from(current.querySelectorAll('.bo-now-lane[data-key] details[open]'))
          .map(el=>el.closest('.bo-now-lane').dataset.key));
        current.replaceChildren();
        const labels={scout:'Scout',publisher:'Comment publisher',original:'Original posts',dependencies:'Gateway + Ollama'};
        const links={scout:'/logs?service=scout',publisher:'/logs?service=publisher',original:'/originals',dependencies:'/system/status'};
        ops.lanes.slice(0,4).forEach(item=>{
          if(!item || !Object.prototype.hasOwnProperty.call(labels,String(item.key)))return;
          const key=String(item.key);
          const card=document.createElement('div');card.className='bo-now-lane';card.dataset.key=key;
          const head=document.createElement('b');
          const dot=document.createElement('span');dot.className='bo-now-dot';dot.dataset.tone=String(item.state||'unknown');
          head.append(dot,document.createTextNode(labels[key]));
          const activity=document.createElement('p');activity.textContent=String(item.activity||'Status unconfirmed');
          const detail=document.createElement('details');detail.open=expanded.has(key);
          const summary=document.createElement('summary');summary.textContent='Why / evidence';
          const reason=document.createElement('small');
          reason.textContent=String(item.reason||'')+(item.next_scheduled?' · Systemd next: '+String(item.next_scheduled):'');
          const link=document.createElement('a');link.href=links[key];link.textContent='Inspect evidence';
          detail.append(summary,reason,link);
          card.append(head,activity,detail);
          current.append(card);
        });
      }
    } else {
      txt('now-headline','Current activity unavailable');
      txt('now-detail','No verified activity explanation. See System Status and Logs.');
      const current=id('now-lanes');if(current)current.replaceChildren();
    }
    services.replaceChildren();
    d.services.slice(0,12).forEach(x=>row(services,String(x.name||'Service'),String(x.state||'unknown')));
    workers.replaceChildren();
    const stages={};
    d.workers.forEach(x=>{if(x && x.worker) stages[x.worker]=x;});
    const titles={scout:'Scout',publisher:'Comment publisher',original:'Original drafting',original_publish:'Original publisher'};
    Object.keys(titles).forEach(kind=>{
      const s=stages[kind];
      row(workers,titles[kind],s ? String(s.stage||'unknown') : 'unobserved',
          s ? String(s.message||'')+' · '+String(s.updated_at||'') : 'No checkpoint observed yet');
    });
    jobs.replaceChildren();
    (Array.isArray(d.jobs)?d.jobs:[]).slice(0,6).forEach(x=>row(
      jobs,String(x.kind||'job')+' · '+String(x.job_id||'').slice(0,26),
      String(x.state||'unknown'),String(x.updated||x.created||'')));
    if (!jobs.childElementCount) jobs.textContent = d.queues_observed ? 'No recent jobs.' : 'Recent queue unavailable.';
    txt('notice','Read-only status updated. Counts represent attempts, not guaranteed public visibility.');
  }
  async function refresh() {
    if (inflight || document.hidden) return;
    inflight=true;
    const button=id('refresh');
    button.disabled=true;
    root.setAttribute('aria-busy','true');
    const ctrl=new AbortController();
    const timeout=setTimeout(()=>ctrl.abort(),12500);
    try {
      const response=await fetch('/api/dashboard/overview',{credentials:'same-origin',cache:'no-store',
        headers:{Accept:'application/json'},signal:ctrl.signal});
      if (!response.ok) throw Error('HTTP failure');
      draw(await response.json());
    } catch (_) {
      txt('notice','Refresh unavailable. Displaying last known snapshot; the values may be stale.');
    } finally {
      clearTimeout(timeout);
      root.setAttribute('aria-busy','false');
      button.disabled=false;
      inflight=false;
    }
  }
  id('refresh').addEventListener('click',refresh);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
  setInterval(refresh,15000);
})();
"""


def javascript():
    return JS


def _pill(state):
    return ('<span class="bo-pill" data-tone="'+tone(state)+'">'+esc(state)+'</span>')


def _cap(name, label, used, limit, subtitle, color):
    valid=type(used)==int and type(limit)==int and limit>=0
    percent=pct(used,limit) if valid and limit>0 else 0
    text=('Disabled' if limit==0 else f'{used} / {limit}') if valid else 'Unknown'
    return (f'<article class="bo-cap"><div class="bo-ring" id="bo-ring-{name}" '
            f'role="img" aria-label="{esc(label)} budget {percent} percent consumed" '
            f'style="--progress:{percent}%;--ring:{color}">'
            f'<span id="bo-budget-{name}" class="bo-number">{esc(text)}</span></div>'
            f'<b>{esc(label)}</b><p>{esc(subtitle)}</p>'
            f'<div class="bo-progress"><span id="bo-bar-{name}" style="width:{percent}%"></span></div>'
            '</article>')


def _fact(key, value, label, href=None):
    link = f'<a href="{href}">View details</a>' if href else ''
    return (f'<div class="bo-fact"><b id="bo-{key}">{esc(value)}</b>'
            f'<span>{esc(label)}</span>{link}</div>')


def _rows(items, *, worker=False):
    result=[]
    for item in items:
        if worker:
            title=WORKERS.get(item.get("worker"),"Worker")
            detail=f'{item.get("message","")} · {item.get("updated_at","")}'
            status=item.get("stage","unknown")
        else:
            title=item.get("name","Service")
            detail=""
            status=item.get("state","unknown")
        result.append(f'<div class="bo-row"><span>{esc(title)}'
                      + (f'<br><small class="bo-muted">{esc(detail)}</small>' if detail else '')
                      + '</span>'+_pill(status)+'</div>')
    return "".join(result)


def _operations_html(data):
    """Escaped SSR fallback. JS updates through textContent, never innerHTML."""
    ops=data.get("operations") or {}
    lanes=ops.get("lanes") if isinstance(ops,dict) else []
    lanes=lanes if isinstance(lanes,list) else []
    names={"scout":"Scout","publisher":"Comment publisher",
           "original":"Original posts","dependencies":"Gateway + Ollama"}
    links={"scout":"/logs?service=scout","publisher":"/logs?service=publisher",
           "original":"/originals","dependencies":"/system/status"}
    cards=[]
    for item in lanes[:4]:
        if not isinstance(item,dict) or item.get("key") not in names:
            continue
        key=item["key"]
        state=item.get("state","unknown")
        state=state if state in ("active","waiting","blocked","idle","unknown") else "unknown"
        extra=(" · Systemd next: "+str(item["next_scheduled"])
               if item.get("next_scheduled") else "")
        cards.append('<div class="bo-now-lane"><b><span class="bo-now-dot" data-tone="'+
                     state+'"></span>'+esc(names[key])+'</b><p>'+
                     esc(item.get("activity","Status unconfirmed"))+'</p>'+
                     '<details><summary>Why / evidence</summary><small>'+
                     esc(str(item.get("reason",""))+extra)+'</small><br>'
                     '<a href="'+links[key]+'">Inspect evidence</a></details></div>')
    state=ops.get("state","unknown")
    state=state if state in ("active","waiting","blocked","idle","unknown") else "unknown"
    return ('<section class="bo-panel bo-now" aria-label="Bob right now">'
            '<div class="bo-now-top"><h2>Bob right now</h2>'
            '<span id="bo-now-state" class="bo-pill" data-tone="'+state+'">'+
            esc(state)+'</span></div>'
            '<p id="bo-now-headline" class="bo-now-headline">'+
            esc(ops.get("headline","Current activity unconfirmed"))+'</p>'
            '<details class="bo-now-why"><summary>Why this status?</summary>'
            '<p id="bo-now-detail" class="bo-now-detail">'+
            esc(ops.get("detail","No verified status available."))+'</p></details>'
            '<div id="bo-now-lanes" class="bo-now-grid">'+''.join(cards)+'</div>'
            '<p class="bo-muted">Evidence checked: <span id="bo-now-checked">'+
            esc(ops.get("checked_at","Unknown"))+'</span>. '
            'Read-only observations; no inferred work or scheduled publications.</p>'
            '</section>')


def page(data):
    metrics=data["metrics"]
    avail=bool(metrics.get("available"))
    limits=metrics.get("limits") or {}
    usage=metrics.get("usage") or {}
    queue=metrics.get("queues") or {}
    count=lambda key: queue.get(key,"—") if avail else "—"
    cap=lambda name,lk,uk,desc,color:_cap(name,lk,
         usage.get(uk) if avail else None,limits.get(lk) if avail else None,desc,color)
    # display labels are not dict keys
    cards="".join([
        _cap("comments","Comments",usage.get("comments"),limits.get("comment_daily"),
             "Total attempts today · UTC","#66b7ff"),
        _cap("auto","Automatic",usage.get("auto"),limits.get("comment_auto_daily"),
             "Subset of comment budget","#6ee4d3"),
        _cap("originals","Original posts",usage.get("originals"),limits.get("original_daily"),
             "Owner-authorized attempts","#d6a2ff"),
    ])
    workers={x.get("worker"):x for x in data["workers"]}
    stages=[workers.get(key,{"worker":key,"stage":"unobserved","message":"No checkpoint observed yet"}) for key in KEYS]
    recent=metrics.get("recent_events") or []
    event_rows="".join('<li><strong>'+esc(x["kind"])+'</strong>'
                       '<span class="bo-muted">'+esc(x["at"])+'</span></li>' for x in recent)
    if not event_rows: event_rows='<li class="bo-muted">No recent events available.</li>'
    jobs="".join('<div class="bo-row"><span>'+esc(x.get("kind","job"))+' · '+
                 esc(str(x.get("job_id",""))[:26])+'<br><small class="bo-muted">'+
                 esc(x.get("updated") or x.get("created") or "")+'</small></span>'+
                 _pill(x.get("state","unknown"))+'</div>' for x in data["jobs"])
    if not jobs: jobs='<p class="bo-muted">No recent jobs available.</p>'
    times=metrics.get("next_possible_utc") or {}
    body=(STYLE+'<div class="bo" id="bob-overview">'
          '<section class="bo-panel"><div class="bo-panel-head"><h2>Daily activity budgets</h2>'
          '<span id="bo-metrics-state" class="bo-muted">'+
          esc("Auto comments enabled" if metrics.get("auto_enabled") else
              "Auto comments disabled" if avail else "Metrics unavailable")+
          '</span></div><div class="bo-caps">'+cards+'</div>'
          '<p class="bo-sub">Earliest policy-permitted comment (not scheduled): <b id="bo-next-comment">'+
          esc(times.get("comments","Unknown"))+'</b><br>'
          'Earliest policy-permitted original (not scheduled): <b id="bo-next-original">'+
          esc(times.get("originals","Unknown"))+'</b></p></section>'
          +_operations_html(data)+
          '<div class="bo-grid"><section class="bo-panel"><div class="bo-panel-head"><h2>Queue &amp; publication</h2>'
          '<a href="/manage" class="bo-muted">Manage queues</a></div><div class="bo-facts">'+
          _fact("comments-queued",count("comments_queued"),"Comments queued","/manage?tab=activity&state=queued")+
          _fact("manual-queued",count("manual_queued"),"Manual comment queue")+
          _fact("auto-queued",count("auto_queued"),"Automatic comment queue")+
          _fact("originals-draft",count("originals_draft"),"Original drafts / approved","/originals")+
          _fact("originals-queued",count("originals_queued"),"Originals queued","/originals")+
          _fact("generating",count("generation_queued"),"Generation requests underway")+
          '</div></section><section class="bo-panel"><div class="bo-panel-head"><h2>Recorded outcomes</h2>'
          '<a href="/activity" class="bo-muted">View activity</a></div><div class="bo-facts">'+
          _fact("api-ack",count("comments_api_ack"),"Comment API acknowledgments")+
          _fact("public-originals",count("originals_public_visible"),"Independently visible originals")+
          _fact("replies",count("replies_observed"),"Incoming replies observed")+
          _fact("uncertain",int(queue.get("comments_uncertain",0)+queue.get("originals_uncertain",0)) if avail else "—",
                "Uncertain / unconfirmed outcomes")+
          '</div><p class="bo-muted">Comment API acknowledgments do not prove '
          'public visibility. Uncertain results must never be blindly retried.</p></section></div>'
          '<div class="bo-grid"><section class="bo-panel"><div class="bo-panel-head">'
          '<h2>Services &amp; dependencies</h2><a href="/system/status" class="bo-muted">More detail</a>'
          '</div><div class="bo-list" id="bo-services">'+_rows(data["services"])+
          '</div></section><section class="bo-panel"><div class="bo-panel-head">'
          '<h2>Background workers</h2><span class="bo-muted">Observed checkpoints</span>'
          '</div><div class="bo-list" id="bo-workers">'+_rows(stages,worker=True)+
          '</div></section></div>'
          '<div class="bo-grid"><section class="bo-panel"><div class="bo-panel-head">'
          '<h2>Recent jobs</h2><a href="/system/status" class="bo-muted">All recent</a>'
          '</div><div id="bo-jobs" class="bo-list">'+jobs+'</div></section>'
          '<section class="bo-panel"><div class="bo-panel-head"><h2>Recent events</h2>'
          '<span class="bo-muted">Latest seven</span></div>'
          '<ul id="bo-events" class="bo-events">'+event_rows+'</ul></section></div>'
          '<div class="bo-panel"><div class="bo-panel-head"><h2>Live refresh</h2>'
          '<button class="bo-action" type="button" id="bo-refresh">Refresh now</button></div>'
          '<p class="bo-sub" id="bo-notice" role="status" aria-live="polite">'
          'Read-only status updates every 15 seconds while the tab is visible.</p>'
          '<noscript><p class="bo-alert">JavaScript disabled. Reload to obtain a new '
          'read-only snapshot; the page remains usable.</p></noscript></div></div>')
    output=wrap("Overview",body,"/")
    return output.replace('</head>',
                          '<script src="/assets/bob-overview.js" defer></script></head>',1)
