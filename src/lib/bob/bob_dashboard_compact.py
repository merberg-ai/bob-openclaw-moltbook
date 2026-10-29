"""Compact, paginated Scout and Activity views for the existing Bob dashboard.

GET-only rendering. Reuses approved single-item POST routes, existing review
hashes and current private archive flags. Does not invoke publishers, change
approval state, or access Moltbook credentials.
"""
from __future__ import annotations

from html import escape
import re
from urllib.parse import urlencode

from bob_dashboard_manage import get_items, filtered, initialize as hidden_init
from bob_originals import initialize as original_init
from bob_publish_common import setting, UUID
from bob_activity_limits import summary as limit_summary

PAGE_SIZE = 8
SCOUT_STATES = ("pending", "all", "approved", "rejected", "needs review",
                "queued", "awaiting_verification", "published", "failed", "cancelled")
ACTIVITY_VIEWS = ("comments", "originals", "replies", "events")
ACTIVITY_STATES = ("all", "queued", "published", "verified_unconfirmed",
                   "awaiting_verification", "uncertain", "failed", "cancelled",
                   "draft", "approved", "rejected")
VISIBILITY = ("active", "archived", "all")

CSS = """<style>
.bcv{max-width:1030px;margin:0 auto}
.bcv-bar{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:16px 0}
.bcv-bar a,.bcv-page a{display:inline-block;background:#203851;border:1px solid #3d5878;
color:#ddebff;border-radius:9px;text-decoration:none;padding:9px 13px;min-height:44px}
.bcv-bar a[aria-current=page]{background:#2d5d8b;color:#fff}
.bcv-note{color:#b5c6dc;font-size:.9rem;line-height:1.5}
.bcv-stats{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}
.bcv-stat{background:#172a40;border:1px solid #334d6d;padding:9px 13px;border-radius:10px;font-size:.9rem}
.bcv-stat b{font-size:1.08rem;margin-right:5px}
.bcv-filter{display:grid;grid-template-columns:minmax(120px,2fr) repeat(2,minmax(120px,1fr)) auto;gap:9px;align-items:end;
margin:16px 0;padding:13px;border:1px solid #314d6c;border-radius:12px;background:#142238}
.bcv-filter label{display:grid;gap:6px;font-size:.88rem;font-weight:700}
.bcv-filter :is(select,input),.bcv :is(input,button){box-sizing:border-box;max-width:100%;min-height:44px;font:inherit;border-radius:8px}
.bcv-filter :is(select,input),.bcv input{width:100%;padding:8px;background:#0c1a2b;border:1px solid #526f92;color:#eff6ff}
.bcv button{min-height:44px;padding:9px 14px;background:#29618d;color:#fff;border:1px solid #739fca;border-radius:9px;cursor:pointer;font-weight:700}
.bcv button.reject{background:#66343c;border-color:#c17a83}
.bcv button.reset{background:#314560}
.bcv-card{border:1px solid #324a68;background:#132238;border-radius:13px;padding:15px;margin:11px 0}
.bcv-card h2{font-size:1.08rem;margin:5px 0 8px;overflow-wrap:anywhere}
.bcv-card p{margin:7px 0;overflow-wrap:anywhere}
.bcv-pill{display:inline-block;border:1px solid #496b8b;border-radius:15px;font-size:.78rem;padding:3px 9px;margin:3px 5px 4px 0}
.bcv-card details,.bcv-control details{margin-top:9px;padding-top:9px;border-top:1px solid #34506a}
.bcv-card summary,.bcv-control summary{cursor:pointer;color:#abd5ff;min-height:36px}
.bcv-card pre{max-height:310px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;
background:#0c1728;border:1px solid #2c4565;border-radius:9px;padding:12px;font-size:.85rem}
.bcv-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:end;margin:12px 0 3px}
.bcv-actions form{margin:0}
.bcv-page{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:20px 0}
.bcv-control{padding:13px;border:1px solid #334c68;background:#17283e;border-radius:12px;margin:10px 0}
.bcv-verify{display:grid;gap:8px;max-width:420px}
.bcv-verify input{display:block;margin:8px 0}
@media(max-width:720px){
.bcv-filter{grid-template-columns:1fr 1fr}
.bcv-filter label:first-child{grid-column:1/-1}
.bcv-filter button{width:100%}
.bcv-card{padding:12px}
.bcv-actions form{flex:1 1 130px}
.bcv-actions button{width:100%}
.bcv-bar a{flex:1 1 auto;text-align:center}
}
</style>"""


