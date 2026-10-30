"""FM4.1: private, evidence-linked Moltbook social memory timeline.

Only reads existing sealed friend/Scout/review/focus/publication data. Never
makes network/model calls, starts a worker, follows another agent, modifies
SOUL.md, or writes to the persistent memory or publication database.
"""
from __future__ import annotations

from datetime import datetime,timezone
from html import escape
from pathlib import Path
from urllib.parse import urlencode
import hashlib
import json
import re
import sqlite3

import bob_publish_common as common
import bob_friends as friends
import bob_friend_scout as scout

PAGE=12
MAX_FRIENDS=300
MAX_SCOUT=80
MAX_ROWS=60
MAX_EVENTS=25
MAX_FOCUS=20
MAX_TEXT=320
SORT_KEYS=("observed","interpretation","review","publication","focus","operator")
SOURCE_STATUS=("verified","stored_snapshot","missing")
STYLE="""<style>
.fmt{max-width:1140px;margin:auto;display:grid;gap:12px}
.fmt-panel{border:1px solid #355472;background:linear-gradient(145deg,#152a43,#0c1b2d);
border-radius:13px;padding:clamp(11px,2.2vw,19px);min-width:0}
.fmt-panel h2{font-size:1.07rem;margin:0 0 8px}
.fmt-muted{font-size:.8rem;color:#b0c5dc;line-height:1.48;overflow-wrap:anywhere}
.fmt-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.7fr);gap:12px}
.fmt-form{display:flex;flex-wrap:wrap;gap:9px;align-items:flex-end}
.fmt-form label{display:grid;gap:5px;min-width:0;flex:1 1 190px;font-size:.8rem}
.fmt-form input{min-height:42px;border:1px solid #4b7194;border-radius:8px;
width:100%;background:#0b1a2d;color:#edf6ff;font:inherit;padding:8px}
.fmt-form button{border:1px solid #73a7d5;background:#245b86;color:white;
border-radius:8px;padding:10px 15px;min-height:42px;font:inherit}
.fmt-people{display:grid;gap:6px;margin-top:10px}
.fmt-person{border:1px solid #345573;border-radius:9px;padding:10px;
text-decoration:none;display:block;background:#102238;color:#e4f0ff}
.fmt-person[aria-current=page]{background:#204663;border-color:#76aede}
.fmt-person b{display:block;font-size:.86rem}
.fmt-person small{color:#a8c0d9;font-size:.72rem}
.fmt-pager{display:flex;gap:12px;margin-top:12px;font-size:.8rem}
.fmt-event{border:1px solid #345473;background:#102237;border-radius:10px;
padding:11px 12px;margin:8px 0;min-width:0}
.fmt-top{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center}
.fmt-label{font-size:.72rem;color:#b9dbf5;font-weight:700}
.fmt-badge{border-radius:999px;font-size:.68rem;background:#28445e;color:#cce7fb;padding:4px 8px}
.fmt-badge[data-trust=review]{background:#194738;color:#b9edda}
.fmt-badge[data-trust=interpretation]{background:#453c2a;color:#f2ddb0}
.fmt-event h3{font-size:.91rem;margin:8px 0 4px}
.fmt-event p{font-size:.8rem;line-height:1.46;margin:6px 0;overflow-wrap:anywhere}
.fmt-evidence{font-size:.73rem;color:#abc2d9;overflow-wrap:anywhere}
.fmt-links{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
.fmt-links a{font-size:.8rem}
.fmt :is(button,input,a):focus-visible{outline:2px solid #f5d48c;outline-offset:2px}
@media(max-width:750px){.fmt-grid{grid-template-columns:1fr}.fmt-panel{padding:11px}}
</style>"""


def e(x):
    return escape(str(x if x is not None else ""),quote=True)


def _when(value):
    if not isinstance(value,str):
        return ""
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        if dt.tzinfo is None:
            return ""
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (ValueError,OverflowError):
        return ""


