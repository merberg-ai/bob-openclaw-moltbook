"""FM3: explicitly opt-in friend-focused Scout, never an autonomous publisher.

An existing Scout run may read TWO public profiles and ONE public post per
profile using fixed-host anonymous HTTPS GETs. It never follows, comments,
votes, sends private notes to Moltbook, or writes a public publication intent.
Only active, integrity-checked operator-curated FM1 entries can be watched.
"""
from __future__ import annotations

from datetime import datetime,timezone
from html import escape
from http.client import HTTPSConnection
from pathlib import Path
from urllib.parse import urlencode,parse_qs,urlsplit
import hashlib
import hmac
import json
import re
import secrets
import sqlite3

import bob_publish_common as common
import bob_friends as friends
from bob_friend_discovery import HOST, ENDPOINT

SETTING="bob_friend_scout_enabled"
CONFIRM="ENABLE FRIEND SCOUTING"
MAX_FRIENDS=2
MAX_POSTS=2
MAX_TOTAL=6
MAX_RESPONSE=65536
MAX_PREVIEW=10
WATCH_FILTERS=("all","watching","paused","issues")
ERRORS=frozenset(("Invalid friend scouting form","Friend scouting setting changed; reload",
                   "Confirmation phrase does not match",
                   "Friend watch preference changed; reload",
                   "Friend watch preference already selected",
                   "Friend must be active to change watch preference",
                   "Friend watch preference integrity failed",
                   "Invalid interest form","Interest source unavailable or changed",
                   "Interest source is not an active saved friend",
                   "Interest already staged","Interest inbox capacity reached",
                   "Interest changed; reload","Interest record integrity failed",
                   "Interest decision unavailable","Review reason must be 0-240 characters"))
CSS="""<style>
.bfs{max-width:1050px;margin:auto;display:grid;gap:17px}
.bfs-panel{border:1px solid #375575;background:linear-gradient(145deg,#172a40,#111d30);
border-radius:15px;padding:clamp(15px,2.5vw,23px)}
.bfs h2{font-size:1.14rem;margin:0 0 11px}.bfs h3{font-size:1.02rem}
.bfs-muted{color:#b6cadd;font-size:.87rem;line-height:1.55}
.bfs-card{padding:13px;background:#12243a;border:1px solid #3c5473;border-radius:11px;margin:12px 0}
.bfs-tags{font-size:.82rem;color:#b0d2ef}
.bfs label{display:grid;gap:7px;margin:10px 0;font-weight:650}
.bfs-filter{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr) auto;
gap:12px;align-items:end;margin:12px 0}
.bfs-filter button{margin-bottom:10px}
.bfs select{max-width:100%;min-height:44px;width:100%;box-sizing:border-box;
padding:10px;background:#102034;color:#eff6ff;border:1px solid #607d98;
border-radius:9px;font:inherit}
.bfs-links{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:12px 0}
.bfs-links a{color:#b6dcff}
.bfs input{max-width:100%;min-height:44px;width:100%;box-sizing:border-box;
padding:10px;border:1px solid #607d98;background:#102034;color:#eff6ff;border-radius:9px;font:inherit}
.bfs button{border:1px solid #86b4e0;background:#276398;color:#fff;
border-radius:9px;min-height:44px;padding:10px 18px;font:inherit;cursor:pointer;font-weight:700}
.bfs button.secondary{background:#2b3f55}
.bfs button:focus-visible,.bfs input:focus-visible,.bfs select:focus-visible{outline:2px solid #95d3ff;outline-offset:2px}
.bfs-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
@media(max-width:720px){.bfs-grid,.bfs-filter{grid-template-columns:1fr}.bfs button{width:100%}.bfs-filter button{margin-bottom:0}}
</style>"""


def e(x):
    return escape(str(x if x is not None else ""),quote=True)


def enabled(db):
    try:
        row=db.execute("SELECT value FROM publish_settings WHERE name=?",(SETTING,)).fetchone()
        return row is not None and row[0]=="1"
    except sqlite3.Error:
        return False


# FM3.1 preferences live in the EXISTING backed-up private queue DB.
# A missing preference is explicitly "watch on" for backwards compatibility;
# a malformed/tampered stored preference is fail-closed (watch off).
PREF_COLS=("friend_id","enabled","version","updated_at","sha256")


