"""PM2.1 private, operator-curated memory ledger.

No agent prompt injection, external fetch, Moltbook posting, or worker calls.
All state lives in the existing privately backed-up publication SQLite file.
Imported or model-suggested memories are intentionally not supported yet.
"""
from __future__ import annotations

from html import escape
from urllib.parse import urlsplit, urlencode
import hashlib
import hmac
import json
import re
import secrets

from bob_publish_common import now, event

CATEGORIES = ("observation", "preference", "fact", "question", "opinion", "other")
CONFIDENCE = ("low", "medium", "high")
STATES = ("active", "archived", "excluded")
ID = re.compile(r"[0-9a-f]{24}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
DOMAIN = re.compile(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+\Z")
CAP = 500
PAGE_SIZE = 12
FIELDS = ("title", "content", "category", "confidence", "source_label", "source_url")
COLS = ("id",) + FIELDS + ("source_kind", "state", "created_at", "updated_at", "version", "sha256")

CSS = """<style>
.bmm{max-width:1090px;margin:auto;display:grid;gap:18px}
.bmm-panel{padding:clamp(16px,2.5vw,24px);border:1px solid #304b6c;border-radius:15px;
 background:linear-gradient(150deg,#17283f,#111e32)}
.bmm h2{font-size:1.12rem;margin:0 0 12px}
.bmm h3{font-size:1rem;margin:0 0 8px}
.bmm-muted{color:#afc5dc;font-size:.87rem;line-height:1.55}
.bmm-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}
.bmm label{display:grid;gap:6px;font-weight:650;font-size:.91rem}
.bmm input:not([type=hidden]),.bmm select,.bmm textarea{width:100%;min-width:0;box-sizing:border-box;
 background:#0e1b2b;color:#f0f5ff;border:1px solid #506b8c;border-radius:9px;
 font:inherit;padding:10px 12px;min-height:44px}
.bmm textarea{min-height:115px;resize:vertical;line-height:1.45}
.bmm input:focus-visible,.bmm select:focus-visible,.bmm textarea:focus-visible,
.bmm button:focus-visible,.bmm a:focus-visible{outline:2px solid #87c5ff;outline-offset:2px}
.bmm button,.bmm .bmm-link{border:1px solid #77a9db;border-radius:9px;background:#285f91;
 color:white;font:inherit;font-weight:700;padding:10px 14px;min-height:44px;cursor:pointer}
.bmm .bmm-link{display:inline-flex;align-items:center;text-decoration:none}
.bmm button.secondary,.bmm .bmm-link.secondary{background:#23354b;border-color:#536e8a}
.bmm-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:13px}
.bmm-actions form{margin:0}
.bmm-filter{display:grid;grid-template-columns:minmax(160px,2fr) minmax(130px,1fr) auto;gap:12px;align-items:end}
.bmm-card{border:1px solid #34516c;border-radius:11px;background:#13243a;padding:15px;margin-top:12px;
 overflow-wrap:anywhere}
.bmm-meta{display:flex;gap:8px;flex-wrap:wrap;margin:9px 0;color:#bbcee3;font-size:.8rem}
.bmm-tag{border:1px solid #4b6888;padding:3px 9px;border-radius:20px}
.bmm-content{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.5}
.bmm small{font-size:.79rem;color:#afc5dc}
.bmm details{margin-top:12px}
.bmm summary{cursor:pointer;color:#b5d8ff}
.bmm-pager{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
@media(max-width:680px){.bmm-grid,.bmm-filter{grid-template-columns:1fr}
.bmm-actions button,.bmm-actions .bmm-link{width:100%;justify-content:center}
.bmm-actions form{width:100%}}
</style>"""


def e(value):
    return escape(str(value if value is not None else ""), quote=True)


def initialize(db):
    """Additive, idempotent schema. Never alter existing publisher tables."""
    db.execute("""CREATE TABLE IF NOT EXISTS bob_memories (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
      category TEXT NOT NULL, confidence TEXT NOT NULL,
      source_label TEXT NOT NULL, source_url TEXT NOT NULL,
      source_kind TEXT NOT NULL CHECK(source_kind='operator'),
      state TEXT NOT NULL CHECK(state IN ('active','archived','excluded')),
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      version INTEGER NOT NULL, sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS bob_memory_revisions (
      revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
      memory_id TEXT NOT NULL, version INTEGER NOT NULL,
      saved_at TEXT NOT NULL, action TEXT NOT NULL,
      reason TEXT NOT NULL, snapshot_json TEXT NOT NULL,
      UNIQUE(memory_id,version))""")
    db.execute("CREATE INDEX IF NOT EXISTS bob_memories_state_idx ON bob_memories(state,updated_at)")
    db.execute("CREATE INDEX IF NOT EXISTS bob_memories_revision_idx ON bob_memory_revisions(memory_id,version)")


def source_url(value):
    if not value:
        return ""
    if len(value) > 1000 or any(c.isspace() or ord(c) < 32 or c == "\\" for c in value):
        raise ValueError("Source URL must be a short HTTPS link")
    try:
        p = urlsplit(value)
        hostname = (p.hostname or "").lower()
        port = p.port
    except ValueError:
        raise ValueError("Malformed source URL") from None
    if (p.scheme != "https" or not DOMAIN.fullmatch(hostname)
            or hostname.startswith("-") or p.username is not None
            or p.password is not None or port not in (None, 443)
            or not p.netloc or "#" in value and len(p.fragment) > 120):
        raise ValueError("Use an ordinary public HTTPS source URL")
    return value


def _text(value, name, low, high, *, single_line=False):
    if not isinstance(value, str):
        raise ValueError("Invalid " + name)
    value = value.strip()
    if (not low <= len(value) <= high or "\x00" in value
            or any(ord(c) < 32 and c not in ("\n", "\t") for c in value)
            or single_line and ("\n" in value or "\t" in value)):
        raise ValueError(name + " must be " + str(low) + "-" + str(high) + " characters")
    return value


def validate(fields):
    if set(fields) != set(FIELDS):
        raise ValueError("Incomplete memory fields")
    category = fields["category"]
    confidence = fields["confidence"]
    if category not in CATEGORIES or confidence not in CONFIDENCE:
        raise ValueError("Unsupported category or confidence")
    return dict(
        title=_text(fields["title"], "Title", 4, 120, single_line=True),
        content=_text(fields["content"], "Memory text", 1, 2400),
        category=category,
        confidence=confidence,
        source_label=_text(fields["source_label"], "Source description", 0, 160, single_line=True),
        source_url=source_url(_text(fields["source_url"], "Source URL", 0, 1000, single_line=True)),
    )


def seal(item):
    snapshot = {k: item[k] for k in COLS if k != "sha256"}
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _get(db, ident):
    if not isinstance(ident, str) or not ID.fullmatch(ident):
        raise ValueError("Invalid memory ID")
    row = db.execute("SELECT " + ",".join(COLS) + " FROM bob_memories WHERE id=?", (ident,)).fetchone()
    if row is None:
        raise ValueError("Memory not found")
    item = dict(zip(COLS, row))
    if not hmac.compare_digest(item["sha256"], seal(item)):
        raise ValueError("Memory record integrity check failed")
    return item


def _revision(db, item, action, reason):
    snapshot = json.dumps({k: item[k] for k in COLS}, sort_keys=True, ensure_ascii=False)
    db.execute("INSERT INTO bob_memory_revisions(memory_id,version,saved_at,action,reason,snapshot_json) "
               "VALUES(?,?,?,?,?,?)", (item["id"], item["version"], item["updated_at"],
                                       action, reason, snapshot))


def create(db, fields):
    data = validate(fields)
    initialize(db)
    if db.execute("SELECT count(*) FROM bob_memories").fetchone()[0] >= CAP:
        raise ValueError("Memory capacity reached; archive/export before adding")
    stamp = now()
    item = dict(id=secrets.token_hex(12), **data, source_kind="operator", state="active",
                created_at=stamp, updated_at=stamp, version=1)
    item["sha256"] = seal(item)
    db.execute("INSERT INTO bob_memories(" + ",".join(COLS) + ") VALUES(" +
               ",".join("?" for _ in COLS) + ")", tuple(item[k] for k in COLS))
    _revision(db, item, "create", "Owner entered an unverified memory")
    event(db, "bob_memory_created", item["id"])
    return item["id"]


def change(db, ident, expected_sha, action, fields=None, reason=""):
    if action not in ("edit", "correct", "archive", "exclude", "restore"):
        raise ValueError("Unknown memory action")
    if not isinstance(expected_sha, str) or not HASH.fullmatch(expected_sha):
        raise ValueError("Invalid memory revision token")
    initialize(db)
    item = _get(db, ident)
    if not hmac.compare_digest(expected_sha, item["sha256"]):
        raise ValueError("Memory changed; reload before editing")
    if action in ("edit", "correct"):
        if item["state"] != "active":
            raise ValueError("Restore the memory before editing")
        updated = validate(fields)
        reason = _text(reason, "Edit reason", 8, 240)
        if all(updated[k] == item[k] for k in FIELDS):
            raise ValueError("No memory changes to save")
        item.update(updated)
    else:
        state = {"archive": "archived", "exclude": "excluded", "restore": "active"}[action]
        if action == "restore" and item["state"] == "active" or action != "restore" and item["state"] != "active":
            raise ValueError("Memory state changed; reload before updating")
        item["state"] = state
        reason = "Owner changed memory state to " + state
    item["version"] += 1
    item["updated_at"] = now()
    item["sha256"] = seal(item)
    changed = db.execute(
        "UPDATE bob_memories SET " +
        ",".join(k + "=?" for k in COLS if k != "id") +
        " WHERE id=? AND sha256=?",
        tuple(item[k] for k in COLS if k != "id") + (ident, expected_sha)
    )
    if changed.rowcount != 1:
        raise ValueError("Memory was updated concurrently; reload")
    _revision(db, item, action, reason)
    event(db, "bob_memory_" + action, ident + " v" + str(item["version"]))
    return ident


def dispatch(db, form):
    """Call only after authenticated same-origin, CSRF-verified, bounded POST."""
    operation = form.get("operation", "")
    if operation == "create":
        if set(form) != set(FIELDS) | {"operation", "csrf"}:
            raise ValueError("Unexpected memory create fields")
        return create(db, {k: form[k] for k in FIELDS})
    if operation in ("edit", "correct"):
        if set(form) != set(FIELDS) | {"operation", "csrf", "id", "expected_sha", "reason"}:
            raise ValueError("Unexpected memory edit fields")
        return change(db, form["id"], form["expected_sha"], operation,
                      {k: form[k] for k in FIELDS}, form["reason"])
    if operation in ("archive", "exclude", "restore"):
        if set(form) != {"operation", "csrf", "id", "expected_sha"}:
            raise ValueError("Unexpected memory state fields")
        return change(db, form["id"], form["expected_sha"], operation)
    raise ValueError("Unsupported memory action")


def _field(name, value, label, *, multiline=False, required=False, maxlength=120):
    attrs = ' required' if required else ""
    if multiline:
        return (f'<label>{e(label)}<textarea name="{name}" maxlength="{maxlength}"{attrs}>'
                f'{e(value)}</textarea></label>')
    return (f'<label>{e(label)}<input type="text" name="{name}" value="{e(value)}" '
            f'maxlength="{maxlength}"{attrs}></label>')


def _select(name, options, selected):
    return ('<label>' + e(name.title()) + f'<select name="{name}">' +
            "".join(f'<option value="{e(v)}"' + (' selected' if v == selected else '') +
                    f'>{e(v.title())}</option>' for v in options) + '</select></label>')


def _editor(csrf, item=None):
    data = item or dict(title="", content="", category="observation", confidence="low",
                        source_label="", source_url="")
    editing = bool(item)
    output = ['<section class="bmm-panel"><h2>' +
              ("Edit memory" if editing else "Add a memory") + '</h2>',
              '<p class="bmm-muted">Operator-entered, unverified context. This will not enter '
              'OpenClaw prompts or generate public activity.</p>',
              '<form method="post" action="/mind/memory">',
              f'<input type="hidden" name="csrf" value="{e(csrf)}">',
              f'<input type="hidden" name="operation" value="{"edit" if editing else "create"}">']
    if editing:
        output += [f'<input type="hidden" name="id" value="{e(item["id"])}">',
                   f'<input type="hidden" name="expected_sha" value="{e(item["sha256"])}">']
    output += ['<div class="bmm-grid">',
               _field("title", data["title"], "Title", required=True),
               _select("category", CATEGORIES, data["category"]),
               _select("confidence", CONFIDENCE, data["confidence"]),
               _field("source_label", data["source_label"], "Source description (optional)", maxlength=160),
               '</div>',
               _field("content", data["content"], "Memory / note", multiline=True, required=True, maxlength=2400),
               _field("source_url", data["source_url"], "Public HTTPS source URL (optional)", maxlength=1000)]
    if editing:
        output.append(_field("reason", "", "Why did this change? (required)", required=True, maxlength=240))
        output.append('<p class="bmm-muted">Use Correct below when fixing inaccurate memory, '
                      'or Save edit for ordinary refinements. Both keep revision history.</p>')
    output.append('<div class="bmm-actions"><button type="submit">' +
                  ("Save edit" if editing else "Add private memory") + '</button>')
    if editing:
        # Separate explicit correction action overrides the ordinary edit submit button.
        output += ['<button type="submit" name="operation" value="correct">Correct memory</button>',
                   '<a class="bmm-link secondary" href="/mind/memory">Cancel edit</a>']
    output.append('</div></form></section>')
    return "".join(output)


def _state_form(csrf, item, action, label):
    return ('<form method="post" action="/mind/memory">'
            f'<input type="hidden" name="csrf" value="{e(csrf)}">'
            f'<input type="hidden" name="id" value="{e(item["id"])}">'
            f'<input type="hidden" name="expected_sha" value="{e(item["sha256"])}">'
            f'<input type="hidden" name="operation" value="{e(action)}">'
            f'<button type="submit" class="secondary">{e(label)}</button></form>')


def _history(db, ident):
    output = ['<section class="bmm-panel"><h2>Revision history</h2>',
              '<p class="bmm-muted">Snapshots remain private and are not used as agent instructions.</p>']
    rows = db.execute("SELECT version,saved_at,action,reason,snapshot_json "
                      "FROM bob_memory_revisions WHERE memory_id=? "
                      "ORDER BY version DESC LIMIT 20", (ident,)).fetchall()
    for version, saved, action, reason, raw in rows:
        try:
            snapshot = json.loads(raw)
            body = snapshot["content"]
            title = snapshot["title"]
            if not isinstance(body, str) or not isinstance(title, str):
                continue
        except (ValueError, KeyError, TypeError):
            continue
        output.append(f'<details><summary>v{version} · {e(action)} · {e(saved)}'
                      f' · {e(reason)}</summary><h3>{e(title)}</h3>'
                      f'<p class="bmm-content">{e(body)}</p></details>')
    output.append('</section>')
    return "".join(output)


def page(db, params, csrf, wrap):
    initialize(db)
    def getparam(key, default=""):
        values = params.get(key, [])
        return values[0] if len(values) == 1 and isinstance(values[0], str) else default
    search = getparam("q")[:64].strip()
    show = getparam("show", "active")
    show = show if show in STATES + ("all",) else "active"
    edit_id = getparam("edit")
    raw_page = getparam("page", "1")
    requested = min(int(raw_page), 999) if re.fullmatch(r"[1-9]\d{0,3}", raw_page) else 1
    selected = None
    if ID.fullmatch(edit_id):
        try:
            selected = _get(db, edit_id)
        except ValueError:
            pass
    clauses, args = [], []
    if show != "all":
        clauses.append("state=?")
        args.append(show)
    if search:
        clauses.append("(instr(lower(title),lower(?))>0 OR instr(lower(content),lower(?))>0 "
                       "OR instr(lower(source_label),lower(?))>0)")
        args.extend([search] * 3)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute("SELECT count(*) FROM bob_memories" + where, args).fetchone()[0]
    last = max(1, (total + PAGE_SIZE - 1)//PAGE_SIZE)
    number = min(requested, last)
    rows = db.execute("SELECT " + ",".join(COLS) + " FROM bob_memories" + where +
                      " ORDER BY updated_at DESC,id DESC LIMIT ? OFFSET ?",
                      args + [PAGE_SIZE, (number-1)*PAGE_SIZE]).fetchall()
    items = [dict(zip(COLS, r)) for r in rows]
    def href(page_number):
        return "/mind/memory?" + urlencode({"q":search,"show":show,"page":page_number})
    parts = [CSS, '<div class="bmm"><p class="bmm-muted">Private memory ledger · '
             'Every entry is operator-entered and unverified. Archived and excluded entries '
             'will not be eligible for later agent recall. No recall integration exists yet.</p>',
             _editor(csrf, selected),
             '<section class="bmm-panel"><h2>Search memories</h2>',
             '<form method="get" action="/mind/memory" class="bmm-filter">',
             f'<label>Search<input type="search" name="q" maxlength="64" value="{e(search)}" '
             'placeholder="Title, text, source"></label>',
             '<label>Visibility<select name="show">']
    for state in ("active", "archived", "excluded", "all"):
        parts.append(f'<option value="{state}"' + (' selected' if state==show else '') +
                     f'>{state.title()}</option>')
    parts += ['</select></label><button type="submit">Filter</button></form>',
              f'<p class="bmm-muted">{total} matching memories · page {number} of {last} · '
              'limit 500 total memories</p>']
    for item in items:
        if not hmac.compare_digest(item["sha256"],seal(item)):
            continue
        parts += ['<article class="bmm-card"><h3>'+e(item["title"])+'</h3>',
                  '<div class="bmm-meta">',
                  *[f'<span class="bmm-tag">{e(text)}</span>' for text in
                    (item["state"], item["category"], item["confidence"]+" confidence",
                     "operator-entered · unverified", "v"+str(item["version"]))],
                  '</div><p class="bmm-content">'+e(item["content"])+'</p>']
        if item["source_label"]:
            parts.append('<p class="bmm-muted">Source: '+e(item["source_label"])+'</p>')
        if item["source_url"]:
            parts.append('<p><a href="'+e(item["source_url"])+'" rel="noopener noreferrer nofollow" '
                         'target="_blank">Open supplied source link</a></p>')
        parts.append('<p class="bmm-muted">Updated '+e(item["updated_at"])+'</p>')
        parts.append('<div class="bmm-actions">')
        if item["state"]=="active":
            parts += [f'<a class="bmm-link secondary" href="/mind/memory?edit={e(item["id"])}">'
                      'Edit and view history</a>',
                      _state_form(csrf,item,"archive","Archive"),
                      _state_form(csrf,item,"exclude","Exclude from recall")]
        else:
            parts.append(_state_form(csrf,item,"restore","Restore to active"))
            parts.append(f'<a class="bmm-link secondary" href="/mind/memory?edit={e(item["id"])}">'
                         'View history</a>')
        parts.append('</div></article>')
    if not items:
        parts.append('<p class="bmm-muted">No memories match this view.</p>')
    parts.append('<nav class="bmm-pager">')
    if number > 1:
        parts.append(f'<a href="{e(href(number-1))}">Previous</a>')
    parts.append(f'<span class="bmm-muted">Showing {len(items)} of {total}</span>')
    if number < last:
        parts.append(f'<a href="{e(href(number+1))}">Next</a>')
    parts.append('</nav></section>')
    if selected:
        parts.append(_history(db,selected["id"]))
    parts.append('</div>')
    return wrap("Bob's Mind · Memory", "".join(parts), "/mind/memory")