def e(value):
    return escape(str(value if value is not None else ""), quote=True)


def only(params, key, default, *, max_length=64):
    values = params.get(key, [])
    if len(values) != 1 or not isinstance(values[0], str):
        return default
    return values[0][:max_length]


def page_number(params):
    raw = only(params, "page", "1", max_length=5)
    return int(raw) if re.fullmatch(r"[1-9]\d{0,3}", raw) else 1


def paging(entries, params, base, filters):
    total = len(entries)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    number = min(total_pages, page_number(params))
    subset = entries[(number-1)*PAGE_SIZE:number*PAGE_SIZE]
    def link(target):
        return base + "?" + urlencode({**filters, "page": target})
    links = ['<nav class="bcv-page" aria-label="Pages">']
    if number > 1:
        links.append(f'<a href="{e(link(number-1))}">Previous</a>')
    links.append(f'<span class="bcv-note">Page {number} of {total_pages} · {total} matching</span>')
    if number < total_pages:
        links.append(f'<a href="{e(link(number+1))}">Next</a>')
    links.append('</nav>')
    return subset, "".join(links)


def filters_form(base, values, states, *, show_visibility=True):
    q = values.get("q", "")
    state = values.get("state", "all")
    show = values.get("show", "active")
    pieces = [f'<form class="bcv-filter" method="get" action="{e(base)}">']
    for name, value in values.items():
        if name not in ("q", "state", "show"):
            pieces.append(f'<input type="hidden" name="{e(name)}" value="{e(value)}">')
    pieces.append(f'<label>Search<input type="search" name="q" maxlength="64" '
                  f'value="{e(q)}" placeholder="Find title or text"></label>'
                  '<label>Status<select name="state">')
    for entry in states:
        pieces.append(f'<option value="{e(entry)}"'
                      + (' selected' if entry == state else '')
                      + f'>{e(entry.title())}</option>')
    pieces.append('</select></label>')
    if show_visibility:
        pieces.append('<label>Visibility<select name="show">')
        for value in VISIBILITY:
            pieces.append(f'<option value="{value}"'
                          + (' selected' if value == show else '')
                          + f'>{e(value.title())}</option>')
        pieces.append('</select></label>')
    else:
        pieces.append('<input type="hidden" name="show" value="active">')
    pieces.append('<button type="submit">Filter</button></form>')
    return "".join(pieces)


def action_form(action, ident, digest, csrf, label, cls="", return_to="/scout"):
    return (f'<form method="post" action="{e(action)}">'
            f'<input type="hidden" name="csrf" value="{e(csrf)}">'
            f'<input type="hidden" name="digest" value="{e(digest)}">'
            f'<input type="hidden" name="return_to" value="{e(return_to)}">'
            f'<button type="submit" class="{e(cls)}">{e(label)}</button></form>')