def _present(kind,title,detail,when,source,trust,ref="",status="verified"):
    """Output only fixed, bounded labels, not DB body or arbitrary error text."""
    return {"kind":kind,"title":title[:100],"detail":detail[:MAX_TEXT],
            "when":_when(when),"source":source[:80],"trust":trust,
            "ref":ref if re.fullmatch(r"[0-9a-f]{24}|\d{8}T\d{6}Z",ref or "") else "",
            "status":status}


def _available(db,name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                      (name,)).fetchone() is not None


def _friends(db):
    if not _available(db,"bob_friends"):
        return []
    rows=db.execute("SELECT "+",".join(friends.COLS)+" FROM bob_friends "
                    "ORDER BY handle_key LIMIT ?",(MAX_FRIENDS,)).fetchall()
    out=[]
    for row in rows:
        item=dict(zip(friends.COLS,row))
        try:
            if (friends.ID.fullmatch(item["id"]) and
                item["state"] in friends.STATES and
                item["handle_key"]==item["handle"].casefold() and
                item["sha256"]==friends.seal(item)):
                out.append(item)
        except (TypeError,ValueError,KeyError):
            pass
    return out


def _choice(rid,handle):
    """Reverify saved source/author, not a claimed live identity or friendship."""
    if not isinstance(rid,str) or not common.RUN_ID.fullmatch(rid):
        return None
    result=common.DATA/("scout-result-"+rid+".json")
    feed=common.DATA/("scout-feed-"+rid+".json")
    try:
        if (result.is_symlink() or feed.is_symlink() or
            not result.is_file() or not feed.is_file() or
            result.stat().st_size>1024*1024 or feed.stat().st_size>512*1024):
            return None
        rec=common.load_record(rid)
        if not isinstance(rec,dict):
            return None
        author,verified,pid=friends._source_author(rid)
        if verified!=rid or author.casefold()!=handle.casefold():
            return None
        why=rec.get("why")
        if not isinstance(why,str):
            why=""
        raw=feed.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=rec["snapshot_sha256"]:
            return None
        posts=json.loads(raw).get("posts")
        if not isinstance(posts,list):
            return None
        post=next((x for x in posts if isinstance(x,dict)
                   and x.get("id")==pid and x.get("author")==author),None)
        if post is None:
            return None
        title=post.get("title")
        if not isinstance(title,str):
            title=""
        return {"run_id":rid,"post_id":pid,"sha":rec["snapshot_sha256"],
                "title":title[:160],"why":why.strip()[:320],
                "approval_sha":rec.get("approval_sha256","")}
    except (OSError,ValueError,TypeError,KeyError,AttributeError,StopIteration):
        return None


def _safe_rows(db,table,cols,order="updated_at",limit=MAX_ROWS,where="",args=()):
    if not _available(db,table):
        return []
    return [dict(zip(cols,row)) for row in db.execute(
        "SELECT "+",".join(cols)+" FROM "+table+where+" ORDER BY "+
        order+" DESC LIMIT ?",tuple(args)+(limit,)).fetchall()]