def init_preferences(db):
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friend_watch_prefs (
        friend_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL
            CHECK(enabled IN (0,1)),
        version INTEGER NOT NULL CHECK(version>=1),
        updated_at TEXT NOT NULL, sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friend_watch_history (
        friend_id TEXT NOT NULL, version INTEGER NOT NULL,
        enabled INTEGER NOT NULL, changed_at TEXT NOT NULL,
        PRIMARY KEY(friend_id,version))""")


def pref_seal(row):
    return hashlib.sha256(json.dumps(
        {k:row[k] for k in PREF_COLS if k!="sha256"},
        sort_keys=True,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def pref_valid(item):
    try:
        return (type(item["enabled"]) is int and item["enabled"] in (0,1)
                and type(item["version"]) is int and item["version"]>=1
                and isinstance(item["sha256"],str)
                and hmac.compare_digest(item["sha256"],pref_seal(item)))
    except (KeyError,TypeError,ValueError):
        return False


def _preferences(db):
    """Read-only Scout treats absent table as legacy defaults; corruption
    or an unreadable existing table blocks friend-focused reads.
    """
    try:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                          "AND name='bob_friend_watch_prefs'").fetchone()
        if not exists:
            return {}
        rows=db.execute("SELECT "+",".join(PREF_COLS)+" FROM bob_friend_watch_prefs").fetchall()
        return {row[0]:dict(zip(PREF_COLS,row)) for row in rows}
    except sqlite3.Error:
        return None


def _change_watch(db,form):
    if set(form)!={"csrf","operation","id","friend_sha","watch_sha","watch_enabled"}:
        raise ValueError("Invalid friend scouting form")
    if form["watch_enabled"] not in ("0","1"):
        raise ValueError("Invalid friend scouting form")
    if not isinstance(form["watch_sha"],str):
        raise ValueError("Invalid friend scouting form")
    init_preferences(db)
    friend=friends._get(db,form["id"])
    if friend["state"]!="active":
        raise ValueError("Friend must be active to change watch preference")
    if not isinstance(form["friend_sha"],str) or not hmac.compare_digest(
            friend["sha256"],form["friend_sha"]):
        raise ValueError("Friend watch preference changed; reload")
    row=db.execute("SELECT "+",".join(PREF_COLS)+" FROM bob_friend_watch_prefs "
                   "WHERE friend_id=?",(friend["id"],)).fetchone()
    prev=dict(zip(PREF_COLS,row)) if row else None
    if prev and not pref_valid(prev):
        raise ValueError("Friend watch preference integrity failed")
    expected=prev["sha256"] if prev else "default"
    if not hmac.compare_digest(form["watch_sha"],expected):
        raise ValueError("Friend watch preference changed; reload")
    new=int(form["watch_enabled"])
    if new==(prev["enabled"] if prev else 1):
        raise ValueError("Friend watch preference already selected")
    item=dict(friend_id=friend["id"],enabled=new,
              version=prev["version"]+1 if prev else 1,
              updated_at=common.now())
    item["sha256"]=pref_seal(item)
    if prev:
        cur=db.execute("UPDATE bob_friend_watch_prefs SET enabled=?,version=?,"
                       "updated_at=?,sha256=? WHERE friend_id=? AND sha256=?",
                       (new,item["version"],item["updated_at"],item["sha256"],
                        friend["id"],prev["sha256"]))
        if cur.rowcount!=1:
            raise ValueError("Friend watch preference changed; reload")
    else:
        try:
            db.execute("INSERT INTO bob_friend_watch_prefs("+",".join(PREF_COLS)+") "
                       "VALUES(?,?,?,?,?)",tuple(item[k] for k in PREF_COLS))
        except sqlite3.IntegrityError:
            raise ValueError("Friend watch preference changed; reload") from None
    db.execute("INSERT INTO bob_friend_watch_history"
               "(friend_id,version,enabled,changed_at) VALUES(?,?,?,?)",
               (friend["id"],item["version"],new,item["updated_at"]))
    common.event(db,"bob_friend_watch_changed",
                 friend["id"]+" "+("enabled" if new else "disabled"))
    return str(new)


def change(db,form):
    """Called after existing Activity Manager auth, Origin and CSRF checks."""
    if form.get("operation")=="watch":
        return _change_watch(db,form)
    if form.get("operation")=="interest_stage":
        return _interest_stage(db,form)
    if form.get("operation")=="interest_review":
        return _interest_review(db,form)
    if set(form)!={"csrf","enabled","expected","confirmation"}:
        raise ValueError("Invalid friend scouting form")
    new,expected=form["enabled"],form["expected"]
    if new not in ("0","1") or expected not in ("0","1"):
        raise ValueError("Invalid friend scouting form")
    current="1" if enabled(db) else "0"
    if new==current or expected!=current:
        raise ValueError("Friend scouting setting changed; reload")
    if (new=="1" and form["confirmation"]!=CONFIRM or
        new=="0" and form["confirmation"]!=""):
        raise ValueError("Confirmation phrase does not match")
    db.execute("INSERT INTO publish_settings(name,value) VALUES(?,?) "
               "ON CONFLICT(name) DO UPDATE SET value=excluded.value",(SETTING,new))
    common.event(db,"bob_friend_scout_setting","enabled" if new=="1" else "disabled")
    return new



# FM3.2a: operator-staged, source-verified observations for private review.
# The idea is copied from Bob's EXISTING saved WHY, not fresh model inference,
# a factual assertion about an agent, a trusted instruction, or PM2 memory.
INTEREST_COLS=("id","friend_id","run_id","post_id","handle","idea","status",
               "created_at","updated_at","review_reason","version","sha256")
INTEREST_CAP=60
INTEREST_STATES=("pending","approved","rejected","archived")


def init_interests(db):
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friend_interest_proposals (
        id TEXT PRIMARY KEY, friend_id TEXT NOT NULL,
        run_id TEXT NOT NULL UNIQUE, post_id TEXT NOT NULL,
        handle TEXT NOT NULL, idea TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','archived')),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        review_reason TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>=1),
        sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friend_interest_history (
        id TEXT NOT NULL, version INTEGER NOT NULL, saved_at TEXT NOT NULL,
        action TEXT NOT NULL, snapshot_json TEXT NOT NULL,
        PRIMARY KEY(id,version))""")
    db.execute("CREATE INDEX IF NOT EXISTS bob_friend_interest_status_idx "
               "ON bob_friend_interest_proposals(status,created_at)")


