"""PM1 Personality Lab: owner-editable staging profile, audit history, workspace inventory.

Persisted traits are PREVIEW SETTINGS, not an OpenClaw runtime override.
No tool permissions, SOUL.md writes, agent invocation or network calls.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import hashlib
import json
import os
import re
import stat

from bob_publish_common import setting, set_setting, event

# (name, displayed label, suggested starting value, explanation)
TRAITS = (
    ("sarcasm", "Sarcasm", 65, "Witty and dry, never cruel"),
    ("humor", "Humor", 75, "Playfulness in appropriate conversations"),
    ("friendliness", "Friendliness", 60, "Warmth without forced agreement"),
    ("assertiveness", "Assertiveness", 55, "Ability to state a view without bluster"),
    ("curiosity", "Curiosity", 90, "Investigate questions rather than assume"),
    ("independence", "Intellectual independence", 85, "Reason independently, not automatically agree"),
    ("reconsideration", "Willingness to reconsider", 80, "Update opinions when evidence changes"),
    ("exploration", "Interest exploration", 90, "Discover new subjects and interests"),
)
KEYS = tuple(x[0] for x in TRAITS)
PREFIX = "bob_personality_"
STEP = 5
INT = re.compile(r"(?:0|[1-9][0-9]{0,2})\Z")
REV = re.compile(r"[1-9][0-9]{0,8}\Z")
WORKSPACE = Path.home() / ".openclaw/workspace"
FILES = ("SOUL.md", "IDENTITY.md")
HISTORY_LIMIT = 8


def validate(values):
    if set(values) != set(KEYS):
        raise ValueError("Incomplete personality profile")
    validated = {}
    for name in KEYS:
        raw = values[name]
        if not isinstance(raw, str) or not INT.fullmatch(raw):
            raise ValueError("Personality values must be whole canonical numbers")
        number = int(raw)
        if not 0 <= number <= 100 or number % STEP:
            raise ValueError("Personality values must be 0-100 in steps of five")
        validated[name] = number
    return validated


def read_profile(db):
    values = {name: setting(db, PREFIX+name, str(default))
              for name, _, default, _ in TRAITS}
    return validate(values)


def _table_exists(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='bob_personality_revisions'").fetchone())


def _create_history(db):
    db.execute("""CREATE TABLE IF NOT EXISTS bob_personality_revisions (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       saved_at TEXT NOT NULL,
       profile_json TEXT NOT NULL,
       sha256 TEXT NOT NULL,
       reason TEXT NOT NULL CHECK(reason IN ('saved', 'restored'))
    )""")


def read_history(db, limit=HISTORY_LIMIT):
    if not _table_exists(db):
        return []
    result = []
    for item_id, saved_at, raw, sha, reason in db.execute(
        "SELECT id,saved_at,profile_json,sha256,reason "
        "FROM bob_personality_revisions ORDER BY id DESC LIMIT ?", (min(20,max(1,int(limit))),)
    ):
        try:
            if not isinstance(raw,str) or len(raw)>2048 or hashlib.sha256(raw.encode()).hexdigest()!=sha:
                continue
            profile = validate({k:str(v) for k,v in json.loads(raw).items()})
        except (ValueError,TypeError,AttributeError,KeyError):
            continue
        result.append({"id":item_id,"saved_at":saved_at,"reason":reason,
                       "profile":profile})
    return result


def store_profile(db, incoming, *, restore_id=None):
    """Called after authenticated, same-origin CSRF POST, in one DB transaction."""
    if restore_id is None:
        profile = validate(incoming)
        reason = "saved"
    else:
        if not isinstance(restore_id,str) or not REV.fullmatch(restore_id):
            raise ValueError("Invalid revision")
        if not _table_exists(db):
            raise ValueError("No profile history")
        row = db.execute("SELECT profile_json,sha256 FROM bob_personality_revisions "
                         "WHERE id=?", (int(restore_id),)).fetchone()
        if not row or hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:
            raise ValueError("Unknown or modified profile revision")
        old = json.loads(row[0])
        if not isinstance(old,dict):
            raise ValueError("Invalid saved profile")
        profile = validate({k:str(v) for k,v in old.items()})
        reason = "restored"
    # No SOUL.md, IDENTITY.md, AGENTS.md, API tokens, or publishing settings touched.
    _create_history(db)
    for name in KEYS:
        set_setting(db, PREFIX+name, profile[name])
    raw=json.dumps(profile,sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(raw.encode()).hexdigest()
    db.execute("INSERT INTO bob_personality_revisions(saved_at,profile_json,sha256,reason) "
               "VALUES(?,?,?,?)",
               (datetime.now(timezone.utc).isoformat(timespec="seconds"), raw,digest,reason))
    event(db,"bob_personality_staged",f"{reason}: {digest[:12]}")
    return profile


def identity_inventory(root=WORKSPACE):
    """Metadata of the assumed workspace only; avoid exposing private file bodies."""
    root=Path(root)
    result=[]
    for name in FILES:
        path=root/name
        info={"name":name,"status":"not found"}
        try:
            if root.is_symlink() or path.is_symlink():
                info["status"]="symlink blocked"
            else:
                fd=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
                try:
                    st=os.fstat(fd)
                    if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid():
                        info["status"]="unsupported file"
                    elif st.st_size>65536:
                        info["status"]="too large to inspect"
                    else:
                        data=os.read(fd,65537)
                        if len(data)>65536:
                            info["status"]="too large to inspect"
                        else:
                            info={"name":name,"status":"present","bytes":len(data),
                                  "sha256":hashlib.sha256(data).hexdigest()[:16]}
                finally:
                    os.close(fd)
        except FileNotFoundError:
            pass
        except OSError:
            info["status"]="unavailable"
        result.append(info)
    return result


def esc(value):
    return escape(str(value),quote=True)


CSS = """<style>
.bpm{display:grid;gap:18px;max-width:1080px;margin:auto}
.bpm-panel{background:linear-gradient(150deg,#17283f,#111e32);border:1px solid #304b6c;
 border-radius:15px;padding:clamp(16px,3vw,24px)}
.bpm-intro{color:#b5c9df;line-height:1.55;margin:0}
.bpm-notice{padding:12px 14px;background:#3c2d1d;border:1px solid #846137;
 color:#ffdfae;border-radius:10px;font-size:.88rem;line-height:1.5}
.bpm-head{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.bpm-head h2{font-size:1.13rem;margin:0}
.bpm-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}
.bpm-trait{display:grid;gap:7px}
.bpm-trait label{display:flex;justify-content:space-between;gap:12px;font-weight:700;font-size:.91rem}
.bpm-trait output{color:#a9dbff;font-variant-numeric:tabular-nums}
.bpm-trait input[type=range]{width:100%;margin:0;accent-color:#70baff;height:32px;cursor:pointer}
.bpm-trait small{color:#a6bcd5;font-size:.77rem}
.bpm-preview{background:#101d2d;border:1px solid #335477;border-radius:11px;padding:15px;
 color:#d4e6f8;white-space:pre-wrap;overflow-wrap:anywhere;font-size:.89rem;line-height:1.55}
.bpm-actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.bpm button{cursor:pointer;border-radius:10px;border:1px solid #79a9df;background:#265d90;
 color:#fff;min-height:44px;padding:10px 16px;font:inherit;font-weight:700}
.bpm button.secondary{background:#23354b;border-color:#536e8a}
.bpm-muted{color:#a9bfd7;font-size:.81rem;line-height:1.5}
.bpm-table{width:100%;border-collapse:collapse;font-size:.87rem}
.bpm-table th,.bpm-table td{text-align:left;border-bottom:1px solid #30445d;padding:10px 6px}
.bpm-table td:last-child{text-align:right}
.bpm-table form{margin:0}
.bpm-table button{min-height:38px;padding:7px 11px;font-size:.82rem}
.bpm[aria-busy=true]{opacity:.8}
@media(max-width:690px){.bpm-grid{grid-template-columns:1fr;gap:17px}
.bpm-table th:nth-child(2),.bpm-table td:nth-child(2){display:none}}
@media(prefers-reduced-motion:reduce){.bpm *{animation:none!important;transition:none!important}}
</style>"""

JS = r"""'use strict';
(() => {
  const root=document.getElementById('bob-personality');
  if (!root) return;
  const inputs=[...root.querySelectorAll('input[data-bpm-trait]')];
  const preview=document.getElementById('bpm-preview');
  const levels=(value)=>value<=20?'minimal':value<=40?'restrained':value<=60?'balanced':value<=80?'pronounced':'very strong';
  function draw() {
    const traits=[];
    for(const input of inputs) {
      const output=document.getElementById('bpm-value-'+input.name);
      if(output) output.textContent=input.value+'%';
      traits.push(input.dataset.bpmLabel+': '+levels(Number(input.value))+' ('+input.value+'/100)');
    }
    preview.textContent='Illustrative tone guidance (not a generated Bob reply):\n'+traits.join('\n')
       +'\n\nCuriosity and openness encourage exploration, not unsupported certainty. '
       +'These settings are staged until a later, separately reviewed Apply to Bob phase.';
  }
  inputs.forEach(x=>x.addEventListener('input',draw));
  draw();
})();
"""


def javascript():
    return JS


def _row(item, csrf):
    id=item["id"]
    return ('<tr><td>'+esc(item["saved_at"])+'</td><td>'+esc(item["reason"])+'</td>'
            '<td><form method="post" action="/mind/personality">'
            '<input type="hidden" name="csrf" value="'+esc(csrf)+'">'
            '<input type="hidden" name="mode" value="restore">'
            '<input type="hidden" name="revision" value="'+esc(id)+'">'
            '<button type="submit" class="secondary">Restore profile</button>'
            '</form></td></tr>')


def page(db, csrf, wrap):
    profile=read_profile(db)
    history=read_history(db)
    identity=identity_inventory()
    left=TRAITS[:4]; right=TRAITS[4:]
    def traits(items):
        return "".join(
            '<div class="bpm-trait"><label for="bpm-'+esc(name)+'">'+esc(label)+
            '<output id="bpm-value-'+esc(name)+'" for="bpm-'+esc(name)+'">'+
            str(profile[name])+'%</output></label>'
            '<input id="bpm-'+esc(name)+'" type="range" name="'+esc(name)+
            '" min="0" max="100" step="5" value="'+str(profile[name])+
            '" data-bpm-trait data-bpm-label="'+esc(label)+'">'
            '<small>'+esc(desc)+'</small></div>'
            for name,label,default,desc in items
        )
    identity_items="".join(
        '<li><b>'+esc(item["name"])+'</b>: '+esc(item["status"])+
        (f' · {item["bytes"]} bytes · SHA-256 {esc(item["sha256"])}…' if "sha256" in item else "")+
        '</li>' for item in identity)
    body=(CSS+'<div class="bpm" id="bob-personality">'
          '<p class="bpm-intro">Adjust Bob’s social and intellectual style. The sliders are editable and '
          'saved privately with history. They do not yet alter OpenClaw prompts.</p>'
          '<div class="bpm-notice"><b>Staging only:</b> Saving here does not change Bob’s live personality. '
          'First we verify the actual workspace, then add a separate safe Apply &amp; Rollback step.</div>'
          '<section class="bpm-panel"><div class="bpm-head"><h2>Personality controls</h2>'
          '<span class="bpm-muted">Eight traits · 0–100 · increments of five</span></div>'
          '<form method="post" action="/mind/personality">'
          '<input type="hidden" name="csrf" value="'+esc(csrf)+'">'
          '<input type="hidden" name="mode" value="save">'
          '<div class="bpm-grid"><div class="bpm-grid-col"><h3>Social style</h3>'+
          traits(left)+'</div><div class="bpm-grid-col"><h3>Intellectual style</h3>'+
          traits(right)+'</div></div><div class="bpm-actions">'
          '<button type="submit">Save staged profile</button>'
          '<span class="bpm-muted">Saved to private local database; no agent change</span>'
          '</div></form></section>'
          '<section class="bpm-panel"><div class="bpm-head"><h2>Live slider interpretation</h2>'
          '<span class="bpm-muted">No Ollama call or publication</span></div>'
          '<div class="bpm-preview" id="bpm-preview">Enable JavaScript to preview guidance.</div></section>'
          '<section class="bpm-panel"><div class="bpm-head"><h2>Existing OpenClaw identity files</h2>'
          '<span class="bpm-muted">Read-only metadata</span></div>'
          '<p class="bpm-muted">Inspected assumed default workspace: ~/.openclaw/workspace. '
          'The active workspace must be confirmed before any file edits. '
          'Only names, sizes and short hashes are shown; no contents are copied to Git.</p>'
          '<ul>'+identity_items+'</ul></section>'
          '<section class="bpm-panel"><div class="bpm-head"><h2>Saved profile history</h2>'
          '<span class="bpm-muted">Most recent eight</span></div>'+
          ('<table class="bpm-table"><thead><tr><th>Saved at (UTC)</th><th>Action</th>'
           '<th>Restore</th></tr></thead><tbody>'+ "".join(_row(x,csrf) for x in history)+
           '</tbody></table>' if history else '<p class="bpm-muted">No saved profiles yet. '
           'Current values are suggested starting points, not a reading of Bob’s existing identity.</p>')+
          '<p class="bpm-muted">Restoring a profile updates only these staged sliders. '
          'Every change creates a new revision.</p></section></div>')
    return wrap("Bob’s Mind · Personality",body,"/mind/personality").replace(
        '</head>','<script src="/assets/bob-personality.js" defer></script></head>',1)
