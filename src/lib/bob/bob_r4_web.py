"""R4 authenticated, mobile-first multi-page Activity Manager extension.

Only the trusted HTTPS Handler wraps this mixin. Existing routes and source
identity/CSRF checks are inherited, not reimplemented as an open HTTP server.
No Moltbook credentials, POST to Moltbook, model prompts or worker invocations.
Owner Forms only stage reviewed R4 preferences and pause in existing SQLite.
"""
from __future__ import annotations

from html import escape
import hmac
import re
import sqlite3
from urllib.parse import parse_qs,urlsplit

from bob_publish_common import connect as publish_conn
from bob_r4_controls import ACTIONS,CAPS,read_modes,set_mode,pause_state,set_pause
from bob_r4_projection import snapshot

PAGES=frozenset((
    "/r4","/r4/now","/r4/inbox","/r4/bob",
    "/r4/controls","/r4/diagnostics","/r4/chat"))
PANEL={
    "/r4":"now","/r4/now":"now","/r4/inbox":"inbox",
    "/r4/bob":"bob","/r4/controls":"controls",
    "/r4/diagnostics":"diagnostics","/r4/chat":"chat"}
ACTION_URL=re.compile(
    r"/r4/controls/(comment|reply|post|upvote|follow|unfollow)\Z")
REVIEW_URL=re.compile(
    r"/r4/review/(\d{8}T\d{6}Z)/(approve|reject)\Z")
OUTBOX_URL=re.compile(
    r"/r4/outbox/(\d{8}T\d{6}Z)/(queue|cancel)\Z")
SUGGEST_URL=re.compile(
    r"/r4/suggestion/(\d{8}T\d{6}Z)/(memory|relationship)/(approve|reject)\Z")
CSS="""<style>
.r4{max-width:1120px;margin:0 auto;display:grid;gap:15px;color:#ebf4ff}
.r4 *{box-sizing:border-box;min-width:0}
.r4 h2{font-size:clamp(1.26rem,3vw,1.65rem);margin:0}
.r4 h3{font-size:1rem;margin:0 0 8px}
.r4 p,.r4 td,.r4 code{overflow-wrap:anywhere}
.r4 pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:300px;
  overflow-y:auto;padding:12px;border-radius:9px;background:#0b182b;
  border:1px solid #335371;font:0.8rem/1.5 ui-monospace,monospace}
.r4 .panel form{margin:13px 0;display:grid;gap:9px}
.r4 .muted{font-size:.83rem;color:#b7cbe1;line-height:1.55}
.r4 .tabs{display:flex;gap:7px;flex-wrap:wrap;padding-bottom:4px}
.r4 .tabs a{padding:11px 14px;border:1px solid #425c78;
  background:#142944;border-radius:11px;color:#d9eeff;text-decoration:none;
  font-size:.85rem;min-height:44px}
.r4 .tabs [aria-current=page]{background:#245b89;border-color:#82b9e0;color:#fff}
.r4 .panel{padding:clamp(13px,2.5vw,22px);background:#101f34;
  border:1px solid #314b6a;border-radius:13px}
.r4 .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.r4 .stat{border:1px solid #3c5673;border-radius:10px;
  padding:12px;background:#172a42}
.r4 .stat strong{font-size:1.45rem;display:block}
.r4 .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.r4 ul{padding-left:19px;line-height:1.6}
.r4 li{margin:7px 0;overflow-wrap:anywhere}
.r4 .mode-list{display:grid;gap:10px}
.r4 .mode{display:grid;grid-template-columns:minmax(100px,1fr) 90px;
  align-items:center;gap:10px;border:1px solid #3a5779;
  border-radius:10px;padding:13px;background:#14283f}
.r4 .mode form{grid-column:1/-1;display:grid;
  grid-template-columns:minmax(110px,160px) minmax(0,1fr) auto;
  gap:9px;align-items:end}
.r4 label{display:grid;gap:4px;font-size:.83rem}
.r4 input,.r4 select{padding:10px;background:#0b1b2e;
  border:1px solid #6784a7;border-radius:8px;color:#fff;
  min-height:44px;width:100%;font:inherit}
.r4 button{padding:10px 15px;border-radius:8px;min-height:44px;
  border:1px solid #78b1d8;background:#24618b;color:#fff;cursor:pointer;
  font:inherit}
.r4 .badge{font-size:.78rem;background:#253f59;border:1px solid #476f93;
  border-radius:999px;padding:4px 9px;text-align:center}
.r4 .pill{display:inline-block;margin-right:6px;padding:2px 7px;
  border:1px solid #4d7294;border-radius:9px;font-size:.74rem}
.r4 .tablewrap{overflow-x:auto}
.r4 table{border-collapse:collapse;min-width:490px;width:100%;
  font-size:.8rem;table-layout:fixed}
.r4 th,.r4 td{padding:9px 7px;border-bottom:1px solid #344d6a;text-align:left}
.r4 a{color:#b7ddff}
.r4 :is(a,button,input,select):focus-visible{outline:3px solid #ffd083;
  outline-offset:3px}
@media(max-width:680px){
 .r4 .stats{grid-template-columns:repeat(2,minmax(0,1fr))}
 .r4 .grid{grid-template-columns:1fr}
 .r4 .mode form{grid-template-columns:1fr}
 .r4 button{width:100%}
}
@media(max-width:380px){
 .r4 .stats{grid-template-columns:1fr 1fr;gap:7px}
 .r4 .stat{padding:9px}
 .r4 .tabs a{flex:1 1 45%;text-align:center;padding:10px 8px}
 .r4 .panel{padding:11px}
 .r4 h2{font-size:1.14rem}
}
@media(prefers-reduced-motion:reduce){.r4 *{scroll-behavior:auto}}
</style>"""


