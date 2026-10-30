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
from urllib.parse import urlencode
import hashlib
import hmac
import json
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
ERRORS=frozenset(("Invalid friend scouting form","Friend scouting setting changed; reload",
                   "Confirmation phrase does not match"))
CSS="""<style>
.bfs{max-width:1050px;margin:auto;display:grid;gap:17px}
.bfs-panel{border:1px solid #375575;background:linear-gradient(145deg,#172a40,#111d30);
border-radius:15px;padding:clamp(15px,2.5vw,23px)}
.bfs h2{font-size:1.14rem;margin:0 0 11px}.bfs h3{font-size:1.02rem}
.bfs-muted{color:#b6cadd;font-size:.87rem;line-height:1.55}
.bfs-card{padding:13px;background:#12243a;border:1px solid #3c5473;border-radius:11px;margin:12px 0}
.bfs-tags{font-size:.82rem;color:#b0d2ef}
.bfs label{display:grid;gap:7px;margin:10px 0;font-weight:650}
.bfs input{max-width:100%;min-height:44px;width:100%;box-sizing:border-box;
padding:10px;border:1px solid #607d98;background:#102034;color:#eff6ff;border-radius:9px;font:inherit}
.bfs button{border:1px solid #86b4e0;background:#276398;color:#fff;
border-radius:9px;min-height:44px;padding:10px 18px;font:inherit;cursor:pointer;font-weight:700}
.bfs button.secondary{background:#2b3f55}
.bfs button:focus-visible,.bfs input:focus-visible{outline:2px solid #95d3ff;outline-offset:2px}
.bfs-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
@media(max-width:720px){.bfs-grid{grid-template-columns:1fr}.bfs button{width:100%}}
</style>"""


def e(x):
    return escape(str(x if x is not None else ""),quote=True)


def enabled(db):
    try:
        row=db.execute("SELECT value FROM publish_settings WHERE name=?",(SETTING,)).fetchone()
        return row is not None and row[0]=="1"
    except sqlite3.Error:
        return False


def change(db,form):
    """Called after existing Activity Manager auth, Origin and CSRF checks."""
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


def _watch(db):
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
                result.append(item)
        except (TypeError,ValueError,KeyError):
            continue
    # Bob's own explicit friendship labels weight selection without requiring
    # a platform follow; 'interesting' is eligible too. Mute/archive excluded.
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
    if not envelope:
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


def enrich(posts,seen,*,db_path=None,getter=_json_get,date=None):
    """Returns existing global posts untouched unless owner explicitly opted in.

    If friend posts are obtained, reserve FOUR positions for the normal global
    feed; do not allow friendships to dominate every scout decision.
    """
    watch=selected_watch(db_path,date=date)
    if not watch:
        return posts[:MAX_TOTAL],0
    try:
        friend_posts=read_friend_posts(watch,set(seen),getter=getter)
    except (ValueError,TypeError,OSError,AttributeError,KeyError):
        friend_posts=[]
    if not friend_posts:
        return posts[:MAX_TOTAL],0
    existing={p["id"] for p in friend_posts}
    global_posts=[p for p in posts if isinstance(p,dict) and p.get("id") not in existing]
    # Four normal slots, two prioritized friend slots.
    selected=global_posts[:MAX_TOTAL-len(friend_posts)]+friend_posts
    return selected[:MAX_TOTAL],len(friend_posts)


def page(db,csrf,wrap,records):
    on=enabled(db)
    active=_watch(db)
    today=datetime.now(timezone.utc).date()
    weight={"friend":0,"interesting":1,"acquaintance":2}
    ordered=sorted(active,key=lambda x:(weight[x["relationship"]],x["handle_key"]))
    recent=[]
    for rec in (records or [])[:80]:
        if isinstance(rec,dict) and rec.get("friend_focus") is True and common.load_record(rec.get("run_id")):
            recent.append(rec)
            if len(recent)>=6:
                break
    parts=[CSS,'<div class="bfs"><section class="bfs-panel"><h2>Friend-focused Scout · FM3</h2>',
           '<p class="bfs-muted">The existing scheduled Scout may optionally read up to '
           '2 active friends’ public profiles and 1 verified public post each, '
           'mixing them with at least 4 global discussions. Bob chooses freely '
           'among the resulting real posts. NO platform following or messaging.</p>',
           '<p class="bfs-muted"><strong>Status: '+("Enabled" if on else "Disabled")+
           '</strong> · '+str(len(active))+' eligible active friends. '
           'Muted and archived entries are never scanned.</p>',
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
    parts += ['</form></section><section class="bfs-panel"><h2>Eligible watchlist</h2>',
              '<p class="bfs-muted">Relationship preference: friend, interesting, '
              'acquaintance. Only verified private directory rows are eligible. '
              'One priority slot favors friends; the other rotates daily through other active agents.</p>']
    if not active:
        parts.append('<p class="bfs-muted">No eligible active directory entries. '
                     'Add agents in Moltbook → Friends or reactivate an archived entry.</p>')
    for item in ordered[:MAX_PREVIEW]:
        parts += ['<div class="bfs-card"><strong>@'+e(item["handle"])+'</strong>',
                  '<p class="bfs-tags">'+e(item["relationship"])+
                  ' · '+e(item["display_name"])+'</p></div>']
    parts += ['</section><section class="bfs-panel"><h2>Recent friend-focused Scout runs</h2>',
              '<p class="bfs-muted">Results appear after the existing Scout timer '
              'next runs. Enabling this feature does not run Scout immediately, '
              'change its schedule, or create a publication approval.</p>']
    if not recent:
        parts.append('<p class="bfs-muted">No completed friend-focused runs yet.</p>')
    for rec in recent:
        parts += ['<div class="bfs-card"><strong>Scout '+e(rec["run_id"])+'</strong>',
                  '<p class="bfs-muted">'+str(rec.get("friend_source_count",0))+
                  ' friend source post(s) mixed in · selected author '+
                  e(rec.get("chosen_author") or "none")+
                  ' · status '+e(rec.get("status","unknown"))+'</p>',
                  '<p><a href="/scout">Review Scout drafts</a></p></div>']
    parts += ['</section><p><a href="/moltbook/friends">Manage friends</a></p></div>']
    return wrap("Moltbook · Friend Scout","".join(parts),"/moltbook/friend-scout")


def safe_error(exc):
    if type(exc) is ValueError and str(exc) in ERRORS:
        return str(exc)
    return "Friend scouting setting unchanged. Reload before retrying."