def scout_page(db, records, status_fn, params, csrf, wrap):
    hidden_init(db)
    state = only(params,"state","pending",max_length=32)
    if state not in SCOUT_STATES:
        state = "pending"
    show = only(params,"show","active",max_length=12)
    if show not in VISIBILITY:
        show = "active"
    search = only(params,"q","").strip()
    items = get_items(db,"scout",records,status_fn)
    shown = filtered(items,state,show,search)
    page_items, controls = paging(shown,params,"/scout",dict(state=state,show=show,q=search))
    return_to = "/scout?" + urlencode(dict(
        state=state, show=show, q=search, page=page_number(params)))
    by_id = {r["run_id"]:r for r in records if isinstance(r.get("run_id"),str)}
    counts = {s: sum(x["status"] == s for x in items) for s in
              ("pending","approved","rejected","needs review")}
    archived = sum(x["hidden"] for x in items)
    auto_on = setting(db,"auto_enabled","0") == "1"
    limits_today = limit_summary(db)
    daily = limits_today['limits']['comment_daily']
    spacing = limits_today['limits']['comment_gap_minutes']
    auto_daily = limits_today['limits']['comment_auto_daily']
    h = [CSS,'<div class="bcv"><p class="bcv-note">Review drafts without '
         'scrolling through entire agent reports. Expand a draft to read it, '
         'or open the full original view for additional context.</p>',
         '<div class="bcv-bar"><a href="/manage?tab=scout&state=pending&show=all">'
         'Manage multiple drafts</a><a href="/scout/full">Full Scout history</a></div>',
         '<div class="bcv-stats">',
         f'<span class="bcv-stat"><b>{counts["pending"]}</b>Pending review</span>',
         f'<span class="bcv-stat"><b>{counts["approved"]}</b>Approved</span>',
         f'<span class="bcv-stat"><b>{counts["rejected"]}</b>Rejected</span>',
         f'<span class="bcv-stat"><b>{counts["needs review"]}</b>Needs repair</span>',
         f'<span class="bcv-stat"><b>{archived}</b>Archived in Manage</span>',
         '</div>',
         '<section class="bcv-control"><b>Autonomous comments: ',
         'ON' if auto_on else 'OFF','</b><p class="bcv-note">'
         f'Total budget: {daily} comments/day, at least {spacing} minutes apart; '
         f'automatic budget: {auto_daily}/day. '
         'Manual reviews and original posts retain separate permission rules.</p>',
         '<details><summary>Change autonomous comment setting</summary>']
    if auto_on:
        h.append(f'<form method="post" action="/autopost/disable">'
                 f'<input type="hidden" name="csrf" value="{e(csrf)}">'
                 f'<input type="hidden" name="return_to" value="{e(return_to)}">'
                 '<button type="submit" class="reject">Disable autonomous replies</button></form>')
    else:
        h.append(f'<form method="post" action="/autopost/enable">'
                 f'<input type="hidden" name="csrf" value="{e(csrf)}">'
                 f'<input type="hidden" name="return_to" value="{e(return_to)}">'
                 '<label>Type ENABLE AUTO <input name="confirmation" maxlength="20" '
                 'autocomplete="off" required></label><button type="submit">Enable</button></form>')
    h.append('</details></section>')
    h.append(filters_form("/scout",dict(state=state,show=show,q=search),SCOUT_STATES))
    pending_hidden = sum(x["hidden"] and x["status"]=="pending" for x in items)
    h.append(f'<p class="bcv-note">{len(shown)} matching · {pending_hidden} pending archived '
             '(switch Visibility to All to see them). '
             'Archiving does not cancel queued publication.</p>')
    for item in page_items:
        rid = item["id"]
        rec = by_id.get(rid)
        if rec is None:
            continue
        status = item["status"]
        job = item["publication_state"]
        meta = f'Review: {e(status)}'
        if job:
            meta += f' · Publication: {e(job)} ({e(item["mode"])})'
        if item["hidden"]:
            meta += ' · Archived'
        h.append(f'<article class="bcv-card" id="run-{e(rid)}">'
                 f'<div class="bcv-note">{e(rid)} · {meta}</div>'
                 f'<h2>{e(item["label"])}</h2>'
                 f'<p class="bcv-note">By {e(item["meta"])}</p>'
                 f'<p>{e(str(rec.get("why") or "No selection rationale recorded")[:240])}</p>'
                 '<details><summary>Read Bob’s draft (not necessarily published)</summary>'
                 f'<pre>{e(item["summary"])}</pre></details>')
        errors = rec.get("validation_errors")
        if isinstance(errors,list) and errors:
            h.append('<p class="bcv-note">Validation: '
                     +e("; ".join(map(str,errors))[:380])+'</p>')
        verified = rec.get("verified_draft") and rec.get("status")=="pending"
        digest = rec.get("approval_sha256","")
        if verified and isinstance(digest,str) and re.fullmatch(r"[0-9a-f]{64}",digest):
            h.append('<div class="bcv-actions">')
            if status=="pending":
                h.append(action_form(f"/review/{rid}/approve",rid,digest,csrf,"Approve",return_to=return_to))
                h.append(action_form(f"/review/{rid}/reject",rid,digest,csrf,"Reject","reject",return_to=return_to))
            elif status in ("approved","rejected"):
                h.append(action_form(f"/review/{rid}/reset",rid,digest,csrf,"Return to pending","reset",return_to=return_to))
            if status=="approved" and not job:
                h.append(action_form(f"/publish/{rid}",rid,digest,csrf,
                                     "Queue approved comment",return_to=return_to))
                h.append('<span class="bcv-note">Queueing may lead to a real '
                         'publication when eligible.</span>')
            h.append('</div>')
        if job=="awaiting_verification":
            h.append(f'<form class="bcv-verify" method="post" action="/verify/{e(rid)}">'
                     f'<input type="hidden" name="csrf" value="{e(csrf)}">'
                     f'<input type="hidden" name="return_to" value="{e(return_to)}">'
                     '<label>Verification challenge: answer with two decimals'
                     '<input name="answer" maxlength="16" placeholder="15.00" required></label>'
                     '<button type="submit">Submit challenge answer once</button></form>')
        h.append(f'<p><a href="/scout/full#run-{e(rid)}">Open full draft, '
                 'external excerpt and report</a></p></article>')
    if not page_items:
        h.append('<section class="bcv-card"><p>No matching scout drafts. '
                 'Check your Status and Visibility filters, or open Manage Queues '
                 'to restore archived items.</p></section>')
    h.append(controls)
    h.append('<p class="bcv-note">Direct replies and publication events have '
             'moved to the <a href="/activity">Activity</a> page. '
             'All historical reports remain available in the full view.</p></div>')
    return wrap("Scout & review","".join(h),"/scout")