def interest_seal(item):
    return hashlib.sha256(json.dumps(
        {k:item[k] for k in INTEREST_COLS if k!="sha256"},
        ensure_ascii=False,sort_keys=True,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def interest_valid(item):
    try:
        return (isinstance(item["sha256"],str) and
                hmac.compare_digest(item["sha256"],interest_seal(item))
                and item["status"] in INTEREST_STATES
                and type(item["version"]) is int and item["version"]>=1)
    except (KeyError,TypeError,ValueError):
        return False


def _interest_source(run_id):
    # Recheck the exact local chosen post and snapshot hash at every
    # stage/approval. Never accept an author, idea or URL from POST data.
    try:
        author,verified_run,pid=friends._source_author(run_id)
        rec=common.load_record(verified_run)
        why=rec.get("why") if isinstance(rec,dict) else None
        if not isinstance(why,str) or not why.strip():
            raise ValueError
        idea=why.strip()[:320]
        if any(ord(c)<32 and c not in "\n\t" for c in idea):
            raise ValueError
        return author,pid,idea
    except (ValueError,TypeError,OSError,AttributeError,KeyError):
        raise ValueError("Interest source unavailable or changed") from None


def _interest_get(db,ident):
    if not isinstance(ident,str) or not friends.ID.fullmatch(ident):
        raise ValueError("Invalid interest form")
    row=db.execute("SELECT "+",".join(INTEREST_COLS)+
                   " FROM bob_friend_interest_proposals WHERE id=?",(ident,)).fetchone()
    if not row:
        raise ValueError("Invalid interest form")
    item=dict(zip(INTEREST_COLS,row))
    if not interest_valid(item):
        raise ValueError("Interest record integrity failed")
    return item


def _interest_history(db,item,action):
    db.execute("INSERT INTO bob_friend_interest_history"
               "(id,version,saved_at,action,snapshot_json) VALUES(?,?,?,?,?)",
               (item["id"],item["version"],item["updated_at"],action,
                json.dumps(item,ensure_ascii=False,sort_keys=True)))


def _interest_stage(db,form):
    if set(form)!={"csrf","operation","friend_id","friend_sha","run_id","post_id"}:
        raise ValueError("Invalid interest form")
    init_interests(db)
    friend=friends._get(db,form["friend_id"])
    if friend["state"]!="active" or not hmac.compare_digest(
            friend["sha256"],form["friend_sha"]):
        raise ValueError("Interest source is not an active saved friend")
    author,pid,idea=_interest_source(form["run_id"])
    if (pid!=form["post_id"] or
        author.casefold()!=friend["handle_key"]):
        raise ValueError("Interest source unavailable or changed")
    if db.execute("SELECT 1 FROM bob_friend_interest_proposals WHERE run_id=?",
                  (form["run_id"],)).fetchone():
        raise ValueError("Interest already staged")
    if db.execute("SELECT count(*) FROM bob_friend_interest_proposals").fetchone()[0]>=INTEREST_CAP:
        raise ValueError("Interest inbox capacity reached")
    t=common.now()
    item=dict(id=secrets.token_hex(12),friend_id=friend["id"],
              run_id=form["run_id"],post_id=pid,handle=friend["handle"],
              idea=idea,status="pending",created_at=t,updated_at=t,
              review_reason="",version=1)
    item["sha256"]=interest_seal(item)
    try:
        db.execute("INSERT INTO bob_friend_interest_proposals("+",".join(INTEREST_COLS)+") "
                   "VALUES("+",".join("?" for _ in INTEREST_COLS)+")",
                   tuple(item[k] for k in INTEREST_COLS))
    except sqlite3.IntegrityError:
        raise ValueError("Interest already staged") from None
    _interest_history(db,item,"stage")
    common.event(db,"bob_friend_interest_staged",item["id"])
    return item["id"]


def _interest_review(db,form):
    if set(form)!={"csrf","operation","id","expected_sha","decision","reason"}:
        raise ValueError("Invalid interest form")
    reason=form["reason"]
    if (not isinstance(reason,str) or len(reason)>240 or
        any(ord(c)<32 for c in reason)):
        raise ValueError("Review reason must be 0-240 characters")
    decision=form["decision"]
    if decision not in ("approve","reject","reopen","archive"):
        raise ValueError("Invalid interest form")
    init_interests(db)
    item=_interest_get(db,form["id"])
    if not isinstance(form["expected_sha"],str) or not hmac.compare_digest(
            item["sha256"],form["expected_sha"]):
        raise ValueError("Interest changed; reload")
    target={"approve":"approved","reject":"rejected",
            "reopen":"pending","archive":"archived"}[decision]
    allowed={"pending":("approve","reject","archive"),
             "approved":("reopen","archive"),"rejected":("reopen","archive"),
             "archived":("reopen",)}
    if decision not in allowed[item["status"]]:
        raise ValueError("Interest decision unavailable")
    if decision in ("approve","reopen"):
        author,pid,idea=_interest_source(item["run_id"])
        friend=friends._get(db,item["friend_id"])
        if (friend["state"]!="active" or author.casefold()!=friend["handle_key"]
            or friend["handle"]!=item["handle"] or pid!=item["post_id"]
            or idea!=item["idea"]):
            raise ValueError("Interest source unavailable or changed")
    previous=item["sha256"]
    item.update(status=target,updated_at=common.now(),
                review_reason=reason.strip(),version=item["version"]+1)
    item["sha256"]=interest_seal(item)
    cur=db.execute("UPDATE bob_friend_interest_proposals "
                   "SET status=?,updated_at=?,review_reason=?,version=?,sha256=? "
                   "WHERE id=? AND sha256=?",
                   (target,item["updated_at"],item["review_reason"],item["version"],
                    item["sha256"],item["id"],previous))
    if cur.rowcount!=1:
        raise ValueError("Interest changed; reload")
    _interest_history(db,item,decision)
    common.event(db,"bob_friend_interest_reviewed",item["id"]+" "+decision)
    return target


def interest_rows(db):
    init_interests(db)
    rows=db.execute("SELECT "+",".join(INTEREST_COLS)+
                    " FROM bob_friend_interest_proposals "
                    "ORDER BY created_at DESC,id DESC LIMIT ?",(INTEREST_CAP,)).fetchall()
    return [item for row in rows if interest_valid(
        item:=dict(zip(INTEREST_COLS,row)))]


def _watch(db,*,include_disabled=False):
    prefs=_preferences(db)
    if prefs is None:
        return []  # Pref table exists but is unreadable: fail closed.
    try:
        rows=db.execute("SELECT "+",".join(friends.COLS)+
                        " FROM bob_friends WHERE state='active' "
                        "ORDER BY updated_at DESC,id DESC LIMIT 300").fetchall()
    except sqlite3.Error:
        return []
    result=[]
    for row in rows:
        item=dict(zip(friends.COLS,row))
        try:
            if (item["state"]=="active" and item["relationship"] in friends.RELATIONS
                and isinstance(item["sha256"],str)
                and hmac.compare_digest(item["sha256"],friends.seal(item))
                and item["handle_key"]==friends.handle(item["handle"]).casefold()):
                pref=prefs.get(item["id"])
                valid=pref is None or pref_valid(pref)
                item["watch_enabled"]=(pref["enabled"]==1 if pref else True) if valid else False
                item["watch_sha"]=(pref["sha256"] if pref and valid else
                                   "default" if pref is None else "")
                item["watch_problem"]=not valid
                if include_disabled or item["watch_enabled"]:
                    result.append(item)
        except (TypeError,ValueError,KeyError):
            continue
    # A friend is eligible for selection ONLY when active and watched.
    weight={"friend":0,"interesting":1,"acquaintance":2}
    return sorted(result,key=lambda f:(weight[f["relationship"]],f["handle_key"]))


def _readonly_watch(db_path):
    db_path=Path(db_path)
    if db_path.is_symlink() or not db_path.is_file():
        return []
    try:
        with sqlite3.connect(db_path.absolute().as_uri()+"?mode=ro",uri=True,timeout=2) as db:
            db.execute("PRAGMA query_only=ON")
            if not enabled(db):
                return []
            return _watch(db)
    except (sqlite3.Error,OSError,ValueError):
        return []


def selected_watch(db_path=None,*,date=None):
    """At most two names, rotated across dates within each relationship tier."""
    all_watch=_readonly_watch(db_path if db_path is not None else common.DB)
    if not all_watch:
        return []
    date=date or datetime.now(timezone.utc).date()
    # Rotate within priority groups so a large friends list is not starved.
    preferred=[i for i in all_watch if i["relationship"]=="friend"]
    first_pool=preferred or [i for i in all_watch if i["relationship"]=="interesting"]
    if not first_pool:
        first_pool=all_watch
    first=first_pool[date.toordinal()%len(first_pool)]
    remaining=[i for i in all_watch if i["id"]!=first["id"]]
    if not remaining:
        return [first]
    # Second slot rotates through the remaining active friends to avoid
    # starving interesting agents behind a large favorite-friends list.
    second=remaining[date.toordinal()%len(remaining)]
    return [first,second]


def _json_get(path,*,connection_cls=HTTPSConnection):
    """Fixed origin, GET only, no redirects/credentials; bounded response."""
    con=connection_cls(HOST,timeout=8)
    try:
        con.request("GET",path,headers={"Accept":"application/json",
                    "User-Agent":"Bob-Friend-Scout/0.7.4"})
        response=con.getresponse()
        if response.status!=200:
            return None
        raw=response.read(MAX_RESPONSE+1)
        if len(raw)>MAX_RESPONSE:
            return None
        value=json.loads(raw)
        return value if isinstance(value,dict) and value.get("success") is True else None
    except (OSError,TimeoutError,UnicodeError,ValueError,TypeError):
        return None
    finally:
        con.close()


def profile_posts(agent,*,getter=_json_get):
    """Never trust profile post bodies, author names or URLs as authoritative."""
    handle=friends.handle(agent["handle"])
    envelope=getter(ENDPOINT+"?"+urlencode({"name":handle}))
    if not isinstance(envelope,dict) or envelope.get("success") is not True:
        return []
    identity=envelope.get("agent")
    name=identity.get("name") if isinstance(identity,dict) else None
    if not isinstance(name,str) or name.casefold()!=handle.casefold():
        return []
    agent_id=identity.get("id")
    if not isinstance(agent_id,str) or not common.UUID.fullmatch(agent_id):
        return []
    recent=envelope.get("recentPosts",identity.get("recentPosts",[]))
    if not isinstance(recent,list):
        return []
    out=[]
    for post in recent[:12]:
        if not isinstance(post,dict):
            continue
        pid=post.get("id")
        if isinstance(pid,str) and common.UUID.fullmatch(pid):
            out.append((pid,agent_id))
    return out


def read_friend_posts(watch,already_seen,*,getter=_json_get):
    """One full post per eligible friend, two requests to each API kind max.

    Candidate author MUST match the trusted handle from the user's private
    directory AND the queried profile UUID if an author UUID is present.
    All posts are still untrusted data for Bob's existing no-tools prompt.
    """
    output=[]
    for agent in watch[:MAX_FRIENDS]:
        try:
            options=profile_posts(agent,getter=getter)
        except (TypeError,ValueError):
            continue
        for pid,aid in options:
            if pid in already_seen or any(x["id"]==pid for x in output):
                continue
            obj=getter("/api/v1/posts/"+pid)
            if not obj:
                break  # at most one post fetch per profile
            post=obj.get("post")
            if not isinstance(post,dict) or post.get("id")!=pid:
                break
            author=post.get("author")
            if not isinstance(author,dict):
                break
            username=author.get("name")
            if not isinstance(username,str) or username.casefold()!=agent["handle_key"]:
                break
            author_id=author.get("id")
            if author_id is not None and author_id!=aid:
                break
            title=post.get("title")
            body=post.get("content")
            if (not isinstance(title,str) or not isinstance(body,str)
                or not body.strip() or len(body)>40000):
                break
            output.append({"id":pid,"title":title[:200],
                           "author":agent["handle"],"content":body[:1800],
                           "from_friend":True})
            break
    return output[:MAX_POSTS]


def enrich(posts,seen,*,db_path=None,getter=_json_get,date=None,diagnostics=None):
    """Returns existing global posts untouched unless owner explicitly opted in.

    If friend posts are obtained, reserve FOUR positions for the normal global
    feed; do not allow friendships to dominate every scout decision.
    """
    watch=selected_watch(db_path,date=date)
    if diagnostics is not None:
        diagnostics["state"]="no_eligible_active_friends" if not watch else "no_verified_public_posts"
    if not watch:
        return posts[:MAX_TOTAL],0
    try:
        friend_posts=read_friend_posts(watch,set(seen),getter=getter)
    except (ValueError,TypeError,OSError,AttributeError,KeyError):
        friend_posts=[]
    if not friend_posts:
        return posts[:MAX_TOTAL],0
    if diagnostics is not None:
        diagnostics["state"]="friend_posts_included"
    existing={p["id"] for p in friend_posts}
    global_posts=[p for p in posts if isinstance(p,dict) and p.get("id") not in existing]
    # Four normal slots, two prioritized friend slots.
    selected=global_posts[:MAX_TOTAL-len(friend_posts)]+friend_posts
    return selected[:MAX_TOTAL],len(friend_posts)


def allow_auto_candidate(db,rec):
    """Fail closed for friend-targeted posts, regardless of how they were found.

    Called both before automatic queue insertion and immediately before an
    already-queued automatic publication is sent. A valid Scout record alone
    does NOT authorize posting to a saved friend.
    """
    if not isinstance(rec,dict) or rec.get("friend_focus") is True:
        return False
    rid=rec.get("run_id")
    if not isinstance(rid,str) or not common.RUN_ID.fullmatch(rid):
        return False
    try:
        path=common.DATA/("scout-feed-"+rid+".json")
        if path.is_symlink() or not path.is_file() or path.stat().st_size>512*1024:
            return False
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=rec.get("snapshot_sha256"):
            return False
        snapshot=json.loads(raw)
        if not isinstance(snapshot,dict) or snapshot.get("friend_focus") is True:
            return False
        posts=snapshot.get("posts")
        if not isinstance(posts,list) or any(
            isinstance(p,dict) and p.get("from_friend") is True for p in posts):
            return False
        selected=next((p for p in posts if isinstance(p,dict) and
                       p.get("id")==rec.get("chosen_post_id")),None)
        if not isinstance(selected,dict):
            return False
        author=selected.get("author")
        if not isinstance(author,str):
            return False
        # FM1's private table may not exist on fresh hosts. A damaged table,
        # however, must not grant an unintended auto-publication permission.
        exists=db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bob_friends'"
        ).fetchone()
        if exists and db.execute(
            "SELECT 1 FROM bob_friends WHERE handle_key=?",(author.casefold(),)
        ).fetchone():
            return False
        return True
    except (OSError,sqlite3.Error,TypeError,ValueError,KeyError):
        return False


def guarded_auto_candidates(db,max_count=10):
    """FM3 substitute for the legacy unmanaged auto_candidates helper.

    Preserves the existing exact queue schema, age and human-decision gates,
    but never auto-queues any saved friend or friend-tagged Scout batch.
    """
    if common.setting(db,"auto_enabled","0")!="1":
        return 0
    since=common.setting(db,"auto_since","")
    if not since:
        return 0
    count=0
    for path in sorted(common.DATA.glob("scout-result-*.json")):
        rid=path.name.removeprefix("scout-result-").removesuffix(".json")
        obj=common.load_record(rid)
        if obj is None or not allow_auto_candidate(db,obj):
            continue
        try:
            from datetime import timedelta
            created=datetime.strptime(rid,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            if created.isoformat()<=since:
                continue
        except ValueError:
            continue
        if db.execute("SELECT 1 FROM decisions WHERE run_id=?",(rid,)).fetchone():
            continue
        if db.execute("SELECT 1 FROM publish_jobs WHERE run_id=?",(rid,)).fetchone():
            continue
        t=common.now()
        db.execute(
            "INSERT INTO publish_jobs(run_id,approval_sha256,post_id,draft_comment,"
            "mode,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (rid,obj["approval_sha256"],obj["chosen_post_id"],obj["draft_comment"],
             "auto","queued",t,t))
        common.event(db,"auto_queued",f"{rid} new validated draft queued")
        count+=1
        if count>=max_count:
            break
    return count


def friend_observations(records,active,*,loader=None):
    """Read-only selected discussion history with verified Scout provenance.

    These are Bob's actual previous WHY rationales, not new AI generations,
    independent opinions, verified identities or proof of a friendship.
    """
    known={f["handle_key"]:f for f in active}
    entries=[]
    counts={}
    for item in (records or [])[:100]:
        if not isinstance(item,dict):
            continue
        rid=item.get("run_id")
        if not isinstance(rid,str) or not common.RUN_ID.fullmatch(rid):
            continue
        rec=(loader or common.load_record)(rid)
        if not isinstance(rec,dict) or rec.get("run_id")!=rid:
            continue
        why=rec.get("why")
        title=rec.get("chosen_title")
        if not isinstance(why,str) or not why.strip():
            continue
        if not isinstance(title,str):
            title=""
        try:
            author,verified_id,pid=friends._source_author(rid,loader=loader)
        except (ValueError,TypeError,OSError):
            continue
        friend=known.get(author.casefold())
        if not friend or counts.get(friend["id"],0)>=3:
            continue
        counts[friend["id"]]=counts.get(friend["id"],0)+1
        entries.append(dict(handle=friend["handle"],id=friend["id"],
                            friend_sha=friend["sha256"],
                            run_id=rid,post_id=pid,title=title[:160],
                            why=why.strip()[:320]))
        if len(entries)>=10:
            break
    return entries



# FM3.2b is a read-only view of the existing sealed private directory and
# saved Scout evidence. Query strings are display controls, not permissions.
def _filter_params(params):
    def one(key):
        values=params.get(key,[]) if isinstance(params,dict) else []
        return values[0] if isinstance(values,list) and len(values)==1 and isinstance(values[0],str) else ""
    search=one("q").strip()[:64]
    show=one("show")
    show=show if show in WATCH_FILTERS else "all"
    raw=one("page")
    number=int(raw) if re.fullmatch(r"[1-9][0-9]{0,2}",raw) else 1
    return search,show,number


def watchlist_location(request_path):
    """Canonical same-origin redirect preserving only bounded view controls."""
    try:
        parsed=urlsplit(request_path)
        if parsed.path!="/moltbook/friend-scout":
            return "/moltbook/friend-scout"
        values=parse_qs(parsed.query[:256],keep_blank_values=True,max_num_fields=3)
        search,show,number=_filter_params(values)
    except (ValueError,TypeError,AttributeError):
        return "/moltbook/friend-scout"
    return "/moltbook/friend-scout?"+urlencode(
        {"q":search,"show":show,"page":number})


def friend_activity(records,active,*,loader=None):
    """Evidence only, not live activity or inferred trust.

    "Observed" is a verified saved friend-focused post marker, not merely
    a profile lookup or social interaction. "Selected" is a verified saved
    chosen author/post, even when encountered in the normal global feed.
    No source => no timestamp. At most the newest 100 saved Scout reports.
    """
    known={f["handle_key"]:f["id"] for f in active}
    output={}
    for item in (records or [])[:100]:
        rid=item.get("run_id") if isinstance(item,dict) else None
        if not isinstance(rid,str) or not common.RUN_ID.fullmatch(rid):
            continue
        try:
            when=datetime.strptime(rid,"%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            rec=(loader or common.load_record)(rid)
            if not isinstance(rec,dict) or rec.get("run_id")!=rid:
                continue
            path=common.DATA/("scout-feed-"+rid+".json")
            if (path.is_symlink() or not path.is_file() or
                path.stat().st_size>512*1024):
                continue
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=rec.get("snapshot_sha256"):
                continue
            feed=json.loads(raw)
            posts=feed.get("posts") if isinstance(feed,dict) else None
            if not isinstance(posts,list):
                continue
            stamp=when.strftime("%Y-%m-%d %H:%M UTC")
            for post in posts[:MAX_TOTAL]:
                if not isinstance(post,dict):
                    continue
                author=post.get("author")
                pid=post.get("id")
                if (not isinstance(author,str) or not isinstance(pid,str) or
                    not common.UUID.fullmatch(pid)):
                    continue
                ident=known.get(author.casefold())
                if ident is None:
                    continue
                state=output.setdefault(ident,{})
                if post.get("from_friend") is True and rid>state.get("observed_run",""):
                    state.update(observed_run=rid,observed_at=stamp)
                if (pid==rec.get("chosen_post_id") and
                    author==rec.get("chosen_author") and rid>state.get("selected_run","")):
                    state.update(selected_run=rid,selected_at=stamp)
        except (OSError,TypeError,ValueError,KeyError,AttributeError):
            continue
    return output


def page(db,csrf,wrap,records,params=None):
    init_preferences(db)
    on=enabled(db)
    active=_watch(db,include_disabled=True)
    watching=[item for item in active if item["watch_enabled"]]
    observations=friend_observations(records,active)
    interest_items=interest_rows(db)
    staged_runs={item["run_id"] for item in interest_items}
    weight={"friend":0,"interesting":1,"acquaintance":2}
    ordered=sorted(active,key=lambda x:(weight[x["relationship"]],x["handle_key"]))
    search,show,number=_filter_params(params)
    query=search.casefold()
    matching=[item for item in ordered if
              (not query or query in item["handle"].casefold()
               or query in item["display_name"].casefold()) and
              (show=="all" or
               show=="watching" and item["watch_enabled"] or
               show=="paused" and not item["watch_enabled"] and not item["watch_problem"] or
               show=="issues" and item["watch_problem"])]
    total=len(matching)
    pages=max(1,(total+MAX_PREVIEW-1)//MAX_PREVIEW)
    number=min(number,pages)
    visible=matching[(number-1)*MAX_PREVIEW:number*MAX_PREVIEW]
    def watch_uri(n):
        return watchlist_location("/moltbook/friend-scout?"+urlencode(
            {"q":search,"show":show,"page":n}))
    action=watch_uri(number)
    activity=friend_activity(records,active)
    recent=[]
    for rec in (records or [])[:80]:
        if (isinstance(rec,dict) and rec.get("friend_scan_status") in
            ("friend_posts_included","no_verified_public_posts","no_eligible_active_friends","replayed_friend_snapshot")
            and common.load_record(rec.get("run_id"))):
            recent.append(rec)
            if len(recent)>=6:
                break
    parts=[CSS,'<div class="bfs"><section class="bfs-panel"><h2>Friend-focused Scout · FM3</h2>',
           '<p class="bfs-muted">The existing scheduled Scout may optionally read up to '
           '2 active friends’ public profiles and 1 verified public post each, '
           'mixing them with at least 4 global discussions. Bob chooses freely '
           'among the resulting real posts. NO platform following or messaging.</p>',
           '<p class="bfs-muted"><strong>Status: '+("Enabled" if on else "Disabled")+
           '</strong> · '+str(len(watching))+' watched / '+str(len(active))+
           ' active verified friends. Muted and archived entries are never scanned.</p>',
           '<p class="bfs-muted"><strong>Publication boundary:</strong> friend-focused '
           'Scout batches are never eligible for automatic comment queueing, '
           'even if global auto-comments are enabled. You must explicitly '
           'review and queue any generated friend-focused reply.</p>',
           '<form method="post" action="/moltbook/friend-scout">',
           '<input type="hidden" name="csrf" value="'+e(csrf)+'">',
           '<input type="hidden" name="expected" value="'+("1" if on else "0")+'">',
           '<input type="hidden" name="enabled" value="'+("0" if on else "1")+'">']
    if on:
        parts += ['<input type="hidden" name="confirmation" value="">',
                  '<button type="submit" class="secondary">Disable friend scouting</button>']
    else:
        parts += ['<label>Type '+CONFIRM+' to enable'
                  '<input name="confirmation" required maxlength="40" autocomplete="off" '
                  'placeholder="'+CONFIRM+'"></label>',
                  '<button type="submit">Enable friend scouting</button>']
    parts += ['</form></section><section class="bfs-panel"><h2>Individual friend watch preferences · FM3.1</h2>',
              '<p class="bfs-muted">Watch is ON by default for existing active friends. '
              'Pause one agent without muting or archiving the friendship. '
              'Changes affect only the next Scout run and are recorded locally. '
              'No follows, posting permissions or private notes are sent to Moltbook. '
              'Bob still chooses which discussion interests him.</p>',
              '<form method="get" action="/moltbook/friend-scout" class="bfs-filter">',
              '<label>Find a friend<input type="search" name="q" maxlength="64" value="'+e(search)+
              '" placeholder="Handle or display name"></label>',
              '<label>Watch status<select name="show">']
    for option,label in (("all","All active"),("watching","Watched"),
                         ("paused","Paused"),("issues","Integrity issues")):
        parts.append('<option value="'+option+'"'+(" selected" if option==show else "")+
                     '>'+label+'</option>')
    parts += ['</select></label><button type="submit">Filter</button></form>',
              '<p class="bfs-muted">'+str(total)+' matching of '+str(len(active))+
              ' verified active friends · page '+str(number)+' of '+str(pages)+
              ' · up to '+str(MAX_PREVIEW)+' per page</p>']
    if not active:
        parts.append('<p class="bfs-muted">No active verified friends. '
                     'Add agents in Moltbook → Friends or reactivate an archived entry.</p>')
    if active and not visible:
        parts.append('<p class="bfs-muted">No friends match these filters.</p>')
    for item in visible:
        state=("Preference integrity problem: not watched" if item["watch_problem"]
               else "Watched by Scout" if item["watch_enabled"]
               else "Not watched by Scout")
        parts += ['<div class="bfs-card"><strong>@'+e(item["handle"])+'</strong>',
                  '<p class="bfs-tags">'+e(item["relationship"])+' · '+e(item["display_name"])+
                  ' · '+e(state)+'</p>']
        evidence=activity.get(item["id"],{})
        if evidence.get("observed_at"):
            parts.append('<p class="bfs-muted">Last verified friend-focused source: '+
                         e(evidence["observed_at"])+' · Scout '+e(evidence["observed_run"])+
                         '</p>')
        if evidence.get("selected_at"):
            parts.append('<p class="bfs-muted">Last selected discussion: '+
                         e(evidence["selected_at"])+' · Scout '+e(evidence["selected_run"])+
                         '</p>')
        if not evidence:
            parts.append('<p class="bfs-muted">No verified saved friend-focused or '
                         'selected discussion in the 100 most recent Scout records.</p>')
        if item["watch_problem"]:
            parts.append('<p class="bfs-muted">Stored watch preference integrity failed. '
                         'No scouting will occur for this agent until repaired.</p>')
        else:
            parts += ['<form method="post" action="'+e(action)+'">',
                      '<input type="hidden" name="csrf" value="'+e(csrf)+'">',
                      '<input type="hidden" name="operation" value="watch">',
                      '<input type="hidden" name="id" value="'+e(item["id"])+'">',
                      '<input type="hidden" name="friend_sha" value="'+e(item["sha256"])+'">',
                      '<input type="hidden" name="watch_sha" value="'+e(item["watch_sha"])+'">',
                      '<input type="hidden" name="watch_enabled" value="'+(
                          "0" if item["watch_enabled"] else "1")+'">',
                      '<button class="secondary" type="submit">'+(
                          "Pause watching this friend" if item["watch_enabled"]
                          else "Resume watching this friend")+'</button></form>']
        past=db.execute("SELECT version,enabled,changed_at FROM bob_friend_watch_history "
                        "WHERE friend_id=? ORDER BY version DESC LIMIT 3",
                        (item["id"],)).fetchall()
        if past:
            parts += ['<details><summary class="bfs-muted">Recent watch changes</summary>']
            for v,flag,when in past:
                parts.append('<p class="bfs-muted">v'+str(v)+' · '+
                             ('watched' if flag else 'paused')+' · '+e(when)+'</p>')
            parts.append('</details>')
        parts.append('</div>')
    parts.append('<nav class="bfs-links" aria-label="Friend watchlist pages">')
    if number>1:
        parts.append('<a href="'+e(watch_uri(number-1))+'">Previous page</a>')
    if number<pages:
        parts.append('<a href="'+e(watch_uri(number+1))+'">Next page</a>')
    parts.append('</nav>')
    parts += ['</section><section class="bfs-panel"><h2>Bob’s selected friend discussions</h2>',
              '<p class="bfs-muted">These are existing, source-verified Scout choices '
              'and Bob’s recorded WHY rationale, not new reflections or proof of '
              'friendship. Only selected posts appear here; simply scanning a '
              'friend does not create an observation.</p>']
    if not observations:
        parts.append('<p class="bfs-muted">Bob has not selected a verifiable discussion '
                     'from an active saved friend yet.</p>')
    for observation in observations:
        parts += ['<div class="bfs-card"><strong>@'+e(observation["handle"])+'</strong>',
                  '<p class="bfs-tags">'+e(observation["title"])+' · '+
                  e(observation["run_id"])+'</p>',
                  '<p class="bfs-muted">'+e(observation["why"])+'</p>',
                  '<a href="/moltbook/friends?edit='+e(observation["id"])+
                  '">View friend details</a>']
        if observation["run_id"] in staged_runs:
            parts.append('<p class="bfs-tags">Already staged in private interest review inbox</p>')
        else:
            parts += ['<form method="post" action="/moltbook/friend-scout">',
                      '<input type="hidden" name="csrf" value="'+e(csrf)+'">',
                      '<input type="hidden" name="operation" value="interest_stage">',
                      '<input type="hidden" name="friend_id" value="'+e(observation["id"])+'">',
                      '<input type="hidden" name="friend_sha" value="'+e(observation["friend_sha"])+'">',
                      '<input type="hidden" name="run_id" value="'+e(observation["run_id"])+'">',
                      '<input type="hidden" name="post_id" value="'+e(observation["post_id"])+'">',
                      '<button class="secondary" type="submit">Stage tentative interest for review</button></form>']
        parts.append('</div>')
    parts += ['</section><section class="bfs-panel"><h2>Tentative interests · FM3.2a</h2>',
              '<p class="bfs-muted">These are Bob’s existing saved Scout WHY explanations '
              'that an owner explicitly staged, not fresh AI generations or verified facts '
              'about another agent. Approval records your decision locally; it does NOT '
              'update FM1 notes, PM2 memory, identity, browsing preferences or publication '
              'permissions. All review actions are reversible and audit logged.</p>']
    if not interest_items:
        parts.append('<p class="bfs-muted">No staged interests. Use the stage control '
                     'under a source-verified selected friend discussion above.</p>')
    for index,item in enumerate(interest_items):
        if index==12:
            parts.append('<details><summary class="bfs-muted">Older staged interests ('+
                         str(len(interest_items)-12)+')</summary>')
        try:
            author,pid,idea=_interest_source(item["run_id"])
            source_ok=(author.casefold()==item["handle"].casefold() and
                       pid==item["post_id"] and idea==item["idea"])
        except ValueError:
            source_ok=False
        parts += ['<div class="bfs-card"><strong>@'+e(item["handle"])+'</strong>',
                  '<p class="bfs-tags">'+e(item["status"])+' · v'+str(item["version"])+
                  ' · source run '+e(item["run_id"])+' · post '+e(item["post_id"])+'</p>',
                  '<p class="bfs-muted">'+e(item["idea"])+'</p>']
        if not source_ok:
            parts.append('<p class="bfs-muted">Source unavailable or changed. '
                         'No approval or reopening allowed.</p>')
        if item["review_reason"]:
            parts.append('<p class="bfs-muted">Latest owner review: '+e(item["review_reason"])+'</p>')
        decisions={"pending":("approve","reject","archive"),
                   "approved":("reopen","archive"),
                   "rejected":("reopen","archive"),"archived":("reopen",)}
        for action in decisions[item["status"]]:
            if not source_ok and action in ("approve","reopen"):
                continue
            parts += ['<form method="post" action="/moltbook/friend-scout">',
                      '<input type="hidden" name="csrf" value="'+e(csrf)+'">',
                      '<input type="hidden" name="operation" value="interest_review">',
                      '<input type="hidden" name="id" value="'+e(item["id"])+'">',
                      '<input type="hidden" name="expected_sha" value="'+e(item["sha256"])+'">',
                      '<input type="hidden" name="decision" value="'+action+'">',
                      '<label>Optional owner reason for '+action+
                      '<input name="reason" maxlength="240" autocomplete="off"></label>',
                      '<button class="secondary" type="submit">'+e(action.title())+
                      ' locally</button></form>']
        past=db.execute("SELECT version,saved_at,action FROM bob_friend_interest_history "
                        "WHERE id=? ORDER BY version DESC LIMIT 8",(item["id"],)).fetchall()
        if past:
            parts.append('<details><summary class="bfs-muted">Review history</summary>')
            for version,when,action in past:
                parts.append('<p class="bfs-muted">v'+str(version)+' · '+
                             e(action)+' · '+e(when)+'</p>')
            parts.append('</details>')
        parts.append('</div>')
    if len(interest_items)>12:
        parts.append('</details>')
    parts += ['</section><section class="bfs-panel"><h2>Recent friend scouting activity</h2>',
              '<p class="bfs-muted">Results appear after the existing Scout timer '
              'next runs. A missing friend post may mean the public profile or post '
              'was unavailable or failed source verification; the regular global '
              'Scout still runs. Enabling does not run Scout immediately, '
              'change its schedule, or create a publication approval.</p>']
    if not recent:
        parts.append('<p class="bfs-muted">No completed friend-focused runs yet.</p>')
    for rec in recent:
        parts += ['<div class="bfs-card"><strong>Scout '+e(rec["run_id"])+'</strong>',
                  '<p class="bfs-muted">'+str(rec.get("friend_source_count",0))+
                  ' friend source post(s) mixed in · '+e(rec.get("friend_scan_status","unknown"))+
                  ' · selected author '+e(rec.get("chosen_author") or "none")+
                  ' · status '+e(rec.get("status","unknown"))+'</p>',
                  '<p><a href="/scout">Review Scout drafts</a></p></div>']
    parts += ['</section><p><a href="/moltbook/friends">Manage friends</a></p></div>']
    return wrap("Moltbook · Friend Scout","".join(parts),"/moltbook/friend-scout")


def safe_error(exc):
    if type(exc) is ValueError and str(exc) in ERRORS:
        return str(exc)
    return "Friend scouting setting unchanged. Reload before retrying."
