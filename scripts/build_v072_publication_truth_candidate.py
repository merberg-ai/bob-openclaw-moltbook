#!/usr/bin/env python3
"""Build a precise UI wording fix over Bob's installed v0.7.2 tracking manager.

The original pinned manager is never rewritten in source control. This builder
changes display semantics only: a remote ACK isn't proof of public visibility.
"""
from __future__ import annotations
import build_v072_live_candidate as prior

def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("unexpected dashboard source: refusing edit")
    return source.replace(old, new, 1)

def build():
    manager, navigation = prior.build()
    source = manager.decode("utf-8")
    source = replace_once(
        source,
        "    comm_pub=sum(x[2]=='published' for x in comments)\n    orig_pub=sum(x[2]=='published' for x in originals)",
        """    comm_pub=sum(x[2]=='published' and isinstance(x[4],str) and UUID.fullmatch(x[4]) is not None for x in comments)
    uncertain_pub=sum(x[2] in ('published','verified_unconfirmed') and not (isinstance(x[4],str) and UUID.fullmatch(x[4])) for x in comments)
    orig_pub=sum(x[2]=='published' and bool(x[6]) for x in originals)""")
    source = replace_once(
        source,
        'Confirmed comment jobs</div>\'\n           f\'<div class="stat"><strong>{orig_pub}</strong>Confirmed original post jobs',
        'API-acknowledged comments with IDs (visibility unverified)</div>\'\n           f\'<div class="stat"><strong>{orig_pub}</strong>Publicly visible original post jobs')
    source = replace_once(
        source,
        'f\'<div class="stat"><strong>{orig_pub}</strong>Publicly visible original post jobs',
        'f\'<div class="stat"><strong>{uncertain_pub}</strong>Comments without confirmed IDs</div>\'\n           f\'<div class="stat"><strong>{orig_pub}</strong>Publicly visible original post jobs')
    source = replace_once(
        source,
        '“Published” means the API acknowledged the item; original posts are separately checked for public visibility.',
        'An API acknowledgment does not prove a comment is publicly visible. Comments without IDs are unconfirmed; original posts have a separate public visibility check.')
    anchor = """    for rid,mode,state,pid,cid,body,created,attempted,error in comments:
        pieces.append(f'<article class="card"><b>Comment</b> <span class="pill">{esc(state)}</span> '
                      f'<span class="pill">{esc(mode)}</span><p class="meta">{esc(attempted or created)} · Comment ID: {esc(cid or "not confirmed")}</p>'
                      f'<pre>{esc(body)}</pre>{link(pid)}'
                      +(f'<p class="meta">Issue: {esc(error)}</p>' if error else '')+'</article>')"""
    new = """    for rid,mode,state,pid,cid,body,created,attempted,error in comments:
        has_id=isinstance(cid,str) and UUID.fullmatch(cid) is not None
        label=('ID unconfirmed; visibility unknown' if state in ('published','verified_unconfirmed') and not has_id
               else 'API acknowledged; visibility unchecked' if state=='published' and has_id
               else 'Cancelled before sending' if state=='cancelled' else state)
        context=('Auto queued comment canceled; not sent.' if mode=='auto' and state=='cancelled'
                 else 'Do not requeue automatically.' if state in ('published','verified_unconfirmed','uncertain') else '')
        pieces.append(f'<article class="card"><b>Comment</b> <span class="pill">{esc(label)}</span> '
                      f'<span class="pill">{esc(mode)}</span><p class="meta">{esc(attempted or created)} · Comment ID: {esc(cid or "not confirmed")}</p>'
                      +(f'<p class="meta">{esc(context)}</p>' if context else '')
                      +f'<pre>{esc(body)}</pre>{link(pid)}'
                      +(f'<p class="meta">Issue: {esc(error)}</p>' if error else '')+'</article>')"""
    source = replace_once(source, anchor, new)
    compile(source, "bob-activity-manager", "exec")
    return source.encode("utf-8"), navigation

if __name__ == "__main__":
    manager, nav = build()
    print("v0.7.2 PUBLICATION TRUTH CANDIDATE: PASS")
    print("manager_bytes:", len(manager), "navigation_bytes:", len(nav))
    print("production_modified: NO")