def e(item):
    return escape(str(item if item is not None else ""),quote=True)


def _nav(active: str):
    items=[("now","Now"),("inbox","Inbox"),("bob","Bob"),
           ("controls","Controls"),("diagnostics","Diagnostics"),
           ("chat","Chat (later)")]
    return '<nav class="tabs" aria-label="Bob R4 sections">'+''.join(
        '<a href="/r4/'+key+'"'+(
            ' aria-current="page"' if key==active else "")+'>'+e(label)+'</a>'
        for key,label in items)+'</nav>'


def _notice(data):
    return (
        '<p class="muted">Evidence-based local view. Reading or setting R4 '
        'preferences does not create a Moltbook action. A one-time R3 canary '
        'never grants ongoing R4 permissions. Public visibility is not '
        'rechecked on this page.</p>'
        if data["available"] else
        '<p class="muted">Private Bob queue unavailable or untrusted. '
        'All controls are treated as Off; nothing is dispatched.</p>')


def _stat(number,label):
    return '<div class="stat"><strong>'+e(number)+'</strong><span class="muted">'+e(label)+'</span></div>'


def _now(data):
    parts=['<section class="panel"><h3>Recorded activity, not inferred behavior</h3>',
           '<div class="stats">',
           _stat(data["r3_proposed_recorded"],"Open R3 proposals (recorded)"),
           _stat(data["attempted"],"Local comment attempts"),
           _stat(data["publisher_jobs"],"Historical comment jobs"),
           _stat(data["originals"],"Original post records"),
           _stat(data["saved_friends"],"Local active contacts"),
           _stat(data["saved_memories"],"Owner-entered memories"),
           '</div><p class="muted">R3 public canary receipts live in the '
           'read-only acceptance log; a local API acknowledgment alone does '
           'not constitute fresh remote proof.</p></section>',
           '<section class="panel"><h3>Most recent publisher jobs</h3>',
           _jobs(data),'</section>',
           '<section class="panel"><h3>Working surfaces</h3>'
           '<p><a href="/r3">Review exact Bob R3 drafts</a> · '
           '<a href="/api/system/status">Read-only live system status</a> · '
           '<a href="/moltbook/social-memory">Source-linked social history</a>'
           '</p></section>']
    return ''.join(parts)