def timeline(db,friend,*,choice=_choice):
    """Collect at most 25 per-agent facts, with no private friend-note fields."""
    fid=friend["id"]
    h=friend["handle"]
    items=[]
    source_cache={}
    def verified(rid):
        if rid not in source_cache:
            source_cache[rid]=choice(rid,h)
        return source_cache[rid]
    # Current FM1 operator record is private metadata, not proof of a
    # reciprocal/platform relationship. Its notes/interests never leave DB.
    items.append(_present("operator","Local directory entry",
        "Operator label: "+friend["relationship"]+". This is not a Moltbook follow or mutual friendship.",
        friend["updated_at"],"FM1 sealed directory","operator",fid))
    # Actual chosen post and WHY: both must still match the saved sealed feed.
    seen=set()
    for path in sorted(common.DATA.glob("scout-result-*.json"),reverse=True)[:MAX_SCOUT]:
        rid=path.name.removeprefix("scout-result-").removesuffix(".json")
        rec=verified(rid)
        if not rec or rid in seen:
            continue
        seen.add(rid)
        dt=datetime.strptime(rid,"%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc).isoformat()
        items.append(_present("observed","Selected a public discussion",
            ("Post: "+rec["title"] if rec["title"] else "Saved chosen public post")+
            (". WHY: "+rec["why"] if rec["why"] else
             ". No saved explanation of why it was selected."),
            dt,"Verified Scout feed + chosen post","observed",rid))
    # FM3.2a copied WHY proposal, with separate owner decision state.
    for item in _safe_rows(db,"bob_friend_interest_proposals",scout.INTEREST_COLS,
                           where=" WHERE friend_id=?",args=(fid,)):
        if not scout.interest_valid(item) or item["handle"].casefold()!=h.casefold():
            continue
        rec=verified(item["run_id"])
        valid=bool(rec and rec["post_id"]==item["post_id"] and
                   rec["why"]==item["idea"] and
                   item["status"] in scout.INTEREST_STATES)
        label=("Owner-reviewed" if item["status"]!="pending" else "Tentative")
        items.append(_present("review",label+" saved Scout interest",
            (item["idea"] if valid else
             "Original saved source missing or altered; proposal text withheld."),
            item["updated_at"],"FM3.2a verified owner-review record",
            "review" if item["status"]!="pending" else "interpretation",
            item["id"],"verified" if valid else "missing"))
    # FM3.2c optional AI-generated inference, never a factual assertion.
    for item in _safe_rows(db,"bob_friend_ai_proposals",scout.AI_PROP_COLS,
                           where=" WHERE friend_id=?",args=(fid,)):
        if not scout._ai_valid(item) or item["handle"].casefold()!=h.casefold():
            continue
        rec=verified(item["run_id"])
        valid=bool(rec and rec["post_id"]==item["post_id"] and
                   rec["sha"]==item["snapshot_sha"])
        text=("Tentative: "+item["idea"][:180]+". Uncertainty: "+
              item["uncertainty"][:100] if valid else
              "Original saved source missing or changed; model text withheld.")
        items.append(_present("interpretation",
            "Local model proposal · "+item["status"],text,
            item["updated_at"],"FM3.2c sealed, source-linked local proposal",
            "review" if item["status"]!="pending" else "interpretation",
            item["id"],"verified" if valid else "missing"))
    # FM3.2d manual profile/post inspection is a sealed local snapshot,
    # not proof of a live account or conversation.
    for item in _safe_rows(db,"bob_friend_focus_jobs",scout.FOCUS_COLS,
                           limit=MAX_FOCUS,where=" WHERE friend_id=?",args=(fid,)):
        if not scout.focus_valid(item) or item["handle"].casefold()!=h.casefold():
            continue
        if item["status"]!="completed" or not item["result_json"]:
            continue
        try:
            data=json.loads(item["result_json"])
            if (not isinstance(data,dict) or
                data.get("handle","").casefold()!=h.casefold() or
                not common.UUID.fullmatch(data.get("agent_id","")) or
                not isinstance(data.get("posts"),list) or
                len(data["posts"])>2):
                continue
            posts=data["posts"]
            if any(not isinstance(x,dict) or not common.UUID.fullmatch(
                    str(x.get("id",""))) for x in posts):
                continue
            items.append(_present("focus","Inspected public profile snapshot",
                str(len(posts))+" matching public post(s) captured. "
                "This is a stored, non-live snapshot, not an interaction.",
                item["updated_at"],"FM3.2d sealed public-focus snapshot",
                "observed",item["id"],"stored_snapshot"))
            if item["idea_json"]:
                idea=json.loads(item["idea_json"])
                if isinstance(idea,dict) and isinstance(idea.get("interest"),str):
                    items.append(_present("interpretation",
                        "Public-focus reaction · "+item["review_status"],
                        "Tentative interpretation: "+idea["interest"][:180],
                        item["updated_at"],"FM3.2d sealed local reaction",
                        "review" if item["review_status"] in ("approved","rejected") else
                        "interpretation",item["id"],"stored_snapshot"))
        except (ValueError,TypeError,KeyError,AttributeError):
            continue
    # A confirmed API result is not proof of reciprocal exchange.
    # Match exactly the original verified chosen author/post/digest.
    for job in _safe_rows(db,"publish_jobs",
                          ("run_id","approval_sha256","post_id","mode","state",
                           "comment_id","updated_at"),limit=MAX_ROWS):
        if job["state"]!="published" or not isinstance(job["comment_id"],str) or (
            not common.UUID.fullmatch(job["comment_id"])):
            continue
        rec=verified(job["run_id"])
        if not rec or (rec["post_id"]!=job["post_id"] or
                       rec["approval_sha"]!=job["approval_sha256"]):
            continue
        items.append(_present("publication","Comment API-acknowledged",
            "Publisher recorded a comment on this agent's selected post. "
            "This does not prove the author replied or that the agents are friends.",
            job["updated_at"],"Saved verified Scout + publisher state",
            "observed",job["run_id"]))
    items.sort(key=lambda r:(r["when"],r["kind"],r["ref"]),reverse=True)
    return items[:MAX_EVENTS]


def snapshot(*,path=common.DB,params=None):
    """Return a capped private immutable response; not used in a public API."""
    params=params or {}
    def one(key,default=""):
        a=params.get(key,[])
        return a[0] if isinstance(a,list) and len(a)==1 and isinstance(a[0],str) else default
    q=one("q").strip()[:64]
    ident=one("agent")
    page=one("page","1")
    page=int(page) if re.fullmatch(r"[1-9][0-9]{0,2}",page) else 1
    path=Path(path)
    empty={"available":False,"people":[],"total":0,"page":1,"pages":1,
           "query":q,"selected":None,"entries":[]}
    if path.is_symlink() or not path.is_file():
        return empty
    try:
        with sqlite3.connect(path.absolute().as_uri()+"?mode=ro",
                             uri=True,timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            people=_friends(db)
            matching=[x for x in people if
                      q.casefold() in x["handle"].casefold() or
                      q.casefold() in x["display_name"].casefold()]
            pages=max(1,(len(matching)+PAGE-1)//PAGE)
            page=min(page,pages)
            start=(page-1)*PAGE
            visible=matching[start:start+PAGE]
            selected=next((x for x in visible if x["id"]==ident),None)
            if selected is None and visible:
                selected=visible[0]
            entries=timeline(db,selected) if selected else []
            # No operator-private notes/interests and no hashes ever returned.
            def safe_friend(x):
                return {"id":x["id"],"handle":x["handle"],
                        "display_name":x["display_name"],"state":x["state"],
                        "relationship":x["relationship"]}
            return {"available":True,"people":[safe_friend(x) for x in visible],
                    "total":len(matching),"page":page,"pages":pages,"query":q,
                    "selected":safe_friend(selected) if selected else None,
                    "entries":entries}
    except (sqlite3.Error,OSError,ValueError,TypeError):
        return empty


def _url(q,page,agent=""):
    return "/moltbook/social-memory?"+urlencode({"q":q,"page":page,
                                               **({"agent":agent} if agent else {})})


def page(wrap,params=None,*,data=None):
    d=data if data is not None else snapshot(params=params)
    parts=[STYLE,'<div class="fmt"><section class="fmt-panel">',
           '<h2>Social Memory · FM4.1</h2>',
           '<p class="fmt-muted">Bob’s private, source-linked history of public '
           'encounters and tentative ideas. A local “friend” is not proof of '
           'Moltbook following, direct contact, or reciprocal friendship. '
           'Read-only: no memory writing, automatic social actions or model calls.</p>',
           '<div class="fmt-links"><a href="/moltbook/friends">Friends Manager</a>',
           '<a href="/moltbook/friend-scout">Friend Scout</a>',
           '<a href="/console">Console</a></div></section>',
           '<div class="fmt-grid"><section class="fmt-panel">',
           '<h2>Agents</h2>',
           '<form method="get" action="/moltbook/social-memory" class="fmt-form">',
           '<label>Search saved handle/name<input name="q" type="search" maxlength="64" value="'+
           e(d["query"])+'"></label><button type="submit">Search</button></form>']
    if not d["available"]:
        parts.append('<p class="fmt-muted">Private Friends database unavailable. '
                     'No relationship or encounter can be verified.</p>')
    else:
        parts.append('<p class="fmt-muted">'+str(d["total"])+' saved matching agent(s) '
                     '· page '+str(d["page"])+' of '+str(d["pages"])+'</p>')
    parts.append('<div class="fmt-people">')
    for person in d["people"]:
        selected=d["selected"] and person["id"]==d["selected"]["id"]
        parts.append('<a class="fmt-person" href="'+e(_url(d["query"],d["page"],person["id"]))+
                     '"'+(' aria-current="page"' if selected else '')+'>'+
                     '<b>@'+e(person["handle"])+'</b><small>'+
                     e(person["state"])+' · operator label: '+
                     e(person["relationship"])+'</small></a>')
    parts.append('</div>')
    if d["page"]>1:
        parts.append('<div class="fmt-pager"><a href="'+
                     e(_url(d["query"],d["page"]-1))+'">Previous</a></div>')
    if d["page"]<d["pages"]:
        parts.append('<div class="fmt-pager"><a href="'+
                     e(_url(d["query"],d["page"]+1))+'">Next</a></div>')
    parts.append('</section><section class="fmt-panel"><h2>Evidence timeline</h2>')
    selected=d["selected"]
    if selected:
        parts += ['<p class="fmt-muted">@'+e(selected["handle"])+
                  ' · local status: '+e(selected["state"])+
                  ' · up to '+str(MAX_EVENTS)+' recent records. Source types '
                  'are labeled separately; public post text is untrusted data.</p>',
                  '<div class="fmt-links"><a href="/moltbook/friends?edit='+
                  e(selected["id"])+'">Edit local friend</a></div>']
    if selected and not d["entries"]:
        parts.append('<p class="fmt-muted">No source-verifiable encounters '
                     'have been recorded yet for this agent.</p>')
    if not selected:
        parts.append('<p class="fmt-muted">Choose a saved agent to inspect '
                     'its private timeline.</p>')
    for item in d["entries"]:
        trust=item["trust"] if item["trust"] in ("observed","operator",
                                                 "interpretation","review") else "observed"
        parts += ['<article class="fmt-event"><div class="fmt-top"><span class="fmt-label">'+
                  e(item["kind"].replace("_"," ").title())+'</span>',
                  '<span class="fmt-badge" data-trust="'+trust+'">'+
                  e({"review":"Owner reviewed","interpretation":"Tentative",
                     "operator":"Owner label","observed":"Observed evidence"}[trust])+
                  '</span></div><h3>'+e(item["title"])+'</h3>',
                  '<p>'+e(item["detail"])+'</p>',
                  '<p class="fmt-evidence">UTC: '+e(item["when"] or "Not recorded")+
                  ' · '+e(item["source"])+' · '+e(item["status"])+
                  '</p></article>']
    parts += ['<p class="fmt-muted">“Observed” means a verified saved source, '
              'not an independently verified identity or an ongoing friendship. '
              'No private notes, approval comments, or credentials appear here.</p>',
              '</section></div></div>']
    return wrap("Social Memory","".join(parts),"/moltbook/social-memory")
