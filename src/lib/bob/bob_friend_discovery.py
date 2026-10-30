"""FM2: opt-in read-only public profile lookup and reviewed Scout friend suggestions.

Profile lookup makes exactly one anonymous HTTPS GET to the documented, fixed
Moltbook /api/v1/agents/profile?name= endpoint on user request. All discovered
Scout candidates have immutable local snapshot provenance and cannot be added
without an operator review and a recent matching API-reported profile.
No Moltbook API credentials, follows, posts, messages or autonomous jobs.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from html import escape
from http.client import HTTPSConnection
from urllib.parse import urlencode
import hashlib
import hmac
import json
import sqlite3
import secrets
import re

import bob_publish_common as common
import bob_friends as friends

HOST="www.moltbook.com"
ENDPOINT="/api/v1/agents/profile"
MAX_BYTES=65536
CACHE_HOURS=24
MAX_PROFILES=300
MAX_PENDING=30
MAX_CANDIDATES=200
MAX_CARDS=8
ID=re.compile(r"[0-9a-f]{24}\Z")
SHA=re.compile(r"[0-9a-f]{64}\Z")
UUID=common.UUID
FIELDS=("display_name","relationship","interests","notes")
PROPOSAL_COLS=("id","run_id","post_id","handle","handle_key","post_title",
               "why","status","created_at","reviewed_at","reason","friend_id","sha256")
PROFILE_COLS=("handle_key","handle","agent_id","description","karma",
              "followers","following","claimed","fetched_at","sha256")
ERRORS=frozenset((
    "Invalid discovery form",
    "Invalid friend candidate",
    "Friend candidate changed; reload",
    "Friend candidate already reviewed",
    "Friend candidate already staged",
    "Friend candidate directory is full",
    "Agent already in Friends directory",
    "Profile not found on Moltbook",
    "Public profiles require authorization; no credentials were sent",
    "Moltbook is rate limiting profile requests",
    "Moltbook profile lookup is temporarily unavailable",
    "Moltbook returned an unexpected profile",
    "Moltbook returned a different agent handle",
    "Look up a fresh matching public profile before approving",
    "Source Scout run unavailable or changed",
    "Review reason must be 1-240 characters",
    "Invalid agent handle (2-40 characters: letters, digits, underscore, dot, hyphen)",
    "Relationship must be interesting, acquaintance or friend",
    "Display name must be 0-100 characters",
    "Interests must be 0-500 characters",
    "Notes must be 0-1200 characters",
    "Friends directory capacity reached",
    "Agent handle already in directory",
))


def e(value):
    return escape(str(value if value is not None else ""),quote=True)


def initialize(db):
    friends.initialize(db)
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friend_profile_cache (
     handle_key TEXT PRIMARY KEY, handle TEXT NOT NULL,
     agent_id TEXT NOT NULL, description TEXT NOT NULL, karma INTEGER NOT NULL,
     followers INTEGER NOT NULL, following INTEGER NOT NULL, claimed INTEGER NOT NULL,
     fetched_at TEXT NOT NULL, sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friend_candidates (
     id TEXT PRIMARY KEY, run_id TEXT NOT NULL UNIQUE, post_id TEXT NOT NULL,
     handle TEXT NOT NULL, handle_key TEXT NOT NULL,
     post_title TEXT NOT NULL, why TEXT NOT NULL,
     status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
     created_at TEXT NOT NULL, reviewed_at TEXT NOT NULL, reason TEXT NOT NULL,
     friend_id TEXT NOT NULL, sha256 TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS bob_friend_candidates_state_idx "
               "ON bob_friend_candidates(status,created_at)")


def seal(item,cols):
    return hashlib.sha256(json.dumps(
        {k:item[k] for k in cols if k!="sha256"},
        sort_keys=True,ensure_ascii=False,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def _valid(item,cols):
    return isinstance(item["sha256"],str) and hmac.compare_digest(
        item["sha256"],seal(item,cols))


def _count(db,table,where=""):
    return db.execute("SELECT count(*) FROM "+table+where).fetchone()[0]


def _get_candidate(db,ident):
    if not isinstance(ident,str) or not ID.fullmatch(ident):
        raise ValueError("Invalid friend candidate")
    row=db.execute("SELECT "+",".join(PROPOSAL_COLS)+
                   " FROM bob_friend_candidates WHERE id=?",(ident,)).fetchone()
    if not row:
        raise ValueError("Invalid friend candidate")
    item=dict(zip(PROPOSAL_COLS,row))
    if not _valid(item,PROPOSAL_COLS):
        raise ValueError("Invalid friend candidate")
    return item


def profile_lookup(agent_handle,*,connection_cls=HTTPSConnection):
    """No credentials. No redirect handling, no dynamic host, no untrusted URL."""
    handle=friends.handle(agent_handle)
    path=ENDPOINT+"?"+urlencode({"name":handle})
    conn=connection_cls(HOST,timeout=8)
    try:
        conn.request("GET",path,headers={"Accept":"application/json",
                     "User-Agent":"Bob-Friends-Directory/0.7.4"})
        response=conn.getresponse()
        if response.status==404:
            raise ValueError("Profile not found on Moltbook")
        if response.status in (401,403):
            raise ValueError("Public profiles require authorization; no credentials were sent")
        if response.status==429:
            raise ValueError("Moltbook is rate limiting profile requests")
        if response.status!=200:
            raise ValueError("Moltbook profile lookup is temporarily unavailable")
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise ValueError("Moltbook returned an unexpected profile")
        payload=json.loads(raw)
        if not isinstance(payload,dict) or payload.get("success") is not True:
            raise ValueError("Moltbook returned an unexpected profile")
        data=payload.get("agent")
        if not isinstance(data,dict):
            raise ValueError("Moltbook returned an unexpected profile")
        name=data.get("name")
        if not isinstance(name,str) or name.casefold()!=handle.casefold():
            raise ValueError("Moltbook returned a different agent handle")
        agent_id=data.get("id")
        if not isinstance(agent_id,str) or not UUID.fullmatch(agent_id):
            raise ValueError("Moltbook returned an unexpected profile")
        def count(key):
            n=data.get(key)
            return n if type(n) is int and 0<=n<=10**9 else 0
        desc=data.get("description")
        if not isinstance(desc,str):
            desc=""
        claimed=data.get("is_claimed")
        profile=dict(handle_key=handle.casefold(),handle=handle,agent_id=agent_id,
                     description=desc[:900],karma=count("karma"),
                     followers=count("follower_count"),
                     following=count("following_count"),
                     claimed=1 if claimed is True else 0,
                     fetched_at=common.now())
        profile["sha256"]=seal(profile,PROFILE_COLS)
        return profile
    except (OSError,TimeoutError,json.JSONDecodeError,UnicodeError):
        raise ValueError("Moltbook profile lookup is temporarily unavailable") from None
    finally:
        conn.close()


def cache_profile(db,profile):
    initialize(db)
    h=friends.handle(profile["handle"])
    if profile["handle_key"]!=h.casefold() or not _valid(profile,PROFILE_COLS):
        raise ValueError("Moltbook returned an unexpected profile")
    old=db.execute("SELECT agent_id FROM bob_friend_profile_cache "
                   "WHERE handle_key=?",(h.casefold(),)).fetchone()
    # An observed same-handle account ID change must never be silently treated
    # as the old identity. Fail closed; manual troubleshooting is necessary.
    if old and old[0]!=profile["agent_id"]:
        raise ValueError("Moltbook returned a different agent handle")
    if not old and _count(db,"bob_friend_profile_cache")>=MAX_PROFILES:
        raise ValueError("Friend candidate directory is full")
    db.execute("INSERT INTO bob_friend_profile_cache("+",".join(PROFILE_COLS)+") VALUES("+
               ",".join("?" for _ in PROFILE_COLS)+") ON CONFLICT(handle_key) DO UPDATE SET "+
               ",".join(f"{k}=excluded.{k}" for k in PROFILE_COLS if k!="handle_key"),
               tuple(profile[k] for k in PROFILE_COLS))
    common.event(db,"bob_friend_profile_viewed",hashlib.sha256(h.casefold().encode()).hexdigest()[:12])


def cached(db,agent_handle):
    try:
        h=friends.handle(agent_handle)
        row=db.execute("SELECT "+",".join(PROFILE_COLS)+" FROM bob_friend_profile_cache "
                       "WHERE handle_key=?",(h.casefold(),)).fetchone()
        if not row:
            return None
        item=dict(zip(PROFILE_COLS,row))
        return item if _valid(item,PROFILE_COLS) else None
    except (ValueError,sqlite3.Error,KeyError,TypeError):
        return None


def fresh(item):
    if item is None:
        return False
    try:
        age=datetime.now(timezone.utc)-datetime.fromisoformat(item["fetched_at"])
        return timedelta(0)<=age<=timedelta(hours=CACHE_HOURS)
    except (ValueError,TypeError):
        return False


def source(run_id,loader=None):
    # Verified Scout choice ties author, post, and Bob's original rationale
    # to an immutable locally saved feed snapshot. Never a network fetch.
    h,rid,pid=friends._source_author(run_id,loader)
    rec=(loader or common.load_record)(rid)
    if not rec or rec.get("chosen_post_id")!=pid:
        raise ValueError("Source Scout run unavailable or changed")
    why=rec.get("why")
    title=rec.get("chosen_title")
    return h,rid,pid,(why.strip()[:420] if isinstance(why,str) else ""),(
        title.strip()[:160] if isinstance(title,str) else "")


def stage(db,run_id,*,loader=None):
    h,rid,pid,why,title=source(run_id,loader)
    initialize(db)
    if db.execute("SELECT 1 FROM bob_friend_candidates WHERE run_id=?",(rid,)).fetchone():
        raise ValueError("Friend candidate already staged")
    if db.execute("SELECT 1 FROM bob_friends WHERE handle_key=?",(h.casefold(),)).fetchone():
        raise ValueError("Agent already in Friends directory")
    if (_count(db,"bob_friend_candidates")>=MAX_CANDIDATES or
        _count(db,"bob_friend_candidates"," WHERE status='pending'")>=MAX_PENDING):
        raise ValueError("Friend candidate directory is full")
    item=dict(id=secrets.token_hex(12),run_id=rid,post_id=pid,handle=h,
              handle_key=h.casefold(),post_title=title,why=why,status="pending",
              created_at=common.now(),reviewed_at="",reason="",friend_id="")
    item["sha256"]=seal(item,PROPOSAL_COLS)
    db.execute("INSERT INTO bob_friend_candidates("+",".join(PROPOSAL_COLS)+") VALUES("+
               ",".join("?" for _ in PROPOSAL_COLS)+")",tuple(item[k] for k in PROPOSAL_COLS))
    common.event(db,"bob_friend_candidate_staged",item["id"])
    return item["id"]


def review(db,ident,expected_sha,action,reason,fields=None):
    if action not in ("approve","reject") or not isinstance(expected_sha,str) or not SHA.fullmatch(expected_sha):
        raise ValueError("Invalid discovery form")
    if not isinstance(reason,str) or not 1<=len(reason.strip())<=240:
        raise ValueError("Review reason must be 1-240 characters")
    initialize(db)
    item=_get_candidate(db,ident)
    if not hmac.compare_digest(item["sha256"],expected_sha):
        raise ValueError("Friend candidate changed; reload")
    if item["status"]!="pending":
        raise ValueError("Friend candidate already reviewed")
    fid=""
    if action=="approve":
        if not isinstance(fields,dict) or set(fields)!=set(FIELDS):
            raise ValueError("Invalid discovery form")
        values=friends.validate(fields)
        current_h,rid,pid,_,_=source(item["run_id"])
        if current_h.casefold()!=item["handle_key"] or pid!=item["post_id"]:
            raise ValueError("Source Scout run unavailable or changed")
        profile=cached(db,current_h)
        if not fresh(profile):
            raise ValueError("Look up a fresh matching public profile before approving")
        if db.execute("SELECT 1 FROM bob_friends WHERE handle_key=?",(current_h.casefold(),)).fetchone():
            raise ValueError("Agent already in Friends directory")
        fid=friends.create(db,current_h,values,source_kind="scout_snapshot",
                           run_id=rid,post_id=pid)
    item["status"]="approved" if action=="approve" else "rejected"
    item["reason"]=reason.strip()
    item["friend_id"]=fid
    item["reviewed_at"]=common.now()
    item["sha256"]=seal(item,PROPOSAL_COLS)
    values=[k for k in PROPOSAL_COLS if k!="id"]
    cur=db.execute("UPDATE bob_friend_candidates SET "+",".join(k+"=?" for k in values)+
                   " WHERE id=? AND sha256=? AND status='pending'",
                   tuple(item[k] for k in values)+(ident,expected_sha))
    if cur.rowcount!=1:
        raise ValueError("Friend candidate changed; reload")
    common.event(db,"bob_friend_candidate_"+action,ident)
    return fid


def dispatch(db,form):
    op=form.get("operation")
    if op=="stage":
        if set(form)!={"csrf","operation","run_id"}:
            raise ValueError("Invalid discovery form")
        return stage(db,form["run_id"])
    if op=="approve":
        if set(form)!={"csrf","operation","id","expected_sha","reason",*FIELDS}:
            raise ValueError("Invalid discovery form")
        return review(db,form["id"],form["expected_sha"],op,form["reason"],
                      {k:form[k] for k in FIELDS})
    if op=="reject":
        if set(form)!={"csrf","operation","id","expected_sha","reason"}:
            raise ValueError("Invalid discovery form")
        return review(db,form["id"],form["expected_sha"],op,form["reason"])
    raise ValueError("Invalid discovery form")


def safe_error(exc):
    if type(exc) is ValueError and str(exc) in ERRORS:
        return str(exc)
    return "Friend discovery unchanged. Reload and check the selected profile."


CSS="""<style>
.bfd{max-width:1080px;margin:auto;display:grid;gap:17px}
.bfd-panel{border:1px solid #37516c;background:linear-gradient(145deg,#17283f,#111e32);
 border-radius:14px;padding:clamp(15px,2.5vw,23px)}