def _jobs(data):
    if not data["recent_jobs"]:
        return '<p class="muted">No readable publisher queue records.</p>'
    items=[]
    for j in data["recent_jobs"]:
        items.append('<tr><td><code>'+e(j["source_run"])+'</code></td>'
                     '<td>'+e(j["state"])+'</td><td>'+
                     ('yes' if j["attempt_recorded"] else 'no')+'</td>'
                     '<td>not checked</td></tr>')
    return '<div class="tablewrap"><table><thead><tr><th>Source</th><th>Local state</th><th>Attempt</th><th>Public</th></tr></thead><tbody>'+''.join(items)+'</tbody></table></div>'


def _suggestion_cards(data,csrf):
    cards=[]
    for item in data.get("r4_suggestions",[])[:12]:
        run=e(item["source_run"])
        kind=e(item["kind"])
        state=e(item["state"])
        parts=[
            '<article class="panel"><h3>Bob suggested '+kind+': '+
            e(item["title"])+'</h3>',
            '<p class="muted">Sealed source <code>'+run+
            '</code> · original @'+e(item["source_author"])+
            ' · review '+state+'</p>',
            '<p>'+e(item["detail"])+'</p>',
            '<p class="muted">This is a Bob-authored interpretation, not '
            'an established fact. Memory approval creates a low-confidence '
            'owner-reviewed PM2 opinion. Relationship approval sends a '
            'candidate to the existing Friend Discovery review, not the '
            'Friends directory or Moltbook following.</p>'
        ]
        if item["state"]=="pending":
            operations=[("reject","Reject suggestion")]
            if item["social_state"]!="rejected":
                operations.insert(0,("approve","Approve suggestion"))
            for operation,label in operations:
                phrase=(operation.upper()+" R4 "+item["kind"].upper()+
                        " "+item["source_run"])
                parts.append(
                    '<form method="post" action="/r4/suggestion/'+run+'/'+
                    kind+'/'+operation+'">'
                    '<input type="hidden" name="csrf" value="'+e(csrf)+'">'
                    '<input type="hidden" name="seal" value="'+e(item["seal"])+
                    '"><label>Type '+e(phrase)+
                    '<input name="confirmation" autocomplete="off" '
                    'maxlength="64" required></label>'
                    '<button type="submit">'+e(label)+'</button></form>')
        if item["state"]=="pending" and item["social_state"]=="rejected":
            parts.append('<p class="muted">Original social proposal rejected; '
                         'this suggestion may only be rejected, not approved.</p>')
        if item["applied_ref"]:
            parts.append('<p class="muted">Saved local reference: <code>'+
                         e(item["applied_ref"])+'</code></p>')
        parts.append('</article>')
        cards.append(''.join(parts))
    return ('<section class="panel"><h3>Bob&#39;s memory and relationship '
            'suggestions</h3><p class="muted">Owner confirmation is required '
            'before any local PM2 memory or Friend Discovery candidate '
            'is created. No direct network follow or publication.</p></section>'+
            (''.join(cards) if cards else
             '<section class="panel"><p>No independently verified R4 '
             'evidence suggestions available.</p></section>'))


