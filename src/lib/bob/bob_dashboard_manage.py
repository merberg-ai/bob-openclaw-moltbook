"""Compact, server-rendered Bob queue management with guarded batch changes.

Never reads Moltbook credentials, sends HTTP, deletes source rows or performs
network publishing. A queue operation only records an approved publication
intent for the existing rate-limited publisher worker.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import hashlib
import re
import sqlite3
from urllib.parse import urlencode

from bob_originals import initialize as original_init, transition as original_transition
from bob_publish_common import event, queue_manual, UUID

PAGE_SIZE = 10
MAX_SELECTED = 10
ID_SCOUT = re.compile(r"\d{8}T\d{6}Z\Z")
ID_ORIGINAL = re.compile(r"[0-9a-f]{24}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
TABS = ("scout", "originals", "activity")
STATES = ("all", "pending", "draft", "needs review", "approved", "rejected",
          "queued", "sending", "awaiting_verification", "verifying",
          "published", "verified_unconfirmed", "uncertain", "failed", "cancelled")
SHOW = ("active", "archived", "all")
TITLES = {"scout": "Scout & review", "originals": "Original posts",
          "activity": "Comment activity"}
ALLOWED = {"scout": ("approve", "reject", "queue", "archive", "restore"),
           "originals": ("approve", "reject", "queue", "archive", "restore"),
           "activity": ("archive", "restore")}

CSS = """<style>
.bqm{max-width:1040px;margin:auto}
.bqm-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
.bqm-tabs a{display:inline-block;padding:10px 15px;background:#1a304a;border:1px solid #3a5374;border-radius:10px;text-decoration:none;font-weight:700}
.bqm-tabs a[aria-current="page"]{background:#295e91;color:#fff}
.bqm-filter{display:grid;grid-template-columns:minmax(150px,2fr) repeat(2,minmax(115px,1fr)) auto;gap:10px;align-items:end;margin:14px 0}
.bqm-filter label,.bqm-actionbar label{display:grid;gap:5px;font-weight:650;font-size:.9rem}
.bqm :is(input,select,button){min-height:44px;box-sizing:border-box;border-radius:9px}
.bqm :is(input,select){width:100%;padding:8px;background:#0e1b2b;color:#f0f5ff;border:1px solid #506b8c}
.bqm button{padding:8px 14px;cursor:pointer;background:#2b6093;color:#fff;border:1px solid #6f9dce;font-weight:700}
.bqm-info{color:#b6c9e1;font-size:.88rem;margin:12px 0}
.bqm-item{border:1px solid #2f4867;border-radius:12px;padding:15px;margin:10px 0;background:#14243a}
.bqm-item-head{display:flex;align-items:flex-start;gap:12px}
.bqm-check{display:inline-flex!important;align-items:center;gap:7px;min-height:44px;flex:0 0 auto}
.bqm-check input{min-height:22px;width:22px;accent-color:#80bfff}
.bqm-item-main{min-width:0;flex:1}
.bqm-item h2{font-size:1.04rem;margin:3px 0 7px;overflow-wrap:anywhere}
.bqm-flag{display:inline-block;border:1px solid #4d6e8b;border-radius:12px;padding:3px 9px;font-size:.76rem;margin:0 4px 5px 0}
.bqm-item details{margin-top:8px}
.bqm-item summary{cursor:pointer;min-height:35px;color:#a9d1ff}
.bqm-item pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:320px;overflow:auto}
.bqm-actionbar{border:1px solid #47688e;background:#192d45;border-radius:12px;padding:15px;display:grid;gap:12px;margin:16px 0}
.bqm-actionbar-grid{display:grid;grid-template-columns:minmax(140px,1fr) minmax(170px,1fr) auto;gap:10px;align-items:end}
.bqm-pages{display:flex;gap:12px;flex-wrap:wrap;justify-content:space-between;margin:18px 0}
.bqm-pages a{padding:9px 12px;background:#1b3856;border-radius:9px}
@media(max-width:730px){
.bqm-filter{grid-template-columns:1fr 1fr}
.bqm-filter label:first-child{grid-column:1 / -1}
.bqm-filter button{width:100%}
.bqm-actionbar-grid{grid-template-columns:1fr}
.bqm-actionbar button{width:100%}
.bqm-item{padding:12px}
}
</style>"""


def e(value):
    return escape(str(value if value is not None else ""), quote=True)


def initialize(db):
    # UI-only soft archive. Never mutate publishing states or original text.
    db.execute("""CREATE TABLE IF NOT EXISTS dashboard_hidden (
        kind TEXT NOT NULL CHECK(kind IN ('scout','originals','activity')),
        item_id TEXT NOT NULL, hidden_at TEXT NOT NULL,
        PRIMARY KEY (kind, item_id))""")


def fingerprint(*parts):
    return hashlib.sha256("\n".join(str(x or "") for x in parts).encode("utf-8")).hexdigest()


def _safeid(tab, ident):
    if tab == "originals":
        return bool(ID_ORIGINAL.fullmatch(ident))
    return bool(ID_SCOUT.fullmatch(ident))


def get_items(db, tab, records, status_fn):
    """Bound each source and disclose no credentials, private reports or API keys."""
    if tab not in TABS:
        raise ValueError("invalid tab")
    hidden = {row[0] for row in db.execute(
        "SELECT item_id FROM dashboard_hidden WHERE kind=?", (tab,))}
    result = []
    if tab == "scout":
        decisions = {row[0]: (row[1], row[2]) for row in db.execute(
            "SELECT run_id,draft_sha256,status FROM decisions")}
        jobs = {row[0]: (row[1], row[2]) for row in db.execute(
            "SELECT run_id,state,mode FROM publish_jobs")}
        for rec in records[:100]:
            rid = rec.get("run_id", "")
            if not isinstance(rid, str) or not _safeid(tab, rid):
                continue
            decision = status_fn(rec, decisions)
            job = jobs.get(rid)
            state = job[0] if job else decision
            token = rec.get("approval_sha256")
            if not isinstance(token, str) or not DIGEST.fullmatch(token):
                token = fingerprint("scout", rid, rec.get("draft_comment", ""))
            result.append(dict(id=rid, digest=token, status=state,
                               label=str(rec.get("chosen_title") or "Unparsed scouting result")[:160],
                               meta=str(rec.get("chosen_author") or "Unknown author")[:120],
                               summary=str(rec.get("draft_comment") or "No usable draft")[:4000],
                               source="scout", hidden=rid in hidden,
                               detail="/#run-" + rid, mode=job[1] if job else ""))
    elif tab == "originals":
        original_init(db)
        rows = db.execute(
            "SELECT id,title,content,digest,state,submolt,post_id FROM original_posts "
            "ORDER BY created_at DESC LIMIT 250")
        for rid,title,body,sha,state,submolt,pid in rows:
            if not _safeid(tab, rid):
                continue
            result.append(dict(id=rid, digest=sha, status=state, label=title,
                               meta="m/" + submolt, summary=body, source="originals",
                               hidden=rid in hidden, detail="/originals", mode="",
                               post_id=pid))
    else:
        rows = db.execute(
            "SELECT run_id,mode,state,draft_comment,created_at,post_id,comment_id "
            "FROM publish_jobs ORDER BY created_at DESC LIMIT 350")
        for rid,mode,state,body,created,pid,cid in rows:
            if not _safeid(tab, rid):
                continue
            result.append(dict(id=rid,
                               digest=fingerprint(rid,mode,state,body,created,pid,cid),
                               status=state, label="Comment " + rid,
                               meta=(mode or "") + " · " + (created or ""),
                               summary=body, source="activity", hidden=rid in hidden,
                               detail="/activity", mode=mode, comment_id=cid))
    return result


def parse_filters(params):
    def only(name, default):
        vals = params.get(name, [])
        return vals[0] if len(vals) == 1 else default
    tab = only("tab", "scout")
    tab = tab if tab in TABS else "scout"
    state = only("state", "all")
    state = state if state in STATES else "all"
    show = only("show", "active")
    show = show if show in SHOW else "active"
    search = only("q", "").strip()[:64]
    rawpage = only("page", "1")
    number = int(rawpage) if re.fullmatch(r"[1-9]\d{0,3}", rawpage) else 1
    return tab, state, show, search, number


def filtered(items, state, show, search):
    phrase = search.casefold()
    return [item for item in items
            if (state == "all" or item["status"] == state)
            and (show == "all" or item["hidden"] == (show == "archived"))
            and (not phrase or phrase in (item["label"] + " " + item["meta"] +
                                          " " + item["summary"]).casefold())]


def page(db, records, status_fn, params, csrf, wrap):
    initialize(db)
    tab,state,show,q,wanted_page = parse_filters(params)
    all_items = get_items(db, tab, records, status_fn)
    entries = filtered(all_items,state,show,q)
    total = len(entries)
    last = max(1, (total + PAGE_SIZE - 1)//PAGE_SIZE)
    current = min(wanted_page,last)
    visible = entries[(current-1)*PAGE_SIZE:current*PAGE_SIZE]
    def href(page_no, new_tab=None):
        return "/manage?" + urlencode(dict(tab=new_tab or tab,
                                         state=state if not new_tab else "all",
                                         show=show if not new_tab else "active",
                                         q=q if not new_tab else "",
                                         page=page_no))
    parts=[CSS,'<div class="bqm">',
           '<p class="bqm-info">Work from compact queues. Archives only hide items here; '
           'publication records and Moltbook content are preserved. '
           'Archiving a queued item does not cancel its future publication. '
           'Bulk “Queue” never submits a network request directly.</p>',
           '<nav class="bqm-tabs" aria-label="Queue categories">']
    for key in TABS:
        active = ' aria-current="page"' if key == tab else ""
        parts.append(f'<a href="{e(href(1,key))}"{active}>{e(TITLES[key])}</a>')
    parts.append('</nav><form class="bqm-filter" action="/manage" method="get">'
                 f'<input type="hidden" name="tab" value="{e(tab)}">'
                 f'<label>Search<input name="q" type="search" maxlength="64" value="{e(q)}" placeholder="Title, author, text"></label>'
                 '<label>Status<select name="state">')
    for value in STATES:
        chosen=" selected" if value==state else ""
        parts.append(f'<option value="{e(value)}"{chosen}>{e(value.title())}</option>')
    parts.append('</select></label><label>Visibility<select name="show">')
    for value in SHOW:
        chosen=" selected" if value==show else ""
        parts.append(f'<option value="{e(value)}"{chosen}>{e(value.title())}</option>')
    parts.append('</select></label><button type="submit">Filter</button></form>')
    pending=sum(item["status"] in ("pending","draft") and not item["hidden"] for item in all_items)
    archived=sum(item["hidden"] for item in all_items)
    parts.append(f'<p class="bqm-info"><strong>{total}</strong> matching · '
                 f'{pending} pending drafts · {archived} archived · Page {current} of {last}. '
                 'Select up to 10 items on this page.</p>')
    parts.append('<form class="bqm-bulk" action="/manage/bulk" method="post">'
                 f'<input type="hidden" name="csrf" value="{e(csrf)}">'
                 f'<input type="hidden" name="tab" value="{e(tab)}">'
                 f'<input type="hidden" name="state" value="{e(state)}">'
                 f'<input type="hidden" name="show" value="{e(show)}">'
                 f'<input type="hidden" name="q" value="{e(q)}">'
                 f'<input type="hidden" name="page" value="{current}">')
    for item in visible:
        label = e(item["label"])
        badges = (f'<span class="bqm-flag">{e(item["status"])}</span>'
                  + ('<span class="bqm-flag">Archived</span>' if item["hidden"] else '')
                  + (f'<span class="bqm-flag">{e(item["mode"])}</span>' if item["mode"] else ''))
        parts.append('<article class="bqm-item"><div class="bqm-item-head">'
                     f'<label class="bqm-check"><input type="checkbox" name="selected" '
                     f'value="{e(item["id"])}:{e(item["digest"])}" aria-label="Select {label}"></label>'
                     f'<div class="bqm-item-main"><h2>{label}</h2>{badges}'
                     f'<p class="bqm-info">{e(item["meta"])}</p>'
                     f'<details><summary>Read full content</summary><pre>{e(item["summary"])}</pre></details>'
                     f'<p><a href="{e(item["detail"])}">Open full item</a></p>'
                     '</div></div></article>')
    if not visible:
        parts.append('<p class="bqm-info">No matching items on this page.</p>')
    parts.append('<section class="bqm-actionbar"><strong>Apply to selected items</strong>'
                 '<p class="bqm-info">Approval/rejection is recorded locally. '
                 'Queue means request a future publication, not publish immediately. '
                 'Ineligible, stale or changed selections are refused together.</p>'
                 '<div class="bqm-actionbar-grid"><label>Operation<select name="operation">')
    names={"approve":"Approve drafts","reject":"Reject drafts","queue":"Queue approved for publishing",
           "archive":"Archive / hide","restore":"Restore from archive"}
    for op in ALLOWED[tab]:
        parts.append(f'<option value="{e(op)}">{e(names[op])}</option>')
    parts.append('</select></label><label>For Queue only, type QUEUE plus count '
                 '<input name="confirmation" autocomplete="off" maxlength="16" placeholder="e.g. QUEUE 2"></label>'
                 '<button type="submit">Apply to selected</button></div></section></form>')
    parts.append('<nav class="bqm-pages" aria-label="Result pages">')
    if current>1:
        parts.append(f'<a href="{e(href(current-1))}">Previous page</a>')
    parts.append(f'<span>Showing {len(visible)} of {total} matching items</span>')
    if current<last:
        parts.append(f'<a href="{e(href(current+1))}">Next page</a>')
    parts.append('</nav></div>')
    return wrap("Manage queues", "".join(parts), "/manage")


def apply_batch(db, records, status_fn, tab, operation, selected, confirmation):
    """Single atomic transaction, bounded and prevalidated before any changes.

    Caller MUST enforce local authentication, Origin, CSRF, request body size,
    and commit/rollback the SQLite transaction.
    """
    if tab not in TABS or operation not in ALLOWED[tab]:
        raise ValueError("unsupported bulk operation")
    if not 1 <= len(selected) <= MAX_SELECTED or len(selected) != len(set(selected)):
        raise ValueError("select 1 to 10 unique items")
    if operation == "queue" and confirmation != "QUEUE " + str(len(selected)):
        raise ValueError("type QUEUE followed by the selected count")
    initialize(db)
    all_items = {x["id"]: x for x in get_items(db,tab,records,status_fn)}
    checked = []
    for raw in selected:
        if not isinstance(raw,str) or len(raw) > 128 or ":" not in raw:
            raise ValueError("invalid selection")
        ident,digest = raw.split(":",1)
        if not _safeid(tab, ident) or not DIGEST.fullmatch(digest):
            raise ValueError("invalid selection ID")
        row = all_items.get(ident)
        if not row or row["digest"] != digest:
            raise ValueError("item changed since display; reload first")
        if operation == "archive" and row["hidden"]:
            raise ValueError("item already archived")
        if operation == "restore" and not row["hidden"]:
            raise ValueError("item is not archived")
        if operation in ("approve", "reject", "queue") and row["hidden"]:
            raise ValueError("restore archived item before changing decisions")
        if tab == "scout" and operation in ("approve", "reject", "queue"):
            obj = next((x for x in records if x.get("run_id")==ident),None)
            if not obj or not obj.get("verified_draft") or obj.get("approval_sha256") != digest:
                raise ValueError("scout draft not verified")
            if operation in ("approve", "reject") and row["status"]!="pending":
                raise ValueError("only pending drafts may be reviewed")
            if operation == "queue" and row["status"]!="approved":
                raise ValueError("only approved drafts without jobs may be queued")
        if tab == "originals" and operation in ("approve", "reject", "queue"):
            required = "approved" if operation == "queue" else "draft"
            if row["status"] != required:
                raise ValueError("original post not in eligible state")
        checked.append((ident,digest))
    # Avoid duplicate IDs hidden behind distinct snapshot fingerprints.
    if len({rid for rid,_ in checked}) != len(checked):
        raise ValueError("duplicate selection ID")
    now = datetime.now(timezone.utc).isoformat()
    for ident,digest in checked:
        if operation == "archive":
            db.execute("INSERT INTO dashboard_hidden(kind,item_id,hidden_at) VALUES(?,?,?)",
                       (tab,ident,now))
        elif operation == "restore":
            db.execute("DELETE FROM dashboard_hidden WHERE kind=? AND item_id=?",(tab,ident))
        elif tab == "scout":
            if operation == "queue":
                queue_manual(db, ident)
            else:
                db.execute("INSERT INTO decisions(run_id,draft_sha256,status,decided_at) "
                           "VALUES(?,?,?,?)",
                           (ident,digest,"approved" if operation=="approve" else "rejected",now))
        elif tab == "originals":
            original_transition(db,ident,"publish" if operation=="queue" else operation,digest)
    event(db, "dashboard_bulk_" + operation, f"{tab}: {len(checked)} items")
    return len(checked)
