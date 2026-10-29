"""PM2.2 reviewed memory suggestions from previously verified Bob Scout drafts.

No model calls, background jobs, external fetches or automatic memory writes.
The only source is a stored Scout result that passes the existing snapshot
and draft verification again before both staging and acceptance.
"""
from __future__ import annotations
from html import escape
from urllib.parse import urlencode
import hashlib
import hmac
import json
import re
import secrets

from bob_publish_common import load_record, event, now, RUN_ID, UUID
from bob_memory import initialize as memory_init, create as memory_create, validate as memory_validate
from bob_memory import CATEGORIES, CONFIDENCE

ID = re.compile(r"[0-9a-f]{24}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
CAP = 250
PENDING_CAP = 50
PAGE_SIZE = 8
COLS = ("id", "run_id", "post_id", "approval_sha", "snapshot_sha",
        "draft_title", "draft_content", "status", "created_at",
        "reviewed_at", "decision_reason", "memory_id", "sha256")
ERRORS = frozenset((
    "Source Scout run unavailable or no longer verified",
    "That Scout source changed; suggestion cannot be accepted",
    "Scout suggestion already recorded",
    "Suggestion inbox capacity reached",
    "Suggestion not found or modified",
    "Suggestion already reviewed; reload",
    "Suggestion changed; reload the inbox",
    "Invalid suggestion form",
    "Invalid suggestion selection",
    "Review reason must be 1-240 characters",
    "No memory changes to save",
    "Title must be 4-120 characters",
    "Memory text must be 1-2400 characters",
    "Unsupported category or confidence",
    "Memory capacity reached; new entries are disabled until a later retention release",
))


def e(value):
    return escape(str(value if value is not None else ""), quote=True)


def initialize(db):
    memory_init(db)
    db.execute("""CREATE TABLE IF NOT EXISTS bob_memory_suggestions (
       id TEXT PRIMARY KEY,
       run_id TEXT NOT NULL UNIQUE,
       post_id TEXT NOT NULL,
       approval_sha TEXT NOT NULL, snapshot_sha TEXT NOT NULL,
       draft_title TEXT NOT NULL, draft_content TEXT NOT NULL,
       status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
       created_at TEXT NOT NULL, reviewed_at TEXT NOT NULL,
       decision_reason TEXT NOT NULL, memory_id TEXT NOT NULL,
       sha256 TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS bob_memory_suggestions_status_idx "
               "ON bob_memory_suggestions(status, created_at)")


def seal(item):
    return hashlib.sha256(json.dumps({k:item[k] for k in COLS if k != "sha256"},
                                    sort_keys=True, ensure_ascii=False,
                                    separators=(",",":")).encode("utf-8")).hexdigest()


def _verified(run_id, loader=load_record):
    if not isinstance(run_id,str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid suggestion selection")
    record = loader(run_id)
    # load_record is the trusted local file/snapshot verifier, never a network lookup.
    if (not isinstance(record,dict)
        or record.get("run_id") != run_id
        or not isinstance(record.get("approval_sha256"),str)
        or not SHA.fullmatch(record["approval_sha256"])
        or not isinstance(record.get("snapshot_sha256"),str)
        or not SHA.fullmatch(record["snapshot_sha256"])
        or not isinstance(record.get("chosen_post_id"),str)
        or not UUID.fullmatch(record["chosen_post_id"])
        or not isinstance(record.get("draft_comment"),str)
        or not record["draft_comment"].strip()):
        raise ValueError("Source Scout run unavailable or no longer verified")
    return record


def _get(db, ident):
    if not isinstance(ident,str) or not ID.fullmatch(ident):
        raise ValueError("Invalid suggestion selection")
    row=db.execute("SELECT "+",".join(COLS)+" FROM bob_memory_suggestions WHERE id=?",
                   (ident,)).fetchone()
    if not row:
        raise ValueError("Suggestion not found or modified")
    item=dict(zip(COLS,row))
    if not hmac.compare_digest(item["sha256"],seal(item)):
        raise ValueError("Suggestion not found or modified")
    return item


def _suggest_fields(rec):
    raw_title=rec.get("chosen_title") or "Untitled Scout discussion"
    title="Scout discussion: "+str(raw_title).strip()[:95]
    # This is Bob's existing draft text, NOT an independently verified fact.
    content=str(rec["draft_comment"]).strip()[:2000]
    return memory_validate(dict(title=title[:120], content=content,
        category="observation",confidence="low",
        source_label="Verified local Scout run "+rec["run_id"]+
                     " post "+rec["chosen_post_id"],
        source_url=""))


def stage(db, run_id, *, loader=load_record):
    """Explicit operator action. No automated staging or inference."""
    rec=_verified(run_id,loader)
    suggestion=_suggest_fields(rec)
    initialize(db)
    if db.execute("SELECT 1 FROM bob_memory_suggestions WHERE run_id=?",(run_id,)).fetchone():
        raise ValueError("Scout suggestion already recorded")
    total,pending=db.execute(
        "SELECT count(*),sum(CASE WHEN status='pending' THEN 1 ELSE 0 END) "
        "FROM bob_memory_suggestions").fetchone()
    if total>=CAP or (pending or 0)>=PENDING_CAP:
        raise ValueError("Suggestion inbox capacity reached")
    t=now()
    item=dict(id=secrets.token_hex(12), run_id=run_id,
              post_id=rec["chosen_post_id"],approval_sha=rec["approval_sha256"],
              snapshot_sha=rec["snapshot_sha256"],draft_title=suggestion["title"],
              draft_content=suggestion["content"],status="pending",created_at=t,
              reviewed_at="",decision_reason="",memory_id="")
    item["sha256"]=seal(item)
    db.execute("INSERT INTO bob_memory_suggestions("+",".join(COLS)+") VALUES("+
               ",".join("?" for _ in COLS)+")",tuple(item[k] for k in COLS))
    event(db,"bob_memory_suggestion_staged",item["id"])
    return item["id"]


def review(db, ident, expected_sha, operation, reason, proposed=None, *, loader=load_record):
    if operation not in ("approve","reject"):
        raise ValueError("Invalid suggestion form")
    if not isinstance(expected_sha,str) or not SHA.fullmatch(expected_sha):
        raise ValueError("Invalid suggestion selection")
    if not isinstance(reason,str) or not 1<=len(reason.strip())<=240:
        raise ValueError("Review reason must be 1-240 characters")
    reason=reason.strip()
    initialize(db)
    item=_get(db,ident)
    if not hmac.compare_digest(item["sha256"],expected_sha):
        raise ValueError("Suggestion changed; reload the inbox")
    if item["status"]!="pending":
        raise ValueError("Suggestion already reviewed; reload")
    memory_id=""
    if operation=="approve":
        if not isinstance(proposed,dict) or set(proposed)!={"title","content","category","confidence"}:
            raise ValueError("Invalid suggestion form")
        # Provenance is server-owned. Reviewer can rewrite the observation,
        # but cannot impersonate a different source by changing IDs/URL.
        memory_fields=memory_validate(dict(**proposed,
            source_label="Verified local Scout run "+item["run_id"]+" post "+item["post_id"],
            source_url=""))
        live=_verified(item["run_id"],loader)
        if (live["approval_sha256"]!=item["approval_sha"]
            or live["snapshot_sha256"]!=item["snapshot_sha"]
            or live["chosen_post_id"]!=item["post_id"]):
            raise ValueError("That Scout source changed; suggestion cannot be accepted")
        # One SQLite transaction surrounds memory creation AND inbox decision.
        memory_id=memory_create(db,memory_fields)
    item["status"]="approved" if operation=="approve" else "rejected"
    item["memory_id"]=memory_id
    item["decision_reason"]=reason
    item["reviewed_at"]=now()
    item["sha256"]=seal(item)
    changed=db.execute(
        "UPDATE bob_memory_suggestions SET status=?,memory_id=?,decision_reason=?,"
        "reviewed_at=?,sha256=? WHERE id=? AND sha256=? AND status='pending'",
        (item["status"],memory_id,reason,item["reviewed_at"],item["sha256"],
         ident,expected_sha))
    if changed.rowcount!=1:
        raise ValueError("Suggestion changed; reload the inbox")
    event(db,"bob_memory_suggestion_"+operation,ident)
    return memory_id


def dispatch(db, form, *, loader=load_record):
    operation=form.get("operation")
    if operation=="stage":
        if set(form)!={"csrf","operation","run_id"}:
            raise ValueError("Invalid suggestion form")
        return stage(db,form["run_id"],loader=loader)
    if operation=="reject":
        if set(form)!={"csrf","operation","id","expected_sha","reason"}:
            raise ValueError("Invalid suggestion form")
        return review(db,form["id"],form["expected_sha"],operation,
                      form["reason"],loader=loader)
    if operation=="approve":
        if set(form)!={"csrf","operation","id","expected_sha","reason",
                        "title","content","category","confidence"}:
            raise ValueError("Invalid suggestion form")
        return review(db,form["id"],form["expected_sha"],operation,
                      form["reason"],{k:form[k] for k in
                                     ("title","content","category","confidence")},loader=loader)
    raise ValueError("Invalid suggestion form")


def safe_error(exc):
    if type(exc) is ValueError and str(exc) in ERRORS:
        return str(exc)
    return "Suggestion not changed. Reload and check source or revision."


def _select(name,values,selected):
    return ('<label>'+e(name.title())+f'<select name="{name}">'+
        "".join(f'<option value="{e(val)}"'+(' selected' if val==selected else '')+
                f'>{e(val.title())}</option>' for val in values)+'</select></label>')


def _hidden(key,value):
    return f'<input type="hidden" name="{e(key)}" value="{e(value)}">'


def _form_base(csrf,item,operation):
    return ('<form method="post" action="/mind/memory/suggestions">'+
            _hidden("csrf",csrf)+_hidden("operation",operation)+
            _hidden("id",item["id"])+_hidden("expected_sha",item["sha256"]))


def page(db, csrf, wrap, records, *, loader=load_record):
    initialize(db)
    pending=db.execute("SELECT "+",".join(COLS)+" FROM bob_memory_suggestions "
                       "WHERE status='pending' ORDER BY created_at DESC,id DESC "
                       "LIMIT ?",(PAGE_SIZE,)).fetchall()
    recent=db.execute("SELECT "+",".join(COLS)+" FROM bob_memory_suggestions "
                      "WHERE status!='pending' ORDER BY reviewed_at DESC,id DESC "
                      "LIMIT ?",(PAGE_SIZE,)).fetchall()
    known={r[0] for r in db.execute("SELECT run_id FROM bob_memory_suggestions")}
    # Only shortlist actual re-verifiable Scout records. No network work.
    sources=[]
    for rec in (records or [])[:30]:
        rid=rec.get("run_id") if isinstance(rec,dict) else None
        if not isinstance(rid,str) or rid in known:
            continue
        try:
            actual=_verified(rid,loader)
            _suggest_fields(actual)
        except (ValueError,TypeError,OSError):
            continue
        sources.append(actual)
        if len(sources)>=8:
            break
    css="""<style>
.bms{max-width:1060px;margin:auto;display:grid;gap:18px}
.bms-panel{border:1px solid #304b6c;border-radius:15px;padding:clamp(15px,2.5vw,24px);
background:linear-gradient(150deg,#17283f,#111e32)}
.bms-card{background:#13243a;border:1px solid #37516c;border-radius:10px;padding:15px;margin:12px 0;overflow-wrap:anywhere}
.bms h2{font-size:1.14rem;margin:0 0 12px}
.bms h3{font-size:1rem;margin:0 0 8px}
.bms p{line-height:1.5}
.bms-muted{color:#b5c9e1;font-size:.85rem}
.bms label{display:grid;gap:6px;margin:9px 0;font-weight:650}
.bms input:not([type=hidden]),.bms textarea,.bms select{width:100%;box-sizing:border-box;min-height:44px;
background:#0c1b2d;color:#eef4ff;border:1px solid #587593;border-radius:9px;padding:10px;font:inherit}
.bms textarea{min-height:120px;resize:vertical}
.bms button{border:1px solid #77a9db;border-radius:9px;padding:10px 16px;min-height:44px;
background:#285f91;color:white;font:inherit;font-weight:700;cursor:pointer}
.bms .secondary{background:#23354b}
.bms-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
.bms-actions form{flex:1}
.bms-actions button{width:100%}
.bms-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.bms-preview{white-space:pre-wrap;overflow-wrap:anywhere;background:#0d1a2b;padding:12px;
border:1px solid #37516c;border-radius:8px;max-height:210px;overflow:auto}
@media(max-width:680px){.bms-grid{grid-template-columns:1fr}.bms-actions{display:grid}}
</style>"""
    parts=[css,'<div class="bms"><section class="bms-panel"><h2>Suggested memories · review inbox</h2>',
           '<p class="bms-muted">Suggestions come from Bob’s existing locally verified Scout '
           'drafts. This is NOT a new LLM summary and NOT a verified factual claim. '
           'Stage a draft, review/edit it, and approve or reject manually. '
           'No future agent recall or public posting is enabled.</p>',
           f'<p class="bms-muted">{len(pending)} pending shown · up to {PENDING_CAP} pending and '
           f'{CAP} total stored suggestions.</p>']
    if not pending:
        parts.append('<p>No suggestions awaiting review.</p>')
    for row in pending:
        item=dict(zip(COLS,row))
        if not hmac.compare_digest(item["sha256"],seal(item)):
            continue
        parts.extend(['<article class="bms-card"><h3>'+e(item["draft_title"])+'</h3>',
                     '<p class="bms-muted">Scout run '+e(item["run_id"])+
                     ' · source post '+e(item["post_id"])+'</p>',
                     '<p class="bms-muted">This is untrusted draft text. Rewrite or '
                     'fact-check before approving as a memory.</p>',
                     '<p class="bms-preview">'+e(item["draft_content"])+'</p>',
                     _form_base(csrf,item,"approve"),
                     '<label>Memory title<input name="title" maxlength="120" required value="'+
                     e(item["draft_title"])+'"></label>',
                     '<label>Reviewed memory text<textarea name="content" maxlength="2400" required>'+
                     e(item["draft_content"])+'</textarea></label>',
                     '<div class="bms-grid">'+_select("category",CATEGORIES,"observation")+
                     _select("confidence",CONFIDENCE,"low")+'</div>',
                     '<label>Reason for accepting or correcting'
                     '<input name="reason" maxlength="240" required placeholder="What was verified?"></label>',
                     '<button type="submit">Approve as private memory</button></form>',
                     _form_base(csrf,item,"reject"),
                     '<label>Reason to reject<input name="reason" maxlength="240" required '
                     'placeholder="Why should this not be remembered?"></label>',
                     '<button type="submit" class="secondary">Reject suggestion</button></form>',
                     '</article>'])
    parts.append('</section><section class="bms-panel"><h2>Stage from existing Scout work</h2>'
                 '<p class="bms-muted">Only local records that still pass their original '
                 'saved feed-snapshot and draft checks appear. Staging does not create a memory.</p>')
    if not sources:
        parts.append('<p class="bms-muted">No unreviewed verified Scout drafts found.</p>')
    for rec in sources:
        parts.extend(['<article class="bms-card"><h3>'+e(str(rec.get("chosen_title") or
                      "Scout discussion")[:120])+'</h3>',
                      '<p class="bms-muted">Scout run '+e(rec["run_id"])+'</p>',
                      _form_base_for_stage(csrf,rec["run_id"]),
                      '</article>'])
    parts.append('</section><section class="bms-panel"><h2>Recent decisions</h2>')
    if not recent:
        parts.append('<p class="bms-muted">No reviewed suggestions yet.</p>')
    for row in recent:
        item=dict(zip(COLS,row))
        if not hmac.compare_digest(item["sha256"],seal(item)):
            continue
        parts.extend(['<article class="bms-card"><h3>'+e(item["draft_title"])+'</h3>',
                      '<p class="bms-muted">'+e(item["status"])+
                      ' · Scout run '+e(item["run_id"])+' · '+e(item["reviewed_at"])+'</p>',
                      '<p class="bms-muted">Review reason: '+e(item["decision_reason"])+'</p>'])
        if item["memory_id"]:
            parts.append('<p><a href="/mind/memory?edit='+e(item["memory_id"])+
                         '">Open approved memory and revision history</a></p>')
        parts.append('</article>')
    parts.append('</section><p><a href="/mind/memory">Return to Memory Manager</a></p></div>')
    return wrap("Bob's Mind · Memory suggestions","".join(parts),"/mind/memory/suggestions")


def _form_base_for_stage(csrf,run_id):
    return ('<form method="post" action="/mind/memory/suggestions">'+
            _hidden("csrf",csrf)+_hidden("operation","stage")+
            _hidden("run_id",run_id)+
            '<button type="submit">Stage for memory review</button></form>')