def _inbox(data,csrf):
    cards=[]
    for item in data.get("r4_recent",[])[:12]:
        run=e(item["run"])
        seal=e(item["seal"])
        state=e(item["state"])
        parts=[
            '<article class="panel"><h3>'+e(item["kind"].title())+
            ' · '+e(item["source_title"])+'</h3>',
            '<p class="muted">Bob R4 source <code>'+run+'</code> · observed @'+
            e(item["source_author"])+' · review state <strong>'+state+
            '</strong></p>',
            '<p><strong>Bob&#39;s reason:</strong> '+e(item["reason"])+'</p>',
        ]
        if item["body"]:
            parts.append('<pre class="r4-draft">'+e(item["body"])+'</pre>')
        if item["title"]:
            parts.append('<p>Proposed title: '+e(item["title"])+'</p>')
        parts.append('<p class="muted">Exact seal <code>'+seal+
                     '</code>. R4 approval records owner review only. '
                     'It does not queue a post or enable public dispatch.</p>')
        # A second separately typed owner decision is required to stage even
        # an approved R4 upvote in the private queue. R4 public sends remain
        # compiled Off; this button is not a publish button.
        outbox_state=item.get("outbox_state","none")
        if item["state"]=="approved" and item["kind"]=="upvote":
            if outbox_state=="none":
                phrase="QUEUE R4 UPVOTE "+item["run"]
                parts.append(
                    '<form method="post" action="/r4/outbox/'+run+'/queue">'
                    '<input type="hidden" name="csrf" value="'+e(csrf)+'">'
                    '<input type="hidden" name="seal" value="'+seal+'">'
                    '<label>Type '+e(phrase)+'<input name="confirmation" '
                    'autocomplete="off" maxlength="60" required></label>'
                    '<button type="submit">Queue privately (R4 send Off)</button>'
                    '</form>')
            elif outbox_state=="queued":
                phrase="CANCEL R4 "+item["run"]
                parts.append(
                    '<p class="muted">Queued privately. No API send is '
                    'authorized by this release.</p>'
                    '<form method="post" action="/r4/outbox/'+run+'/cancel">'
                    '<input type="hidden" name="csrf" value="'+e(csrf)+'">'
                    '<input type="hidden" name="seal" value="'+seal+'">'
                    '<label>Type '+e(phrase)+'<input name="confirmation" '
                    'autocomplete="off" maxlength="60" required></label>'
                    '<button type="submit">Cancel untouched queue</button>'
                    '</form>')
            else:
                parts.append('<p class="muted">R4 outbox state: '+
                             e(outbox_state)+'. Already processed or cancelled; '
                             'no automatic retry.</p>')
        if item["state"]=="proposed":
            for operation,label in (("approve","Approve private proposal"),
                                    ("reject","Reject private proposal")):
                confirm=operation.upper()+" R4 "+item["run"]
                parts.append(
                    '<form method="post" action="/r4/review/'+run+'/'+
                    operation+'"><input type="hidden" name="csrf" value="'+
                    e(csrf)+'"><input type="hidden" name="seal" value="'+seal+
                    '"><label>Type '+e(confirm)+
                    '<input name="confirmation" autocomplete="off" '
                    'maxlength="48" required></label><button type="submit">'+
                    e(label)+'</button></form>')
        parts.append('</article>')
        cards.append(''.join(parts))
    return (
        '<section class="panel"><h3>Bob R4 proposals · exact owner review</h3>'
        '<p class="muted">These decisions were checked against the original '
        'sealed Scout snapshot and an immutable Bob action seal before '
        'display. Missing or changed source records are withheld. An '
        'owner approval never creates a publication job. R3 continues '
        'using its separate existing review screen.</p>'
        '<p><a href="/r3">R3 drafts</a> · '
        '<a href="/v08/inbox">Shadow anomalies</a> · '
        '<a href="/moltbook/discovery">Friend discovery</a></p></section>'+
        (''.join(cards) if cards else
         '<section class="panel"><p>No independently verified R4 decisions '
         'in the current bounded source window.</p></section>')+
        _suggestion_cards(data,csrf)+
        '<section class="panel"><h3>Evidence digest</h3>'
        '<p class="muted">Most recent verified R3 audit source: <code>'+
        e(data.get("latest_r3_source") or "not recorded")+'</code>. '
        'A skip is abstention, an approved private proposal is not a '
        'queued public action, and a saved friend is not a platform follow.'
        '</p><p><a href="/moltbook/social-memory">Social timeline</a>'
        '</p></section>')


