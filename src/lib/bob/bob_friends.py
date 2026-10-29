"""FM1: private, operator-curated Moltbook agent directory.

Does not follow, message, fetch profiles or write to Moltbook. Scout authors
are only provenance-checked against saved feed snapshots, NOT live accounts.
No friend entries are ever injected into prompts or autonomous scout filters.
"""
from __future__ import annotations

from html import escape
from urllib.parse import urlencode
import hashlib
import hmac
import json
import re
import secrets
import sqlite3

import bob_publish_common as common

ID = re.compile(r"[0-9a-f]{24}\Z")
HANDLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{1,39}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
RELATIONS = ("interesting", "acquaintance", "friend")
STATES = ("active", "muted", "archived")
CAP = 300
PAGE_SIZE = 12
EDIT_FIELDS = ("display_name", "relationship", "interests", "notes")
COLS = ("id", "handle", "handle_key") + EDIT_FIELDS + (
    "source_kind", "source_run", "source_post", "state",
    "created_at", "updated_at", "version", "sha256")
ERRORS = frozenset((
    "Invalid agent handle (2-40 characters: letters, digits, underscore, dot, hyphen)",
    "Agent handle already in directory",
    "Friends directory capacity reached",
    "Missing or invalid friend ID",
    "Friend record modified; reload",
    "Friend record integrity check failed",
    "Archived or muted friend must be reactivated before editing",
    "No changes to save",
    "Relationship must be interesting, acquaintance or friend",
    "Invalid friend form",
    "Reason must be 1-240 characters",
    "Display name must be 0-100 characters",
    "Interests must be 0-500 characters",
    "Notes must be 0-1200 characters",
    "Source Scout run unavailable or changed",
    "Scout author is not a valid agent handle",
    "Friend state changed; reload",
))


def e(value):
    return escape(str(value if value is not None else ""), quote=True)


def initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friends (
      id TEXT PRIMARY KEY, handle TEXT NOT NULL,
      handle_key TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL, relationship TEXT NOT NULL
          CHECK(relationship IN ('interesting','acquaintance','friend')),
      interests TEXT NOT NULL, notes TEXT NOT NULL,
      source_kind TEXT NOT NULL CHECK(source_kind IN ('manual','scout_snapshot')),
      source_run TEXT NOT NULL, source_post TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN ('active','muted','archived')),
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      version INTEGER NOT NULL, sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS bob_friend_revisions (
      revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
      friend_id TEXT NOT NULL, version INTEGER NOT NULL,
      saved_at TEXT NOT NULL, action TEXT NOT NULL,
      reason TEXT NOT NULL, snapshot_json TEXT NOT NULL,
      UNIQUE(friend_id,version))""")
    db.execute("CREATE INDEX IF NOT EXISTS bob_friends_state_idx ON bob_friends(state,updated_at)")
    db.execute("CREATE INDEX IF NOT EXISTS bob_friends_history_idx ON bob_friend_revisions(friend_id,version)")


def handle(value):
    if not isinstance(value,str):
        raise ValueError("Invalid agent handle (2-40 characters: letters, digits, underscore, dot, hyphen)")
    h=value.strip()
    if not HANDLE.fullmatch(h) or h in (".",".."):
        raise ValueError("Invalid agent handle (2-40 characters: letters, digits, underscore, dot, hyphen)")
    return h


def _text(value,name,limit):
    if not isinstance(value,str):
        raise ValueError(name+" must be 0-"+str(limit)+" characters")
    value=value.strip()
    if len(value)>limit or "\x00" in value or any(ord(c)<32 and c not in "\n\t" for c in value):
        raise ValueError(name+" must be 0-"+str(limit)+" characters")
    return value


def validate(fields):
    if not isinstance(fields,dict) or set(fields)!=set(EDIT_FIELDS):
        raise ValueError("Invalid friend form")
    if fields["relationship"] not in RELATIONS:
        raise ValueError("Relationship must be interesting, acquaintance or friend")
    return dict(display_name=_text(fields["display_name"],"Display name",100),
                relationship=fields["relationship"],
                interests=_text(fields["interests"],"Interests",500),
                notes=_text(fields["notes"],"Notes",1200))


def seal(item):
    return hashlib.sha256(json.dumps({k:item[k] for k in COLS if k!="sha256"},
                                    ensure_ascii=False,sort_keys=True,
                                    separators=(",",":")).encode("utf-8")).hexdigest()


def _get(db,ident):
    if not isinstance(ident,str) or not ID.fullmatch(ident):
        raise ValueError("Missing or invalid friend ID")
    row=db.execute("SELECT "+",".join(COLS)+" FROM bob_friends WHERE id=?",(ident,)).fetchone()
    if not row:
        raise ValueError("Missing or invalid friend ID")
    item=dict(zip(COLS,row))
    if not hmac.compare_digest(item["sha256"],seal(item)):
        raise ValueError("Friend record integrity check failed")
    return item


def _revision(db,item,action,reason):
    db.execute("INSERT INTO bob_friend_revisions(friend_id,version,saved_at,action,"
               "reason,snapshot_json) VALUES(?,?,?,?,?,?)",
               (item["id"],item["version"],item["updated_at"],action,reason,
                json.dumps({k:item[k] for k in COLS},sort_keys=True,ensure_ascii=False)))


def _source_author(run_id,loader=None):
    # File snapshot identity (not live account identity) must match BOTH record
    # and original checksum-verified chosen feed post. No remote fetch.
    if not isinstance(run_id,str) or not common.RUN_ID.fullmatch(run_id):
        raise ValueError("Source Scout run unavailable or changed")
    rec=(loader or common.load_record)(run_id)
    if not isinstance(rec,dict) or rec.get("run_id")!=run_id:
        raise ValueError("Source Scout run unavailable or changed")
    try:
        path=common.DATA/("scout-feed-"+run_id+".json")
        if path.is_symlink() or not path.is_file() or path.stat().st_size>512*1024:
            raise ValueError("Source Scout run unavailable or changed")
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=rec["snapshot_sha256"]:
            raise ValueError("Source Scout run unavailable or changed")
        posts=json.loads(raw)["posts"]
        post=next(x for x in posts if isinstance(x,dict)
                  and x.get("id")==rec.get("chosen_post_id"))
        author=post["author"]
        if author!=rec.get("chosen_author"):
            raise ValueError("Source Scout run unavailable or changed")
    except (OSError,KeyError,TypeError,StopIteration,ValueError,json.JSONDecodeError) as exc:
        if isinstance(exc,ValueError) and str(exc)=="Source Scout run unavailable or changed":
            raise
        raise ValueError("Source Scout run unavailable or changed") from None
    try:
        return handle(author),rec["run_id"],rec["chosen_post_id"]
    except ValueError:
        raise ValueError("Scout author is not a valid agent handle") from None


def create(db,agent_handle,fields,*,source_kind="manual",run_id="",post_id=""):
    h=handle(agent_handle)
    data=validate(fields)
    if source_kind not in ("manual","scout_snapshot"):
        raise ValueError("Invalid friend form")
    if source_kind=="manual" and (run_id or post_id):
        raise ValueError("Invalid friend form")
    if source_kind=="scout_snapshot" and (not common.RUN_ID.fullmatch(run_id)
                                        or not common.UUID.fullmatch(post_id)):
        raise ValueError("Invalid friend form")
    initialize(db)
    if db.execute("SELECT count(*) FROM bob_friends").fetchone()[0]>=CAP:
        raise ValueError("Friends directory capacity reached")
    if db.execute("SELECT 1 FROM bob_friends WHERE handle_key=?",(h.casefold(),)).fetchone():
        raise ValueError("Agent handle already in directory")
    t=common.now()
    item=dict(id=secrets.token_hex(12),handle=h,handle_key=h.casefold(),**data,
              source_kind=source_kind,source_run=run_id,source_post=post_id,
              state="active",created_at=t,updated_at=t,version=1)
    item["sha256"]=seal(item)
    try:
        db.execute("INSERT INTO bob_friends("+",".join(COLS)+") VALUES("+
                   ",".join("?" for _ in COLS)+")",tuple(item[k] for k in COLS))
    except sqlite3.IntegrityError:
        raise ValueError("Agent handle already in directory") from None
    _revision(db,item,"create","Operator added a "+source_kind+" directory entry")
    common.event(db,"bob_friend_created",item["id"])
    return item["id"]


def change(db,ident,expected_sha,action,fields=None,reason=""):
    if action not in ("edit","mute","archive","reactivate"):
        raise ValueError("Invalid friend form")
    if not isinstance(expected_sha,str) or not SHA.fullmatch(expected_sha):
        raise ValueError("Invalid friend form")
    initialize(db)
    item=_get(db,ident)
    if not hmac.compare_digest(expected_sha,item["sha256"]):
        raise ValueError("Friend record modified; reload")
    if action=="edit":
        if item["state"]!="active":
            raise ValueError("Archived or muted friend must be reactivated before editing")
        validated=validate(fields)
        reason=_text(reason,"Reason",240)
        if not reason:
            raise ValueError("Reason must be 1-240 characters")
        if all(item[k]==validated[k] for k in EDIT_FIELDS):
            raise ValueError("No changes to save")
        item.update(validated)
    else:
        state={"mute":"muted","archive":"archived","reactivate":"active"}[action]
        if action=="reactivate" and item["state"]=="active" or (
            action!="reactivate" and item["state"]!="active"):
            raise ValueError("Friend state changed; reload")
        item["state"]=state
        reason="Operator changed local directory state to "+state
    item["version"]+=1
    item["updated_at"]=common.now()
    item["sha256"]=seal(item)
    columns=[k for k in COLS if k!="id"]
    cur=db.execute("UPDATE bob_friends SET "+",".join(k+"=?" for k in columns)+
                   " WHERE id=? AND sha256=?",
                   tuple(item[k] for k in columns)+(ident,expected_sha))
    if cur.rowcount!=1:
        raise ValueError("Friend record modified; reload")
    _revision(db,item,action,reason)
    common.event(db,"bob_friend_"+action,ident+" v"+str(item["version"]))
    return ident


def dispatch(db,form,*,loader=None):
    action=form.get("operation","")
    if action=="create":
        if set(form)!={"csrf","operation","handle",*EDIT_FIELDS}:
            raise ValueError("Invalid friend form")
        return create(db,form["handle"],{k:form[k] for k in EDIT_FIELDS})
    if action=="scout_add":
        if set(form)!={"csrf","operation","run_id"}:
            raise ValueError("Invalid friend form")
        h,run_id,pid=_source_author(form["run_id"],loader)
        return create(db,h,dict(display_name=h,relationship="interesting",
                    interests="",notes=""),source_kind="scout_snapshot",
                    run_id=run_id,post_id=pid)
    if action=="edit":
        if set(form)!={"csrf","operation","id","expected_sha","reason",*EDIT_FIELDS}:
            raise ValueError("Invalid friend form")
        return change(db,form["id"],form["expected_sha"],"edit",
                      {k:form[k] for k in EDIT_FIELDS},form["reason"])
    if action in ("mute","archive","reactivate"):
        if set(form)!={"csrf","operation","id","expected_sha"}:
            raise ValueError("Invalid friend form")
        return change(db,form["id"],form["expected_sha"],action)
    raise ValueError("Invalid friend form")


def safe_error(exc):
    if type(exc) is ValueError and str(exc) in ERRORS:
        return str(exc)
    return "Friends directory unchanged. Reload and review your input."


CSS="""<style>
.bfm{max-width:1100px;margin:auto;display:grid;gap:18px}
.bfm-panel{background:linear-gradient(145deg,#17283f,#111e32);border:1px solid #34516c;
border-radius:15px;padding:clamp(15px,2.5vw,23px)}
.bfm h2{font-size:1.12rem;margin:0 0 10px}.bfm h3{font-size:1.02rem;margin:0 0 8px}
.bfm-muted{color:#b4c9df;font-size:.86rem;line-height:1.55}
.bfm-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.bfm label{display:grid;gap:7px;font-weight:650;margin:10px 0}
.bfm input:not([type=hidden]),.bfm select,.bfm textarea{box-sizing:border-box;min-height:44px;width:100%;
padding:10px 12px;background:#0d1c2d;border:1px solid #587493;border-radius:9px;
color:#f1f6ff;font:inherit}
.bfm textarea{min-height:100px;resize:vertical}
.bfm button,.bfm-link{display:inline-block;border:1px solid #75a5d8;background:#2a608f;
border-radius:9px;color:#fff;padding:10px 14px;min-height:44px;font:inherit;
font-weight:700;cursor:pointer;text-decoration:none}
.bfm button.secondary,.bfm-link.secondary{background:#25384e}
.bfm button:focus-visible,.bfm-link:focus-visible,.bfm input:focus-visible,.bfm textarea:focus-visible,
.bfm select:focus-visible{outline:2px solid #87c5ff;outline-offset:2px}
.bfm-actions{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
.bfm-actions form{margin:0}
.bfm-card{border:1px solid #3c5775;background:#14253b;border-radius:12px;
padding:15px;margin:12px 0;overflow-wrap:anywhere}
.bfm-tags{display:flex;gap:7px;flex-wrap:wrap;margin:9px 0}
.bfm-tag{font-size:.77rem;color:#c0d6eb;padding:4px 9px;border-radius:15px;border:1px solid #536f8a}
.bfm-body{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}
.bfm-filter{display:grid;grid-template-columns:minmax(160px,2fr) minmax(130px,1fr) auto;
gap:12px;align-items:end}
@media(max-width:700px){.bfm-grid,.bfm-filter{grid-template-columns:1fr}
.bfm-actions form,.bfm-actions button,.bfm-actions .bfm-link{width:100%;text-align:center}}
</style>"""


def _hidden(name,value):
    return '<input type="hidden" name="'+e(name)+'" value="'+e(value)+'">'


def _field(name,label,value,limit,textarea=False):
    if textarea:
        return '<label>'+e(label)+'<textarea name="'+name+'" maxlength="'+str(limit)+'">'+e(value)+'</textarea></label>'
    return '<label>'+e(label)+'<input name="'+name+'" maxlength="'+str(limit)+'" value="'+e(value)+'"></label>'


def _select(name,values,chosen):
    return '<label>'+e(name.title())+'<select name="'+name+'">'+''.join(
        '<option value="'+e(v)+'"'+(' selected' if v==chosen else '')+'>'+e(v.title())+'</option>'
        for v in values)+'</select></label>'


def _editor(csrf,friend=None):
    editing=friend is not None
    values=friend or dict(handle="",display_name="",relationship="interesting",
                          interests="",notes="")
    parts=['<section class="bfm-panel"><h2>'+("Edit agent" if editing else "Add an agent")+'</h2>',
           '<p class="bfm-muted">This is Bob’s private directory, not a verified Moltbook '
           'friendship or social follow. No online actions occur.</p>',
           '<form method="post" action="/moltbook/friends">',
           _hidden("csrf",csrf),_hidden("operation","edit" if editing else "create")]
    if editing:
        parts += [_hidden("id",friend["id"]),_hidden("expected_sha",friend["sha256"]),
                  '<p><strong>@'+e(friend["handle"])+'</strong> (handle locked; archive to replace)</p>']
    else:
        parts.append('<label>Agent handle<input name="handle" minlength="2" maxlength="40" '
                     'required pattern="[A-Za-z0-9][A-Za-z0-9_.-]{1,39}" '
                     'placeholder="moltbook_agent"></label>')
    parts += ['<div class="bfm-grid">',
              _field("display_name","Display label",values["display_name"],100),
              _select("relationship",RELATIONS,values["relationship"]),
              '</div>',
              _field("interests","Why is this agent interesting?",values["interests"],500,True),
              _field("notes","Private relationship notes",values["notes"],1200,True)]
    if editing:
        parts.append(_field("reason","Reason for changes (required)", "",240))
    parts += ['<div class="bfm-actions"><button type="submit">'+
              ("Save changes" if editing else "Add to private directory")+'</button>']
    if editing:
        parts.append('<a class="bfm-link secondary" href="/moltbook/friends">Cancel edit</a>')
    parts.append('</div></form></section>')
    return ''.join(parts)


def _state_form(csrf,item,action,label):
    return ('<form method="post" action="/moltbook/friends">'+
            _hidden("csrf",csrf)+_hidden("operation",action)+
            _hidden("id",item["id"])+_hidden("expected_sha",item["sha256"])+
            '<button type="submit" class="secondary">'+e(label)+'</button></form>')


def _history(db,ident):
    rows=db.execute("SELECT version,saved_at,action,reason,snapshot_json "
                    "FROM bob_friend_revisions WHERE friend_id=? "
                    "ORDER BY version DESC LIMIT 20",(ident,)).fetchall()
    result=['<section class="bfm-panel"><h2>Private relationship history</h2>']
    for v,t,action,reason,payload in rows:
        try:
            previous=json.loads(payload)
        except (ValueError,TypeError):
            continue
        result += ['<details><summary>v'+str(v)+' · '+e(action)+' · '+e(t)+
                   ' · '+e(reason)+'</summary>',
                   '<p class="bfm-body">'+e(previous.get("notes",""))+'</p>',
                   '<p class="bfm-muted">Interests: '+e(previous.get("interests",""))+'</p></details>']
    result.append('</section>')
    return ''.join(result)


def page(db,csrf,wrap,params,records=None,*,loader=None):
    initialize(db)
    def param(name,default=""):
        vals=params.get(name,[])
        return vals[0] if len(vals)==1 and isinstance(vals[0],str) else default
    search=param("q")[:64].strip()
    show=param("show","active")
    show=show if show in (*STATES,"all") else "active"
    edit_id=param("edit")
    number=param("page","1")
    number=min(int(number),999) if re.fullmatch(r"[1-9]\d{0,3}",number) else 1
    selected=None
    if ID.fullmatch(edit_id):
        try:
            selected=_get(db,edit_id)
        except ValueError:
            selected=None
    clauses=[]
    args=[]
    if show!="all":
        clauses.append("state=?")
        args.append(show)
    if search:
        clauses.append("(instr(lower(handle),lower(?))>0 OR "
                       "instr(lower(display_name),lower(?))>0 OR "
                       "instr(lower(interests),lower(?))>0 OR "
                       "instr(lower(notes),lower(?))>0)")
        args.extend([search]*4)
    where=" WHERE "+" AND ".join(clauses) if clauses else ""
    total=db.execute("SELECT count(*) FROM bob_friends"+where,args).fetchone()[0]
    last=max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)
    number=min(number,last)
    rows=db.execute("SELECT "+",".join(COLS)+" FROM bob_friends"+where+
                    " ORDER BY updated_at DESC,id DESC LIMIT ? OFFSET ?",
                    args+[PAGE_SIZE,(number-1)*PAGE_SIZE]).fetchall()
    def uri(p):
        return "/moltbook/friends?"+urlencode({"q":search,"show":show,"page":p})
    parts=[CSS,'<div class="bfm">',
           '<section class="bfm-panel"><h2>Friends Manager · FM1</h2>',
           '<p class="bfm-muted">Private address book for Bob’s favorite or interesting '
           'Moltbook agents. “Friend” is a personal relationship label, NOT confirmation '
           'of a platform friendship. Future follow, profile lookup and targeted scouting '
           'are separate features and disabled here.</p></section>',
           _editor(csrf,selected if selected and selected["state"]=="active" else None),
           '<section class="bfm-panel"><h2>Find agents</h2>',
           '<form method="get" action="/moltbook/friends" class="bfm-filter">',
           '<label>Search<input name="q" type="search" maxlength="64" value="'+e(search)+
           '" placeholder="Handle, interests, notes"></label>',
           '<label>Visibility<select name="show">']
    for state in (*STATES,"all"):
        parts.append('<option value="'+state+'"'+(" selected" if state==show else "")+
                     '>'+e(state.title())+'</option>')
    parts += ['</select></label><button type="submit">Search</button></form>',
              '<p class="bfm-muted">'+str(total)+' matching agents · page '+str(number)+
              ' of '+str(last)+' · up to '+str(CAP)+' private entries</p>']
    for row in rows:
        item=dict(zip(COLS,row))
        if not hmac.compare_digest(item["sha256"],seal(item)):
            continue
        parts += ['<article class="bfm-card"><h3>@'+e(item["handle"])+'</h3>',
                  '<p class="bfm-muted">'+e(item["display_name"])+'</p>',
                  '<div class="bfm-tags">',
                  *('<span class="bfm-tag">'+e(value)+'</span>' for value in
                    (item["relationship"],item["state"],item["source_kind"],"v"+str(item["version"]))),
                  '</div>']
        if item["interests"]:
            parts.append('<p class="bfm-body"><strong>Interests:</strong> '+e(item["interests"])+'</p>')
        if item["notes"]:
            parts.append('<p class="bfm-body"><strong>Notes:</strong> '+e(item["notes"])+'</p>')
        if item["source_kind"]=="scout_snapshot":
            parts.append('<p class="bfm-muted">Observed in saved Scout run '+e(item["source_run"])+
                         ', post '+e(item["source_post"])+
                         ' (snapshot evidence, not live account verification)</p>')
        parts.append('<div class="bfm-actions">')
        if item["state"]=="active":
            parts += ['<a class="bfm-link secondary" href="/moltbook/friends?edit='+item["id"]+
                      '">Edit / history</a>',
                      _state_form(csrf,item,"mute","Mute locally"),
                      _state_form(csrf,item,"archive","Archive")]
        else:
            parts += [_state_form(csrf,item,"reactivate","Reactivate"),
                      '<a class="bfm-link secondary" href="/moltbook/friends?edit='+item["id"]+
                      '">View history</a>']
        parts.append('</div></article>')
    if not rows:
        parts.append('<p class="bfm-muted">No agents match this view. Add a handle above '
                     'or save a verified Scout author below.</p>')
    parts.append('<nav class="bfm-actions">')
    if number>1:
        parts.append('<a class="bfm-link secondary" href="'+e(uri(number-1))+'">Previous</a>')
    if number<last:
        parts.append('<a class="bfm-link secondary" href="'+e(uri(number+1))+'">Next</a>')
    parts.append('</nav></section>')
    if selected:
        if selected["state"]!="active":
            parts.append('<section class="bfm-panel"><p class="bfm-muted">'
                         'Reactivate this entry before editing; history is still available.</p></section>')
        parts.append(_history(db,selected["id"]))
    # At most six verified local sources, independently checked against their
    # exact captured author; never trust unverified display names from a feed.
    suggestions=[]
    seen=set()
    for rec in (records or [])[:50]:
        run_id=rec.get("run_id") if isinstance(rec,dict) else None
        try:
            h,rid,_pid=_source_author(run_id,loader)
        except (ValueError,OSError,TypeError):
            continue
        key=h.casefold()
        if key in seen or db.execute("SELECT 1 FROM bob_friends WHERE handle_key=?",(key,)).fetchone():
            continue
        seen.add(key)
        suggestions.append((h,rid))
        if len(suggestions)>=6:
            break
    parts += ['<section class="bfm-panel"><h2>Agents seen in Scout</h2>',
              '<p class="bfm-muted">Optional quick-add from a locally verified Scout '
              'snapshot. The captured author string may not be a verified account '
              'identity. Each addition requires your click, never automatic follow.</p>']
    if not suggestions:
        parts.append('<p class="bfm-muted">No new snapshot-backed authors available.</p>')
    for h,rid in suggestions:
        parts += ['<div class="bfm-card"><strong>@'+e(h)+'</strong>',
                  '<p class="bfm-muted">Saved Scout run '+e(rid)+'</p>',
                  '<form method="post" action="/moltbook/friends">'+
                  _hidden("csrf",csrf)+_hidden("operation","scout_add")+
                  _hidden("run_id",rid)+
                  '<button type="submit">Add to private directory</button></form></div>']
    parts.append('</section></div>')
    return wrap("Moltbook · Friends","".join(parts),"/moltbook/friends")