def activity_page(db, params, wrap):
    hidden_init(db)
    original_init(db)
    view = only(params,"view","comments",max_length=16)
    if view not in ACTIVITY_VIEWS:
        view = "comments"
    state = only(params,"state","all",max_length=40)
    if state not in ACTIVITY_STATES:
        state = "all"
    show = only(params,"show","active",max_length=12)
    if show not in VISIBILITY:
        show = "active"
    search = only(params,"q","").strip()
    totals = {
        "comments": db.execute("SELECT count(*) FROM publish_jobs").fetchone()[0],
        "originals": db.execute("SELECT count(*) FROM original_posts").fetchone()[0],
        "replies": (db.execute("SELECT count(*) FROM published_replies").fetchone()[0]
                    + db.execute("SELECT count(*) FROM original_post_replies").fetchone()[0]),
        "events": db.execute("SELECT count(*) FROM publish_events").fetchone()[0],
    }
    h = [CSS,'<div class="bcv"><p class="bcv-note">Local publication history. '
         'An API-acknowledged comment is <b>not</b> automatically confirmed '
         'publicly visible. This page never triggers posting.</p>',
         '<nav class="bcv-bar" aria-label="Activity categories">']
    for v, label in (("comments","Comments"),("originals","Original posts"),
                     ("replies","Incoming replies"),("events","Event log")):
        active = ' aria-current="page"' if view==v else ""
        h.append(f'<a href="/activity?view={v}"{active}>{label} '
                 f'({totals[v]})</a>')
    h.append('</nav>')
    h.append('<p class="bcv-note"><a href="/manage?tab=activity">Manage '
             'comment records and archives</a> · '
             '<a href="/activity/full">Full legacy activity view</a></p>')
    if view in ("comments","originals"):
        items = get_items(db,"activity" if view=="comments" else "originals",
                          [],lambda r, d: "pending")
        shown = filtered(items,state,show,search)
    else:
        state = "all"
        show = "active"
        if view=="replies":
            rows = []
            for table, source in (("published_replies","Direct reply"),
                                  ("original_post_replies","Reply on original post")):
                rows.extend(dict(label=f"{source}: {author or 'Unknown'}",
                                 summary=str(content or ""), meta=str(detected or ""),
                                 status="reply", link=pid)
                            for author,content,pid,detected in db.execute(
                                f"SELECT author,content,post_id,detected_at FROM {table} "
                                "ORDER BY detected_at DESC LIMIT 150"))
            rows.sort(key=lambda x:x["meta"],reverse=True)
        else:
            rows = [dict(label=str(kind or ""),summary=str(details or ""),
                         meta=str(at or ""),status="event",link=None)
                    for at,kind,details in db.execute(
                        "SELECT at,kind,details FROM publish_events "
                        "ORDER BY id DESC LIMIT 200")]
        shown = [i for i in rows
                 if not search.casefold() or search.casefold() in
                 (i["label"]+" "+i["summary"]+" "+i["meta"]).casefold()]
    h.append(filters_form("/activity",
                dict(view=view,state=state,show=show,q=search),
                ACTIVITY_STATES if view in ("comments","originals") else ("all",),
                show_visibility=view in ("comments","originals")))
    if view in ("replies","events"):
        h.append('<p class="bcv-note">Showing a bounded recent-history window '
                 '(up to 300 replies or 200 events). Older entries remain in '
                 'the original database.</p>')
    displayed, controls = paging(shown,params,"/activity",
                                  dict(view=view,state=state,show=show,q=search))
    h.append(f'<p class="bcv-note">{len(shown)} matching in {view}.</p>')
    for item in displayed:
        title = item["label"]
        status = item.get("status","")
        info = item.get("meta","")
        summary = item.get("summary","")
        h.append(f'<article class="bcv-card"><h2>{e(title)}</h2>'
                 f'<span class="bcv-pill">{e(status)}</span>'
                 f'<p class="bcv-note">{e(info)}</p>')
        if view=="comments":
            cid = item.get("comment_id")
            if status=="published":
                h.append('<p class="bcv-note">API acknowledged; public visibility '
                         'not independently confirmed.</p>')
            elif status=="verified_unconfirmed":
                h.append('<p class="bcv-note">Comment ID unconfirmed; '
                         'do not automatically retry.</p>')
            if cid:
                h.append(f'<p class="bcv-note">Comment ID: {e(cid)}</p>')
            h.append(f'<span class="bcv-pill">Mode: {e(item.get("mode") or "unknown")}</span>')
        elif view=="originals":
            h.append('<p class="bcv-note">View publication details and independent '
                     'visibility check on the full Original Posts page.</p>')
        if item.get("hidden"):
            h.append('<span class="bcv-pill">Archived</span>')
        if summary:
            h.append('<details><summary>Read content</summary>'
                     f'<pre>{e(summary)}</pre></details>')
        pid = item.get("link") if view in ("replies","events") else item.get("post_id")
        if isinstance(pid,str) and UUID.fullmatch(pid):
            h.append(f'<p><a href="https://www.moltbook.com/post/{e(pid)}" '
                     'rel="noreferrer" target="_blank">Open discussion</a></p>')
        if view=="originals":
            h.append('<p><a href="/originals">View original post controls</a></p>')
        h.append('</article>')
    if not displayed:
        h.append('<section class="bcv-card"><p>No matching activity in this '
                 'section. Adjust the filters or select another category.</p></section>')
    h.append(controls)
    h.append('</div>')
    return wrap("Published activity","".join(h),"/activity")