def _bob(data):
    # Only seal-verified reasons from the actual R3 agent, never invented
    # personality opinions or remotely confirmed social relationships.
    thoughts=''.join(
        '<li><b>'+e(x["topic"])+'</b> · '+e(x["reason"])+
        ' <a href="/r3">R3 source '+e(x["source_run"])+'</a>'
        '<span class="muted"> · Bob expressed this; not owner-confirmed fact</span>'
        '</li>' for x in data.get("bob_reasons",[])[:8])
    friends=''.join('<li><b>@'+e(x["handle"])+'</b> · '+
           e(x["local_relationship"])+' · '+e(x["evidence"])+
           ' · remote following unknown</li>' for x in data["people"])
    memories=''.join('<li>'+e(x["title"])+' · '+e(x["category"])+
            ' · '+e(x["confidence"])+' · owner-entered, not automatically '
            'recalled</li>' for x in data["memory_titles"])
    return ('<section class="panel"><h3>Bob&#39;s own source-linked reasons</h3>'
            '<p class="muted">These are previous Bob-authored reasons that '
            'passed the sealed R3 source reader. They are tentative '
            'interpretations, not automatically promoted memories.</p><ul>'+
            (thoughts or '<li>No currently verified expressed reasons.</li>')+
            '</ul></section><div class="grid"><section class="panel">'
            '<h3>Personality and memory</h3><p class="muted">Personality '
            'sliders are staged until separately applied to OpenClaw. '
            'Memory notes are owner-curated; they do not silently become '
            'agent recollection.</p><p><a href="/mind/personality">'
            'Personality manager</a> · <a href="/mind/memory">Memory manager</a>'
            '</p><h3>Recent owner memory notes</h3><ul>'+
            (memories or '<li>No active owner notes in the readable window.</li>')+
            '</ul></section><section class="panel"><h3>Friends and interests</h3>'
            '<p class="muted">These labels are local opinions or owner notes, '
            'not verified Moltbook follow/follow-back status.</p><ul>'+
            (friends or '<li>No active local contacts in the readable window.</li>')+
            '</ul><p><a href="/moltbook/friends">Friends manager</a> · '
            '<a href="/moltbook/social-memory">Relationship timeline</a>'
            '</p></section></div>')


def _controls(data,csrf):
    forms=[]
    modes=data["controls"]
    for action in ACTIONS:
        chosen=modes.get(action,"off")
        forms.append(
            '<div class="mode"><div><strong>'+e(action.title())+'</strong>'
            '<div class="muted">Daily proposed upper bound: '+e(CAPS[action])+
            '; no new worker dispatch authority</div></div>'
            '<span class="badge">'+e(chosen.upper())+'</span>'
            '<form action="/r4/controls/'+e(action)+'" method="post">'
            '<input type="hidden" name="csrf" value="'+e(csrf)+'">'
            '<label>Mode<select name="mode">'
            '<option value="off"'+(' selected' if chosen=="off" else '')+'>Off</option>'
            '<option value="propose"'+(' selected' if chosen=="propose" else '')+'>Propose</option>'
            '<option value="auto" disabled>Auto (worker not authorized)</option>'
            '</select></label><label>Exact confirmation phrase'
            '<input type="text" name="confirmation" maxlength="60" '
            'placeholder="SET R4 '+e(action.upper())+' PROPOSE" required '
            'autocomplete="off"></label><button type="submit">Save only</button>'
            '</form></div>')
    paused=data["r4_paused"]
    next_pause=not paused
    pause_phrase="PAUSE R4" if next_pause else "RESUME R4"
    pause_form=(
        '<form action="/r4/controls/pause" method="post">'
        '<input type="hidden" name="csrf" value="'+e(csrf)+'">'
        '<input type="hidden" name="paused" value="'+str(next_pause).lower()+'">'
        '<label>To change R4-only pause, type '+e(pause_phrase)+
        '<input name="confirmation" maxlength="30" required '
        'autocomplete="off"></label><button>Change R4 pause only</button>'
        '</form>')
    return ('<section class="panel"><h3>Independent category permissions</h3>'
            '<p class="muted">Default Off. Propose stores owner preference '
            'without creating or sending a publication. Auto is disabled '
            'until separately signed action-specific worker/receipt handling '
            'exists. R3 canary authority is not inherited.</p>'
            '<div class="mode-list">'+''.join(forms)+'</div></section>'
            '<section class="panel"><h3>R4 global pause</h3><p>R4 pause: '
            '<strong>'+('ON' if paused else 'OFF')+'</strong></p>'
            '<p class="muted">This controls R4 only. It does not reset '
            'historical attempts or turn on/off legacy Scout publication.'
            '</p>'+pause_form+'</section>')


