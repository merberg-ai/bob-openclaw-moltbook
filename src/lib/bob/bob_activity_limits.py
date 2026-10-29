"""Operator-controlled local activity budgets for Bob, enforced by workers.

Only five explicitly allowlisted integer settings live in publish_settings.
Missing settings retain the pre-release safety policy until the owner saves.
No network/API access, credentials, or automatic publishing permissions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import re

from bob_publish_common import event, set_setting, setting

# name, title, default, minimum, maximum, units
FIELDS = (
    ("comment_daily", "Total comment attempts per UTC day", 2, 1, 20, "attempts"),
    ("comment_gap_minutes", "Minimum between comment attempts", 60, 10, 180, "minutes"),
    ("comment_auto_daily", "Automatic comment attempts per UTC day", 2, 0, 20, "attempts"),
    ("original_daily", "Original post attempts per UTC day", 1, 1, 5, "attempts"),
    ("original_gap_minutes", "Minimum between original post attempts", 120, 30, 360, "minutes"),
)
RECOMMENDED = {
    "comment_daily": 6,
    "comment_gap_minutes": 45,
    "comment_auto_daily": 3,
    "original_daily": 2,
    "original_gap_minutes": 120,
}
PREFIX = "activity_limit_"
SELECTION = re.compile(r"(?:0|[1-9][0-9]{0,2})\Z")
MAX_FIELDS = len(FIELDS)


def validated(values):
    """Strict schema. Invalid persisted values fail closed; never fall back high."""
    if set(values) != {f[0] for f in FIELDS}:
        raise ValueError("incomplete activity settings")
    result = {}
    for key, title, default, low, high, units in FIELDS:
        value = values[key]
        if not isinstance(value, str) or not SELECTION.fullmatch(value):
            raise ValueError("activity limit contains noncanonical integer")
        number = int(value)
        if not low <= number <= high:
            raise ValueError("activity limit outside safety range")
        result[key] = number
    if result["comment_auto_daily"] > result["comment_daily"]:
        raise ValueError("automatic cap exceeds total comment cap")
    return result


def read_limits(db):
    stored = {name: setting(db, PREFIX + name, str(default))
              for name, _, default, _, _, _ in FIELDS}
    return validated(stored)


def form_values(db):
    return {name: str(value) for name, value in read_limits(db).items()}


def save_limits(db, raw, *, actor="dashboard"):
    """Strict all-fields parse; call inside an existing SQLite transaction."""
    values = validated(raw)
    previous = read_limits(db)
    # This does not set auto_enabled, create approvals, or queue content.
    for key in values:
        set_setting(db, PREFIX + key, values[key])
    # Metadata only. Do not log passwords, draft text, or cookies.
    event(db, "activity_limits_updated",
          f"{actor}: " + ", ".join(f"{k} {previous[k]}->{values[k]}" for k in values))
    return values


def attempts(db, table, utc_day, *, mode=None):
    if table not in ("publish_jobs", "original_posts"):
        raise ValueError("invalid attempt source")
    if mode is None:
        return db.execute(f"SELECT COUNT(*) FROM {table} WHERE attempted_at LIKE ?",
                          (utc_day + "%",)).fetchone()[0]
    if table != "publish_jobs" or mode != "auto":
        raise ValueError("invalid attempt mode")
    return db.execute("SELECT COUNT(*) FROM publish_jobs "
                      "WHERE attempted_at LIKE ? AND mode='auto'",
                      (utc_day + "%",)).fetchone()[0]


def last_attempt(db, table):
    if table not in ("publish_jobs", "original_posts"):
        raise ValueError("invalid attempt source")
    row = db.execute(f"SELECT attempted_at FROM {table} WHERE attempted_at IS NOT NULL "
                     "ORDER BY attempted_at DESC LIMIT 1").fetchone()
    if not row:
        return None
    try:
        parsed = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def allowed(db, kind, *, mode=None, at=None):
    """Determine eligibility; never consume a slot or perform a POST."""
    config = read_limits(db)
    when = at if at is not None else datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("timezone-aware time required")
    when = when.astimezone(timezone.utc)
    day = when.strftime("%Y-%m-%d")
    if kind == "comment":
        table, daily, gap = ("publish_jobs", config["comment_daily"],
                             config["comment_gap_minutes"])
        if mode not in ("manual", "auto"):
            raise ValueError("comment mode required")
    elif kind == "original":
        if mode is not None:
            raise ValueError("original has no comment mode")
        table, daily, gap = ("original_posts", config["original_daily"],
                             config["original_gap_minutes"])
    else:
        raise ValueError("unknown activity type")
    used = attempts(db, table, day)
    if used >= daily:
        return False, f"{kind} daily attempt limit reached ({used}/{daily})"
    if kind == "comment" and mode == "auto":
        auto_used = attempts(db, table, day, mode="auto")
        if auto_used >= config["comment_auto_daily"]:
            return False, ("automatic comment daily limit reached "
                           f"({auto_used}/{config['comment_auto_daily']})")
    previous = last_attempt(db, table)
    # A malformed non-empty attempted_at is uncertain history. Fail closed.
    if previous is None and db.execute(
        f"SELECT COUNT(*) FROM {table} WHERE attempted_at IS NOT NULL").fetchone()[0]:
        row = db.execute(
            f"SELECT attempted_at FROM {table} WHERE attempted_at IS NOT NULL "
            "ORDER BY attempted_at DESC LIMIT 1").fetchone()
        if row and previous is None:
            return False, "last attempt timestamp unavailable; inspect history"
    if previous is not None and when - previous < timedelta(minutes=gap):
        return False, f"{kind} minimum interval ({gap} minutes) not elapsed"
    return True, ""


def summary(db, *, at=None):
    config = read_limits(db)
    when = at or datetime.now(timezone.utc)
    day = when.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return {"limits": config, "comment_used": attempts(db, "publish_jobs", day),
            "auto_used": attempts(db, "publish_jobs", day, mode="auto"),
            "original_used": attempts(db, "original_posts", day)}


def esc(value):
    return escape(str(value), quote=True)


def nav(active):
    links = (("/settings", "Overview"), ("/settings/users", "Users & access"),
             ("/settings/activity-limits", "Activity limits"))
    return ('<nav class="bal-nav" aria-label="Settings sections">' +
            "".join(f'<a href="{href}"' + (' aria-current="page"' if active == href else "")
                    + f'>{esc(label)}</a>' for href,label in links) + '</nav>')


CSS = """<style>
.bal{max-width:820px;margin:auto}
.bal-nav{display:flex;flex-wrap:wrap;gap:9px;margin:15px 0 22px}
.bal-nav a{padding:10px 14px;min-height:44px;display:inline-flex;align-items:center;
border-radius:9px;background:#1b324c;border:1px solid #3d5777;text-decoration:none}
.bal-nav a[aria-current=page]{background:#285f8f;color:white}
.bal-card{padding:clamp(15px,3vw,25px);margin:14px 0;border:1px solid #365272;
background:#15263d;border-radius:13px}
.bal-card p,.bal-muted{color:#b8c8dd;line-height:1.55}
.bal-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.bal-field{display:grid;gap:6px;font-weight:650;min-width:0}
.bal-field select,.bal-card input{min-height:46px;width:100%;padding:9px 12px;
color:white;background:#0e1b2c;border:1px solid #58769b;border-radius:9px;font:inherit}
.bal-card button{min-height:46px;border:1px solid #739dcc;border-radius:9px;
background:#286294;color:#fff;padding:10px 14px;font-weight:750;cursor:pointer}
.bal-card form{display:grid;gap:14px}
.bal-stats{display:flex;gap:10px;flex-wrap:wrap}
.bal-stats span{background:#1d3751;border-radius:9px;padding:10px 12px}
@media(max-width:680px){.bal-grid{grid-template-columns:1fr}.bal-card button{width:100%}}
</style>"""


def overview(wrap):
    html = (CSS+'<div class="bal">'+nav("/settings")
            +'<section class="bal-card"><h2>Settings</h2>'
            '<p>Manage dashboard access and Bob’s local posting budgets. '
            'Every outgoing publication still requires its existing authorization.</p>'
            '<p><a href="/settings/users">Users & access</a> · '
            '<a href="/settings/activity-limits">Activity limits</a></p>'
            '</section></div>')
    return wrap("Settings", html, "/settings")


def users_page(existing_password_page):
    # Preserve existing password form, POST route, rotation, and credentials.
    old = existing_password_page()
    insertion = CSS + '<div class="bal">' + nav("/settings/users") + '</div>'
    return old.replace("</head>", insertion + "</head>", 1)


def activity_page(db, csrf, wrap, *, preview=False):
    info = summary(db)
    current = info["limits"]
    values = dict(RECOMMENDED) if preview else current
    parts = [CSS, '<div class="bal">', nav("/settings/activity-limits"),
             '<section class="bal-card"><h2>Activity limits</h2>'
             '<p>Worker-enforced limits on attempted sends, counted in UTC. '
             'Limits never create approval or enable autonomous posting. '
             'Moltbook may enforce stricter limits, including new-agent limits.</p>',
             '<div class="bal-stats">',
             f'<span>Comments today <b>{info["comment_used"]}/{current["comment_daily"]}</b></span>',
             f'<span>Automatic today <b>{info["auto_used"]}/{current["comment_auto_daily"]}</b></span>',
             f'<span>Original posts today <b>{info["original_used"]}/{current["original_daily"]}</b></span>',
             '</div><p class="bal-muted">Saving new caps does not erase past attempts. '
             'A queued post still needs worker eligibility and any required verification.</p>',
             '<p><a href="/settings/activity-limits?preset=recommended">Load recommended '
             '(6 comments/day, 45-minute spacing, 3 automatic/day, '
             '2 originals/day, 120-minute spacing)</a></p>',
             '<form method="post" action="/settings/activity-limits">'
             f'<input type="hidden" name="csrf" value="{esc(csrf)}">'
             '<div class="bal-grid">']
    for name, label, default, minimum, maximum, units in FIELDS:
        parts.append(f'<label class="bal-field">{esc(label)}'
                     f'<select name="{esc(name)}">')
        # Deliberately finite allowlist, not an unchecked slider.
        if name.endswith("_gap_minutes"):
            options = range(minimum, maximum+1, 5 if name=="comment_gap_minutes" else 30)
        else:
            options = range(minimum, maximum+1)
        for value in options:
            parts.append(f'<option value="{value}"'
                         +(" selected" if value==values[name] else "")
                         +f'>{value} {esc(units)}</option>')
        parts.append('</select></label>')
    parts.append('</div><label class="bal-field">To apply, type APPLY LIMITS '
                 '<input name="confirmation" maxlength="18" autocomplete="off" '
                 'placeholder="APPLY LIMITS" required></label>'
                 '<button type="submit">Save activity limits</button></form>'
                 '<p class="bal-muted">Changes are recorded locally and take effect '
                 'on the next eligible worker attempt. '
                 'An existing rate-limit response is never blindly retried.</p>'
                 '</section></div>')
    return wrap("Activity limits", "".join(parts), "/settings")
