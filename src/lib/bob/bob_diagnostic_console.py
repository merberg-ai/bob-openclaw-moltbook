"""OC3: safe terminal-like diagnostic stream over existing sanitized evidence.

No terminal commands, session transcripts, raw Ollama/Gateway payloads, journal
text, credentials, or write authority. All output is bounded, allowlisted, and
read-only. Default stream skips expensive journalctl; the Journal filter is
explicit and has no automatic polling.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import urlencode
import json

import bob_diagnostic_logs as logs
from bob_live_status import snapshot as status_snapshot
from navigation_shell import wrap

SOURCES=("all","jobs","events","checkpoints","health","journal")
SERVICES=logs.SERVICES+("ollama",)
LEVELS=logs.LEVELS
WINDOWS=logs.WINDOWS
MAX_ROWS=80
MAX_QUERY=logs.MAX_QUERY
SAFE_HEALTH={
    "running":("info","running"),
    "ready":("info","ready"),
    "listening":("info","listening"),
    "idle":("info","idle (one-shot service may be healthy)"),
    "inactive":("warning","inactive"),
    "failed":("error","failed"),
    "unavailable":("warning","unavailable"),
    "model_missing":("warning","required model not found"),
    "unknown":("warning","unknown"),
}
HEALTH_SERVICES={
    "Gateway":"gateway","Gateway port":"gateway",
    "Scout":"scout","Scout timer":"scout",
    "Publisher":"publisher","Publisher timer":"publisher",
    "Activity Manager":"manager","Ollama":"ollama",
}
MAX_TEXT_BYTES=24000
CSS="""<style>
.bco{max-width:1160px;margin:auto;display:grid;gap:11px}
.bco-panel{border:1px solid #334f6a;border-radius:14px;padding:clamp(11px,2vw,18px);
background:linear-gradient(145deg,#15293e,#0d1b2b);min-width:0}
.bco h2{font-size:1.1rem;margin:0 0 8px}
.bco-muted{color:#a8c0d7;font-size:.79rem;line-height:1.45}
.bco-filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.bco label{font-size:.79rem;color:#c5d9ec;display:grid;gap:4px}
.bco :is(select,input){background:#0a1726;border:1px solid #4d7191;color:#edf6ff;
border-radius:8px;min-height:40px;padding:7px;font:inherit;box-sizing:border-box;width:100%;min-width:0}
.bco-controls{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:8px}
.bco-controls button,.bco-controls a{font:inherit;font-size:.78rem;padding:8px 10px;
min-height:40px;border-radius:8px;border:1px solid #527ca2;background:#244c70;
color:#edf5ff;text-decoration:none;cursor:pointer}
.bco-controls button[disabled]{opacity:.55}
.bco-controls .bco-check{display:flex;gap:6px;align-items:center}
.bco-check input{min-height:auto;width:auto;accent-color:#70c8ff}
.bco-screen{position:relative;min-height:210px;max-height:590px;overflow:auto;overscroll-behavior:contain;
background:#050d15;border:1px solid #34506a;border-radius:12px;padding:8px;
font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.76rem;line-height:1.6}
.bco-line{display:grid;grid-template-columns:minmax(0,auto) auto auto minmax(0,1fr);
gap:7px;align-items:start;border-bottom:1px solid #12263a;padding:4px 0;overflow-wrap:anywhere}
.bco-line:last-child{border-bottom:0}
.bco-time{color:#849db4;font-variant-numeric:tabular-nums;white-space:nowrap}
.bco-level{font-weight:800}
.bco-level[data-level=error]{color:#ffaaa5}
.bco-level[data-level=warning]{color:#f1ce89}
.bco-level[data-level=info]{color:#8bd2b8}
.bco-service{color:#96c9ef}
.bco-message{color:#d8e6f1;min-width:0;white-space:pre-wrap;overflow-wrap:anywhere}
.bco-note{color:#92abc3}
.bco-meta{display:flex;align-items:center;flex-wrap:wrap;gap:8px}
.bco-status{font-size:.75rem;color:#afd8f0}
.bco :is(a,button,select,input):focus-visible{outline:2px solid #f3ce83;outline-offset:2px}
@media(max-width:850px){.bco-filters{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:590px){.bco-line{grid-template-columns:1fr auto;gap:3px 6px}
.bco-message{grid-column:1/-1}.bco-time{white-space:normal}
.bco-screen{max-height:470px}.bco-controls button{flex:1 1 auto}}
@media(prefers-reduced-motion:reduce){.bco *{animation:none!important;scroll-behavior:auto!important}}
</style>"""

def e(v):
    return escape(str(v if v is not None else ""),quote=True)

def options(params):
    """Strict bounded filters; unknown/untrusted GET args never reach subprocess."""
    def one(key,default):
        value=params.get(key,[])
        return value[0] if isinstance(value,list) and len(value)==1 and isinstance(value[0],str) else default
    service=one("service","all")
    source=one("source","all")
    level=one("level","all")
    window=one("window","24h")
    q=one("q","").strip()
    return {"service":service if service in SERVICES else "all",
            "source":source if source in SOURCES else "all",
            "level":level if level in LEVELS else "all",
            "window":window if window in WINDOWS else "24h",
            "q":q[:MAX_QUERY] if len(q)<=MAX_QUERY else ""}

def params_url(opts,*,output="json"):
    data={k:opts[k] for k in ("service","source","level","window","q")}
    if output=="text":
        data["format"]="text"
    return "/api/dashboard/console?"+urlencode(data)

def _health(at, provider=None):
    """Service status names and states are allowlisted; not arbitrary raw output."""
    loader=provider or status_snapshot
    try:
        snapshot=loader()
    except (OSError,ValueError,TypeError,KeyError):
        return [],False
    output=[]
    if not isinstance(snapshot,dict):
        return [],False
    for obj in (snapshot.get("services") or [])[:12]:
        if not isinstance(obj,dict):
            continue
        name=obj.get("name")
        key=HEALTH_SERVICES.get(name) if isinstance(name,str) else None
        val=obj.get("state")
        if key and isinstance(val,str) and val in SAFE_HEALTH:
            level,label=SAFE_HEALTH[val]
            # Fresh probe is an observation, NOT an event or proof of activity.
            output.append({"service":key,"level":level,"source":"health",
                           "at":at.isoformat(timespec="seconds"),
                           "when":at,"id":"","message":name+": "+label})
    return output,True

def collect(opts,*,db_path=None,checkpoint_root=None,
            journal_runner=None,health_provider=None,at=None):
    at=at or datetime.now(timezone.utc)
    since=at-timedelta(days=WINDOWS[opts["window"]])
    db_entries=[]
    checkpoints=[]
    journal=[]
    sources={"database":None,"journal":None,"health":None}
    if opts["source"] in ("all","jobs","events","checkpoints"):
        db_entries,db_ok=logs._db_entries(logs.DB if db_path is None else db_path)
        sources["database"]=db_ok
    if opts["source"] in ("all","checkpoints"):
        checkpoints=logs._checkpoint_entries(checkpoint_root)
        logs.correlate_checkpoints(checkpoints,db_entries,[],journal_ok=False)
    if opts["source"]=="journal":
        if opts["service"]=="ollama":
            # Ollama is not a vetted user-systemd unit; only its local
            # fixed-loopback readiness probe is exposed under Health.
            journal=[]
            sources["journal"]=False
        else:
            journal,ok=logs._journal_entries(
                opts["service"],since,run=journal_runner or logs.subprocess.run)
            sources["journal"]=ok
    health=[]
    if opts["source"] in ("all","health"):
        health,ok=_health(at,health_provider)
        sources["health"]=ok
    entries=(
        [x for x in db_entries if opts["source"] in ("all",x["source"])]
        +checkpoints+journal+health
    )
    matches=[]
    needle=opts["q"].casefold()
    for row in entries:
        if row["when"]<since or row["when"]>at+timedelta(minutes=1):
            continue
        if opts["service"]!="all" and row["service"]!=opts["service"]:
            continue
        if opts["level"]!="all" and row["level"]!=opts["level"]:
            continue
        msg=row["message"]
        if needle and needle not in (msg+" "+row["id"]+" "+row["source"]+" "+row["service"]).casefold():
            continue
        # Values are already allowlisted/classified by the source collector.
        # Never serialize arbitrary DB details, exceptions or journal text.
        matches.append({k:str(row[k])[:350] for k in ("at","service","level","source","id","message")})
    matches.sort(key=lambda x:(x["at"],x["source"],x["id"]),reverse=True)
    return {"checked_at":at.isoformat(timespec="seconds"),
            "entries":matches[:MAX_ROWS],
            "matched":len(matches),
            "sources":sources,
            "journal_explicit_only":True}

def _select(name,choices,chosen):
    html=''.join('<option value="'+e(x)+'"'+(' selected' if x==chosen else '')+'>'+e(
         ("Local + health" if name=="source" and x=="all" else x.replace("_"," ").title()))+
         '</option>' for x in choices)
    return '<label>'+e(name.title())+'<select name="'+name+'" id="bco-'+name+'">'+html+'</select></label>'

def _entries_html(entries):
    if not entries:
        return '<div class="bco-note">No safe observations match these filters.</div>'
    parts=[]
    for row in entries[:MAX_ROWS]:
        parts += ['<div class="bco-line"><span class="bco-time">'+e(row["at"])+'</span>',
                  '<span class="bco-level" data-level="'+e(row["level"])+'">'+
                  e(row["level"].upper())+'</span>',
                  '<span class="bco-service">'+e(row["service"])+'</span>',
                  '<span class="bco-message">'+e(row["message"])+
                  (' · run '+e(row["id"]) if row["id"] else '')+
                  ' <span class="bco-note">['+e(row["source"])+']</span></span></div>']
    return "".join(parts)

def export_text(data):
    """Plain-text export of exactly the same sanitized/bounded JSON entries."""
    lines=["Bob Diagnostic Console (sanitized, read-only)",
           "Observed UTC: "+data["checked_at"],
           "Entries: "+str(len(data["entries"]))+" of "+str(data["matched"]),
           "Raw journal/private content is excluded.",""]
    for row in data["entries"][:MAX_ROWS]:
        lines.append(" ".join((row["at"],row["level"].upper(),row["service"],
                               "["+row["source"]+"]",row["message"],
                               ("run="+row["id"] if row["id"] else ""))).rstrip())
    return "\n".join(lines)[:MAX_TEXT_BYTES]+"\n"

def page(wrap,params,*,collector=None):
    opts=options(params)
    data=(collector or collect)(opts)
    notes=[]
    if data["sources"].get("database") is False:
        notes.append("Queue/event database not available.")
    if data["sources"].get("health") is False:
        notes.append("Local service readiness is not confirmed.")
    if opts["source"]=="journal" and data["sources"].get("journal") is False:
        notes.append("Allowlisted user-systemd journal unavailable for this filter.")
    notes.append("Default stream excludes journal reads; choose Journal to inspect classified entries.")
    parts=[CSS,'<div class="bco"><section class="bco-panel">',
           '<h2>Diagnostic Console</h2>',
           '<p class="bco-muted">Sanitized observations only · UTC · read-only. '
           'No prompt text, credentials, private notes or raw terminal access. '
           'The recorded events and readiness checks do not prove Bob is actively working.</p>',
           '<form id="bco-form" method="get" action="/console"><div class="bco-filters">',
           _select("service",SERVICES,opts["service"]),
           _select("level",LEVELS,opts["level"]),
           _select("source",SOURCES,opts["source"]),
           _select("window",WINDOWS,opts["window"]),
           '</div><div class="bco-controls"><label style="flex:1 1 180px">Search / job ID',
           '<input id="bco-q" type="search" name="q" maxlength="80" value="'+e(opts["q"])+
           '" placeholder="failed, 429, or run ID"></label>',
           '<button type="submit">Apply filters</button><a href="/console">Clear</a>',
           '</div></form></section>',
           '<section class="bco-panel"><div class="bco-meta">',
           '<strong>Safe diagnostic stream</strong>',
           '<span class="bco-status" id="bco-status">Loaded '+str(len(data["entries"]))+
           ' of '+str(data["matched"])+' · '+e(data["checked_at"])+'</span></div>',
           '<div class="bco-controls">',
           '<button id="bco-refresh" type="button">Refresh now</button>',
           '<button id="bco-pause" type="button" aria-pressed="false">Pause updates</button>',
           '<label class="bco-check"><input type="checkbox" id="bco-follow" checked>Auto-scroll</label>',
           '<button id="bco-copy" type="button">Copy safe lines</button>',
           '<a id="bco-export" download="bob-console-sanitized.txt" href="'+
           e(params_url(opts,output="text"))+'">Export safe text</a>',
           '</div><p class="bco-muted" id="bco-note">'+e(" ".join(notes))+'</p>',
           '<div class="bco-screen" id="bco-screen" tabindex="0" role="log" '
           'aria-label="Sanitized diagnostic entries" aria-live="off">'+
           _entries_html(data["entries"])+'</div>',
           '<p class="bco-muted">Showing at most '+str(MAX_ROWS)+' safe records. '
           'Auto-refresh every 45 seconds while visible (not for Journal). '
           'Filtered system journals use allowlisted units and never expose raw lines. '
           '<a href="/logs">Open detailed Logs</a> · '
           '<a href="/system/status">System status</a>.</p></section></div>',
           '<script src="/assets/bob-console.js" defer></script>']
    return wrap("Console","".join(parts),"/console")

JS=r"""'use strict';
(()=>{
  const find=(id)=>document.getElementById('bco-'+id);
  const screen=find('screen'),form=find('form'),status=find('status');
  if(!screen||!form||!status)return;
  const refresh=find('refresh'),pause=find('pause'),follow=find('follow'),copy=find('copy');
  const knownServices=new Set(['scout','publisher','original','original_publish','manager','gateway','ollama']);
  const knownSources=new Set(['jobs','events','checkpoints','health','journal']);
  const knownLevels=new Set(['error','warning','info']);
  let stopped=false,inflight=false,lines=[];
  function options(){
    const params=new URLSearchParams(new FormData(form));
    params.delete('format');
    return params;
  }
  function render(items){
    lines=items.slice(0,80).filter(r=>r&&knownServices.has(r.service)&&
      knownSources.has(r.source)&&knownLevels.has(r.level)&&typeof r.message==='string'&&
      typeof r.at==='string').map(r=>({
      at:r.at.slice(0,40),service:r.service,source:r.source,level:r.level,
      message:r.message.slice(0,350),id:typeof r.id==='string'?r.id.slice(0,26):''
    }));
    const fragment=document.createDocumentFragment();
    lines.forEach(r=>{
      const row=document.createElement('div');row.className='bco-line';
      const time=document.createElement('span');time.className='bco-time';time.textContent=r.at;
      const level=document.createElement('span');level.className='bco-level';
      level.dataset.level=r.level;level.textContent=r.level.toUpperCase();
      const service=document.createElement('span');service.className='bco-service';service.textContent=r.service;
      const message=document.createElement('span');message.className='bco-message';
      message.textContent=r.message+(r.id?' · run '+r.id:'')+' ['+r.source+']';
      row.append(time,level,service,message);fragment.append(row);
    });
    if(!lines.length)fragment.append(document.createTextNode('No safe observations match these filters.'));
    screen.replaceChildren(fragment);
    if(follow.checked)screen.scrollTop=screen.scrollHeight;
  }
  async function update(){
    if(stopped||inflight||document.hidden)return;
    inflight=true;refresh.disabled=true;
    const controller=new AbortController();
    const deadline=setTimeout(()=>controller.abort(),23000);
    try{
      const url='/api/dashboard/console?'+options().toString();
      const response=await fetch(url,{credentials:'same-origin',cache:'no-store',
        headers:{Accept:'application/json'},signal:controller.signal});
      if(!response.ok)throw Error('status');
      const data=await response.json();
      if(!data||!Array.isArray(data.entries))throw Error('schema');
      render(data.entries);
      status.textContent='Loaded '+lines.length+' of '+Number(data.matched||0)+
        ' · '+String(data.checked_at||'UTC unknown');
    }catch(_){status.textContent='Refresh failed; showing last known sanitized snapshot (possibly stale).';}
    finally{clearTimeout(deadline);refresh.disabled=false;inflight=false;}
  }
  refresh.addEventListener('click',()=>{
    if(stopped){stopped=false;pause.setAttribute('aria-pressed','false');pause.textContent='Pause updates';}
    update();
  });
  pause.addEventListener('click',()=>{
    stopped=!stopped;pause.setAttribute('aria-pressed',String(stopped));
    pause.textContent=stopped?'Resume updates':'Pause updates';
    if(!stopped)update();
  });
  copy.addEventListener('click',()=>{
    const text=screen.textContent||'No safe observations';
    const fallback=()=>{
      const field=document.createElement('textarea');field.value=text;
      field.setAttribute('readonly','');field.style.position='fixed';field.style.opacity='0';
      document.body.append(field);field.select();
      const ok=document.execCommand('copy');field.remove();
      status.textContent=ok?'Sanitized lines copied.':'Copy unavailable; use Export safe text.';
    };
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(()=>{status.textContent='Sanitized lines copied.';}).catch(fallback);
    }else{fallback();}
  });
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!stopped&&find('source').value!=='journal')update();});
  setInterval(()=>{if(!stopped&&find('source').value!=='journal')update();},45000);
})();
"""

def javascript():
    return JS