def _diagnostics(data):
    events=''.join('<li><code>'+e(x["source_run"])+'</code> · '+
                   e(x["kind"])+' · '+e(x["at"])+'</li>'
                   for x in data["recent_events"])
    return ('<section class="panel"><h3>Source-linked R3 audit</h3><ul>'+
            (events or '<li>No bounded R3 audit events available.</li>')+
            '</ul><p class="muted">Only sanitized metadata. No raw model '
            'prompts, API keys, draft content, or private network headers.</p>'
            '</section><section class="panel"><h3>Existing diagnostics</h3>'
            '<p><a href="/investigate">Why no activity?</a> · '
            '<a href="/console">Console</a> · '
            '<a href="/settings/activity-limits">Existing worker limits</a>'
            '</p></section>')


def content(panel:str,data:dict,csrf:str) -> str:
    if panel not in PANEL.values():
        raise ValueError("r4_unknown_panel")
    blocks={"now":_now,"inbox":lambda s:_inbox(s,csrf),"bob":_bob,
            "controls":lambda s:_controls(s,csrf),
            "diagnostics":_diagnostics,
            "chat":lambda s:('<section class="panel"><h3>Chat · future CH1</h3>'
                '<p>Direct authenticated conversation with the real Bob '
                'OpenClaw Gateway is reserved for CH1. This is not a '
                'fake chat with the local Ollama backend.</p></section>')}
    return (CSS+'<div class="r4"><header><h2>💀 Bob · R4 Autonomy</h2>'
            '<p class="muted">One workspace for activity, review, Bob, '
            'controls and diagnostics.</p></header>'+_nav(panel)
            +'<section class="panel">'+_notice(data)+'</section>'
            +blocks[panel](data)+'</div>')