.bfd h2{font-size:1.14rem;margin:0 0 11px}.bfd h3{font-size:1.03rem;margin:0 0 9px}
.bfd-muted{font-size:.85rem;color:#b6cadf;line-height:1.5}
.bfd-card{background:#13253a;border:1px solid #385777;border-radius:11px;
padding:15px;margin:11px 0;overflow-wrap:anywhere}
.bfd label{display:grid;gap:6px;margin:10px 0;font-weight:650}
.bfd input:not([type=hidden]),.bfd textarea,.bfd select{width:100%;min-height:44px;box-sizing:border-box;
padding:9px 11px;border:1px solid #597693;border-radius:9px;background:#0d1c2d;color:#f0f6ff;font:inherit}
.bfd textarea{min-height:96px;resize:vertical}
.bfd button,.bfd-link{display:inline-block;min-height:44px;padding:10px 14px;border-radius:9px;
border:1px solid #80afdd;background:#285e90;color:white;font:inherit;font-weight:700;
cursor:pointer;text-decoration:none}
.bfd button.secondary,.bfd-link.secondary{background:#26394e}
.bfd-actions{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.bfd-preview{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b1828;border-radius:8px;
border:1px solid #39516d;padding:12px;max-height:150px;overflow:auto}
.bfd-cols{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.bfd button:focus-visible,.bfd input:focus-visible,.bfd select:focus-visible,.bfd textarea:focus-visible{
outline:2px solid #8dc8fa;outline-offset:2px}
@media(max-width:720px){.bfd-cols{grid-template-columns:1fr}.bfd-actions button{width:100%}}
</style>"""


def _hidden(name,value):
    return '<input type="hidden" name="'+e(name)+'" value="'+e(value)+'">'


def _select(name,options,value):
    return '<label>'+e(name.title())+'<select name="'+e(name)+'">'+''.join(
        '<option value="'+e(opt)+'"'+(" selected" if opt==value else "")+'>'+
        e(opt.title())+'</option>' for opt in options)+'</select></label>'


def _form_review(item,csrf,op):
    base='<form method="post" action="/moltbook/discover">'+_hidden("csrf",csrf)+\
         _hidden("operation",op)+_hidden("id",item["id"])+\
         _hidden("expected_sha",item["sha256"])
    if op=="reject":
        return (base+'<label>Why reject?<input name="reason" maxlength="240" required></label>'+
                '<button class="secondary" type="submit">Reject suggestion</button></form>')
    return (base+'<div class="bfd-cols">'+
            '<label>Display name<input name="display_name" maxlength="100" value="'+
            e(item["handle"])+'"></label>'+_select("relationship",friends.RELATIONS,"interesting")+
            '</div><label>Topics and interests<textarea name="interests" maxlength="500">'+
            e(item["why"][:450])+'</textarea></label>'+
            '<label>Private notes<textarea name="notes" maxlength="1200"></textarea></label>'+
            '<label>Why approve?<input name="reason" maxlength="240" required></label>'+
            '<button type="submit">Approve and add to Friends</button></form>')


def page(db,csrf,wrap,params,records=None):
    initialize(db)
    def arg(name,default=""):
        v=params.get(name,[])
        return v[0] if len(v)==1 and isinstance(v[0],str) else default
    lookup=arg("profile")[:40].strip()
    selected=cached(db,lookup) if lookup else None
    staged={row[0] for row in db.execute("SELECT run_id FROM bob_friend_candidates")}
    pending=db.execute("SELECT "+",".join(PROPOSAL_COLS)+
                       " FROM bob_friend_candidates WHERE status='pending' "
                       "ORDER BY created_at DESC,id DESC LIMIT ?",(MAX_CARDS,)).fetchall()
    decided=db.execute("SELECT "+",".join(PROPOSAL_COLS)+
                       " FROM bob_friend_candidates WHERE status!='pending' "
                       "ORDER BY reviewed_at DESC,id DESC LIMIT ?",(MAX_CARDS,)).fetchall()
    suggestions=[]
    seen=set()
    for rec in (records or [])[:65]:
        rid=rec.get("run_id") if isinstance(rec,dict) else None
        if rid in staged:
            continue
        try:
            h,source_run,pid,why,title=source(rid)
        except (ValueError,OSError,TypeError):
            continue
        key=h.casefold()
        if key in seen or db.execute("SELECT 1 FROM bob_friends WHERE handle_key=?",(key,)).fetchone():
            continue
        seen.add(key)
        suggestions.append(dict(handle=h,run_id=source_run,why=why,title=title))
        if len(suggestions)>=MAX_CARDS:
            break
    parts=[CSS,'<div class="bfd"><section class="bfd-panel">',
           '<h2>Friend discovery · FM2</h2>',
           '<p class="bfd-muted">Search a public agent profile by handle and review '
           'Bob’s previously recorded reasons for choosing Scout discussions. '
           'A profile is reported by Moltbook’s API, not proof of real-world identity '
           'or a mutual friendship. There are no follows, messages, posts, votes or '
           'automatic friend additions.</p>',
           '<form method="post" action="/moltbook/discover">'+_hidden("csrf",csrf)+
           _hidden("operation","lookup"),
           '<label>Public agent handle<input name="handle" minlength="2" maxlength="40" '
           'pattern="[A-Za-z0-9][A-Za-z0-9_.-]{1,39}" required '
           'placeholder="AgentName" value="'+e(lookup)+'"></label>',
           '<button type="submit">Look up public profile</button></form>']
    if selected:
        age="Fresh (<24h)" if fresh(selected) else "Stale (refresh before approval)"
        parts += ['<article class="bfd-card"><h3>API-reported profile · @'+
                  e(selected["handle"])+'</h3>',
                  '<p class="bfd-muted">'+e(age)+' · retrieved '+e(selected["fetched_at"])+
                  ' · provider says claimed: '+("yes" if selected["claimed"] else "no/unknown")+'</p>',
                  '<p class="bfd-muted">Karma '+str(selected["karma"])+
                  ' · followers '+str(selected["followers"])+
                  ' · following '+str(selected["following"])+'</p>',
                  '<p class="bfd-preview">'+e(selected["description"])+'</p>',
                  '<p><a href="https://www.moltbook.com/u/'+e(selected["handle"])+
                  '" rel="noreferrer" target="_blank">Open public Moltbook profile</a></p>',
                  '</article>']
    elif lookup:
        parts.append('<p class="bfd-muted">No locally cached profile for that handle. '
                     'Use the lookup button to fetch it.</p>')
    parts += ['</section><section class="bfd-panel"><h2>Bob’s suggested agents</h2>',
              '<p class="bfd-muted">Suggestions originate from the reason Bob saved '
              'while scouting a hash-verified public post. These observations are not '
              'a new live search or factual verification of the author.</p>']
    if not suggestions:
        parts.append('<p class="bfd-muted">No new verified Scout candidates to stage.</p>')
    for item in suggestions:
        parts += ['<article class="bfd-card"><h3>@'+e(item["handle"])+'</h3>',
                  '<p class="bfd-muted">Discussion: '+e(item["title"])+
                  ' · Scout run '+e(item["run_id"])+'</p>',
                  '<p class="bfd-preview">'+e(item["why"] or
                      "Bob selected the discussion without recording a reason.")+'</p>',
                  '<form method="post" action="/moltbook/discover">'+
                  _hidden("csrf",csrf)+_hidden("operation","stage")+
                  _hidden("run_id",item["run_id"])+
                  '<button type="submit">Stage agent for review</button></form>',
                  '</article>']
    parts += ['</section><section class="bfd-panel"><h2>Review pending candidates</h2>',
              '<p class="bfd-muted">A recent matching profile lookup is required '
              'before approval. Rejections do not create a friend entry.</p>']
    if not pending:
        parts.append('<p class="bfd-muted">No pending candidates.</p>')
    for row in pending:
        item=dict(zip(PROPOSAL_COLS,row))
        if not _valid(item,PROPOSAL_COLS):
            continue
        prof=cached(db,item["handle"])
        label="Recent public profile available" if fresh(prof) else "Profile lookup required"
        parts += ['<article class="bfd-card"><h3>@'+e(item["handle"])+'</h3>',
                  '<p class="bfd-muted">'+e(label)+' · source post '+e(item["post_id"])+
                  ' · run '+e(item["run_id"])+'</p>',
                  '<p class="bfd-preview">'+e(item["why"] or item["post_title"])+'</p>',
                  '<p><a class="bfd-link secondary" href="/moltbook/discover?profile='+
                  e(item["handle"])+'">View cached profile</a></p>',
                  _form_review(item,csrf,"approve"),_form_review(item,csrf,"reject"),
                  '</article>']
    parts += ['</section><section class="bfd-panel"><h2>Recent decisions</h2>']
    for row in decided:
        item=dict(zip(PROPOSAL_COLS,row))
        if not _valid(item,PROPOSAL_COLS):
            continue
        parts += ['<article class="bfd-card"><strong>'+e(item["status"])+
                  '</strong> · @'+e(item["handle"])+
                  '<p class="bfd-muted">Reason: '+e(item["reason"])+
                  ' · '+e(item["reviewed_at"])+'</p>']
        if item["friend_id"]:
            parts.append('<p><a href="/moltbook/friends?edit='+e(item["friend_id"])+
                         '">Open saved friend and history</a></p>')
        parts.append('</article>')
    parts += ['</section><p><a href="/moltbook/friends">Friends Manager</a></p></div>']
    return wrap("Moltbook · Discover","".join(parts),"/moltbook/discover")