class R4HandlerMixin:
    """Additive, authenticated routes over the existing TLS-only R3 handler."""
    R4_CSRF_TOKEN="__no_runtime_token__"

    def do_GET(self):
        path=urlsplit(self.path).path
        if path not in PAGES:
            return super().do_GET()
        if not self._valid_host():
            self._send(403,"Unexpected Host header")
            return
        if not self._authenticated():
            self._auth_required()
            return
        from navigation_shell import wrap
        data=snapshot()
        view=PANEL[path]
        if data["available"] and view in ("bob","inbox"):
            from bob_r4_reflections import reasons
            data["bob_reasons"]=reasons()
        self._send(200,wrap("Bob R4 · "+view.title(),
                            content(view,data,self.R4_CSRF_TOKEN),"/r4/now"),
                   "text/html; charset=utf-8")

    def do_POST(self):
        path=urlsplit(self.path).path
        action=ACTION_URL.fullmatch(path)
        pause=path=="/r4/controls/pause"
        decision=REVIEW_URL.fullmatch(path)
        suggestion=SUGGEST_URL.fullmatch(path)
        outbox=OUTBOX_URL.fullmatch(path)
        if not action and not pause and not decision and not suggestion and not outbox:
            return super().do_POST()
        if not self._valid_host():
            self._send(403,"Unexpected Host header")
            return
        if not self._authenticated():
            self._auth_required()
            return
        if not self._valid_origin():
            self._error_page(403,"R4 action blocked",
                             "Host or Origin verification failed")
            return
        try:
            length=int(self.headers.get("Content-Length","-1"))
            if not 0<length<=512:
                raise ValueError("r4_invalid_form_length")
            params=parse_qs(self.rfile.read(length).decode("utf-8"),
                            keep_blank_values=True,max_num_fields=4)
            if len(params)!=3 or any(
                    len(values)!=1 for values in params.values()):
                raise ValueError("r4_invalid_form_fields")
            if not hmac.compare_digest(params.get("csrf",[""])[0],
                                       self.R4_CSRF_TOKEN):
                self._error_page(403,"R4 action blocked",
                                 "CSRF verification failed")
                return
            # Verify the installed signed code and exact private manager DB.
            from bob_r313d_package import load_verified
            if load_verified()!="verified_registry_archive":
                raise ValueError("r4_unsigned_saved_source_archive")
            from bob_r313d_owner import trusted_manager_boundary
            with publish_conn() as db:
                trusted=trusted_manager_boundary(db)
                if not trusted:
                    raise ValueError("r4_private_db_untrusted")
                phrase=params.get("confirmation",[""])[0]
                if action:
                    if set(params)!={"csrf","mode","confirmation"}:
                        raise ValueError("r4_unexpected_form_fields")
                    set_mode(db,action.group(1),params["mode"][0],
                             phrase,trusted=True)
                elif decision:
                    if set(params)!={"csrf","seal","confirmation"}:
                        raise ValueError("r4_unexpected_review_fields")
                    from bob_publish_common import DATA
                    from bob_r4_ledger import review
                    from datetime import datetime,timezone
                    review(db,DATA,decision.group(1),params["seal"][0],
                           decision.group(2),phrase,trusted=True,
                           at=datetime.now(timezone.utc))
                elif suggestion:
                    if set(params)!={"csrf","seal","confirmation"}:
                        raise ValueError("r4_unexpected_suggestion_fields")
                    from bob_publish_common import DATA
                    from bob_r4_suggestions import review as review_suggestion
                    from datetime import datetime,timezone
                    review_suggestion(db,DATA,suggestion.group(1),
                                      suggestion.group(2),params["seal"][0],
                                      suggestion.group(3),phrase,trusted=True,
                                      at=datetime.now(timezone.utc))
                elif outbox:
                    if set(params)!={"csrf","seal","confirmation"}:
                        raise ValueError("r4_unexpected_outbox_fields")
                    from bob_publish_common import DATA
                    from bob_r4_outbox import queue,cancel
                    from datetime import datetime,timezone
                    if outbox.group(2)=="queue":
                        queue(db,DATA,outbox.group(1),params["seal"][0],
                              phrase,trusted=True,
                              at=datetime.now(timezone.utc))
                    else:
                        cancel(db,outbox.group(1),phrase,trusted=True,
                               at=datetime.now(timezone.utc),
                               provided_seal=params["seal"][0])
                else:
                    if set(params)!={"csrf","paused","confirmation"} or (
                            params["paused"][0] not in ("true","false")):
                        raise ValueError("r4_invalid_pause_fields")
                    set_pause(db,params["paused"][0]=="true",
                              phrase,trusted=True)
            self.send_response(303)
            self.send_header("Location",("/r4/inbox" if decision or suggestion or outbox
                                         else "/r4/controls"))
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,sqlite3.Error,OSError,TypeError,
                ImportError,UnicodeError):
            self._error_page(409,"R4 change not saved",
                             "Request refused or data changed; reload and retry")
