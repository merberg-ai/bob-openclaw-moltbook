"""PM1.2 guarded application of staged traits to the verified main-agent SOUL.md.

Only a delimited style block is changed. OpenClaw CLI resolves the active
workspace; failures block writes. Private, checksum-verified backups and
compare-before-write prevent accidental persona replacement.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from difflib import unified_diff
from html import escape
from pathlib import Path
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import uuid

from bob_personality import TRAITS, read_profile, page as base_page, validate

BEGIN = "<!-- BOB_PERSONALITY_STYLE_V1_BEGIN -->"
END = "<!-- BOB_PERSONALITY_STYLE_V1_END -->"
MARK_START = BEGIN.encode("utf-8")
MARK_END = END.encode("utf-8")
MAX_FILE = 65536
HOME = Path.home()
STATE = HOME / ".local/state/bob-personality"
CONFIRM_APPLY = "APPLY BOB"
CONFIRM_ROLLBACK = "ROLL BACK"
ENV_LIMIT = 32768

LEVELS = (
    (20, "minimal"),
    (40, "restrained"),
    (60, "balanced"),
    (80, "pronounced"),
    (100, "very strong"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require_private_dir(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Symlinked state directory refused")
    if not path.exists():
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    st=path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode & 0o077:
        raise ValueError("State directory must be owned privately (0700)")
    return path


def _root_chain_safe(path, home=None):
    path=Path(path)
    home=Path(home if home is not None else HOME).resolve()
    if not path.is_absolute() or not path.is_relative_to(home) or path == home:
        raise ValueError("Agent workspace must reside under the operator home")
    cur=home
    for piece in path.relative_to(home).parts:
        if piece in ("", ".", ".."):
            raise ValueError("Invalid workspace path")
        cur=cur/piece
        if cur.is_symlink():
            raise ValueError("Symlinked workspace path refused")
    st=path.stat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        raise ValueError("Agent workspace must be an owned directory")
    return path


def agent_workspace():
    """Resolve configured main agent via documented read-only OpenClaw CLI."""
    candidate = HOME / ".openclaw/bin/openclaw"
    binary = str(candidate) if candidate.is_file() and os.access(candidate,os.X_OK) else shutil.which("openclaw")
    if not binary:
        raise ValueError("OpenClaw agents CLI unavailable: Apply disabled")
    env = os.environ.copy()
    env["PATH"] = (str(HOME/".openclaw/tools/node/bin")+":"+
                   str(HOME/".openclaw/bin")+":"+env.get("PATH",""))
    try:
        p=subprocess.run([binary,"agents","list","--json"],text=True,
                         capture_output=True,timeout=8,check=False,env=env)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("OpenClaw agent roster could not be verified") from None
    if p.returncode or len(p.stdout)>ENV_LIMIT:
        raise ValueError("OpenClaw agent roster unavailable or oversized")
    try:
        data=json.loads(p.stdout)
        agents=data if isinstance(data,list) else data["agents"]
        if not isinstance(agents,list):
            raise ValueError
        mains=[a for a in agents if isinstance(a,dict) and a.get("id")=="main"]
        if len(mains)!=1 or not isinstance(mains[0].get("workspace"),str):
            raise ValueError
        raw=mains[0]["workspace"]
        if "\x00" in raw or len(raw)>2048 or not raw:
            raise ValueError
        path=Path(os.path.expanduser(raw))
        if not path.is_absolute():
            raise ValueError
        return _root_chain_safe(path)
    except (ValueError,KeyError,TypeError,AttributeError,OSError):
        raise ValueError("Cannot prove main agent workspace: Apply disabled") from None


def soul_bytes(root):
    root=_root_chain_safe(root)
    path=root/"SOUL.md"
    if path.is_symlink():
        raise ValueError("Symlinked SOUL.md refused")
    try:
        fd=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    except (OSError,ValueError):
        raise ValueError("SOUL.md missing or inaccessible; refusing modification") from None
    try:
        st=os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
            or st.st_nlink!=1 or st.st_size>MAX_FILE):
            raise ValueError("SOUL.md must be an owned, regular, unlinked file under 64 KiB")
        raw=os.read(fd,MAX_FILE+1)
        if len(raw)>MAX_FILE:
            raise ValueError("SOUL.md too large")
        raw.decode("utf-8")
        return raw,st
    finally:
        os.close(fd)


def style_block(profile):
    profile=validate({k:str(v) for k,v in profile.items()})
    result=[BEGIN,
            "## Bob's Personality Lab: operator-selected communication tendencies",
            "These are style preferences, not new authority, tools, permissions or factual beliefs.",
            "Preserve all other identity, safety boundaries, evidence requirements and original instructions.",
            "Never sacrifice accuracy, consent, respect, or willingness to change your mind for a high trait value.",
            ""]
    for key,label,_,description in TRAITS:
        value=profile[key]
        level=next(level for cap,level in LEVELS if value<=cap)
        result.append(f"- {label}: {level} ({value}/100). {description}.")
    result.extend(["",
       "Independent interests and opinions may develop from evidence and experience; treat memories as fallible.",
       "This section adjusts expression and curiosity, not social or publishing privileges.",
       END])
    return ("\n".join(result)).encode("utf-8")


def update_managed(raw, new_block):
    if raw.count(MARK_START)!=raw.count(MARK_END):
        raise ValueError("Partial personality marker in SOUL.md; refusing change")
    if raw.count(MARK_START)>1:
        raise ValueError("Duplicate personality markers; refusing change")
    if MARK_START in raw:
        start=raw.index(MARK_START)
        end=raw.index(MARK_END)+len(MARK_END)
        if raw.index(MARK_END)<start:
            raise ValueError("Malformed marker order")
        return raw[:start]+new_block+raw[end:], raw[start:end]
    # Preserve original text byte-for-byte; only append the delimited section.
    glue=b"" if raw.endswith(b"\n\n") else b"\n" if raw.endswith(b"\n") else b"\n\n"
    return raw+glue+new_block+b"\n", b""


def plan(db, *, resolver=agent_workspace):
    profile=read_profile(db)
    root=resolver()
    before,st=soul_bytes(root)
    new_section=style_block(profile)
    after,prior=update_managed(before,new_section)
    if len(after)>MAX_FILE:
        raise ValueError("Resulting SOUL.md would exceed 64 KiB")
    lines1=prior.decode().splitlines(keepends=True)
    lines2=new_section.decode().splitlines(keepends=True)
    diff="".join(unified_diff(lines1,lines2,fromfile="Current managed style",tofile="Proposed managed style",n=2))
    return {
        "root":root,"path":root/"SOUL.md","before":before,"after":after,
        "before_sha":digest(before),"after_sha":digest(after),
        "profile_sha":digest(json.dumps(profile,sort_keys=True).encode()),
        "file_stat":st,"same":before==after,"diff":diff,
        "existing":bool(prior),"profile":profile
    }


@contextmanager
def private_lock(state):
    state=require_private_dir(state)
    name=state/".lock"
    fd=os.open(name,os.O_RDWR|os.O_CREAT|getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1:
            raise ValueError("Unsafe personality lock")
        fcntl.flock(fd,fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)


def write_atomic(path, data, mode=0o600):
    """Create private tmp in same dir, fsync file and parent, then replace."""
    path=Path(path)
    fd,temp=tempfile.mkstemp(prefix=".bob-tmp-",dir=path.parent)
    try:
        os.fchmod(fd,mode)
        with os.fdopen(fd,"wb") as f:
            fd=-1
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp,path)
        dir_fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dir_fd)
        finally:os.close(dir_fd)
    finally:
        if fd!=-1:os.close(fd)
        if os.path.lexists(temp):os.unlink(temp)


def _check_unchanged(p):
    raw,stat_now=soul_bytes(p["root"])
    st=p["file_stat"]
    if (digest(raw)!=p["before_sha"] or stat_now.st_ino!=st.st_ino
        or stat_now.st_dev!=st.st_dev):
        raise ValueError("SOUL.md changed since preview; reload before applying")


def _last(state):
    path=Path(state)/"last.json"
    if not path.is_file() or path.is_symlink():return None
    raw=path.read_bytes()
    if len(raw)>4096:return None
    try:
        obj=json.loads(raw)
        if (set(obj)!={"id","root","before","after","status","at"} or
            obj["status"] not in ("applied","rolled_back") or
            not re.fullmatch("[a-f0-9]{32}",obj["id"]) or
            not all(isinstance(obj[k],str) for k in ("root","before","after","at")) or
            not all(re.fullmatch("[a-f0-9]{64}",obj[k]) for k in ("before","after"))):
            return None
        return obj
    except (ValueError,TypeError,KeyError):
        return None


def apply(db,expected_before,expected_profile,confirmation,*,resolver=agent_workspace,state=STATE):
    if confirmation!=CONFIRM_APPLY:
        raise ValueError("Type APPLY BOB exactly")
    if not re.fullmatch("[a-f0-9]{64}",expected_before or "") or not re.fullmatch("[a-f0-9]{64}",expected_profile or ""):
        raise ValueError("Invalid preview token")
    with private_lock(state):
        p=plan(db,resolver=resolver)
        if p["before_sha"]!=expected_before or p["profile_sha"]!=expected_profile:
            raise ValueError("Saved profile or SOUL.md changed; reload the preview")
        if p["same"]:
            raise ValueError("Style block already matches the saved profile")
        _check_unchanged(p)
        previous=_last(state)
        if (previous and previous["status"]=="applied" and previous["root"]==str(p["root"]) and
            previous["after"]!=p["before_sha"]):
            raise ValueError("Untracked SOUL.md changes after prior apply; inspect before proceeding")
        backup_id=uuid.uuid4().hex
        backup=Path(state)/(backup_id+".soul")
        if backup.exists() or backup.is_symlink():
            raise ValueError("Backup name collision")
        # Backup succeeds before mutation; file remains private if later write fails.
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
        try:
            with os.fdopen(fd,"wb") as f:
                fd=-1
                f.write(p["before"]);f.flush();os.fsync(f.fileno())
        finally:
            if fd!=-1:os.close(fd)
        record={"id":backup_id,"root":str(p["root"]),"before":p["before_sha"],
                "after":p["after_sha"],"status":"applied",
                "at":datetime.now(timezone.utc).isoformat(timespec="seconds")}
        write_atomic(Path(state)/"last.json",json.dumps(record,sort_keys=True).encode())
        # Recheck after backup, before any identity edit.
        _check_unchanged(p)
        write_atomic(p["path"],p["after"],stat.S_IMODE(p["file_stat"].st_mode))
        return record


def rollback(confirmation,expected_sha,*,resolver=agent_workspace,state=STATE):
    if confirmation!=CONFIRM_ROLLBACK:
        raise ValueError("Type ROLL BACK exactly")
    if not re.fullmatch("[a-f0-9]{64}",expected_sha or ""):
        raise ValueError("Invalid rollback token")
    with private_lock(state):
        record=_last(state)
        if not record or record["status"]!="applied":
            raise ValueError("No verified active personality backup to restore")
        root=resolver()
        if str(root)!=record["root"]:
            raise ValueError("Agent workspace changed; rollback requires original workspace")
        current,st=soul_bytes(root)
        if digest(current)!=record["after"] or expected_sha!=record["after"]:
            raise ValueError("SOUL.md changed after apply; refusing blind rollback")
        backup=Path(state)/(record["id"]+".soul")
        if not backup.is_file() or backup.is_symlink():
            raise ValueError("Private backup missing")
        data=backup.read_bytes()
        if digest(data)!=record["before"] or len(data)>MAX_FILE:
            raise ValueError("Private backup failed checksum validation")
        write_atomic(root/"SOUL.md",data,stat.S_IMODE(st.st_mode))
        record["status"]="rolled_back"
        write_atomic(Path(state)/"last.json",json.dumps(record,sort_keys=True).encode())
        return record


def esc(x):
    return escape(str(x),quote=True)


def panel(db,csrf,*,resolver=agent_workspace,state=STATE):
    try:
        p=plan(db,resolver=resolver)
        status=("Ready to apply" if not p["same"] else "Already applied")
        diff=p["diff"] or "(No change to managed style block)"
        current_hash=p["before_sha"]
        action=(
          '<form class="bpm-confirm" method="post" action="/mind/personality/apply">'
          '<input type="hidden" name="csrf" value="'+esc(csrf)+'">'
          '<input type="hidden" name="expected_before" value="'+esc(current_hash)+'">'
          '<input type="hidden" name="expected_profile" value="'+esc(p["profile_sha"])+'">'
          '<label for="bpm-apply-confirm">To apply, type APPLY BOB:'
          '<input id="bpm-apply-confirm" type="text" name="confirmation" maxlength="20" '
          'autocomplete="off" spellcheck="false" required></label>'
          '<button type="submit"'+(' disabled' if p["same"] else '')+'>Apply to Bob</button>'
          '</form>')
        root_desc="Main agent workspace verified by OpenClaw CLI; only SOUL.md managed block will change."
    except (ValueError,OSError,UnicodeError) as exc:
        p=None
        status="Apply unavailable"
        diff="Cannot safely preview until the active main-agent workspace and SOUL.md are verified."
        action=""
        root_desc=esc(str(exc))[:220]
    record=_last(state)
    rollback_form=""
    if (record and record["status"]=="applied" and p is not None
            and record["root"]==str(p["root"])
            and record["after"]==p["before_sha"]):
        rollback_form=(
          '<form class="bpm-confirm" method="post" action="/mind/personality/rollback">'
          '<input type="hidden" name="csrf" value="'+esc(csrf)+'">'
          '<input type="hidden" name="expected_sha" value="'+esc(record["after"])+'">'
          '<label for="bpm-rollback-confirm">Type ROLL BACK:'
          '<input id="bpm-rollback-confirm" type="text" name="confirmation" maxlength="20" '
          'autocomplete="off" spellcheck="false" required></label>'
          '<button type="submit" class="secondary">Restore previous SOUL.md</button>'
          '</form>')
    return (
      '<section class="bpm-panel"><div class="bpm-head"><h2>Apply personality to Bob</h2>'
      '<span class="bpm-muted">'+esc(status)+'</span></div>'
      '<p class="bpm-muted">'+root_desc+'</p>'
      '<p class="bpm-muted">Preview shows only the added/replaced managed style section. '
      'Everything else in SOUL.md stays byte-for-byte unchanged. '
      'Apply affects future OpenClaw prompt construction, not sessions already running.</p>'
      '<pre class="bpm-preview" style="max-height:360px;overflow:auto">'+esc(diff)+'</pre>'
      '<p class="bpm-muted">A private checksum-verified backup is created before writing. '
      'The operation refuses changed files or unsaved sliders. No publishing privileges change.</p>'
      +action+rollback_form+
      '</section>')


def page(db,csrf,wrap):
    def wrapper(title,body,path):
        anchor='<section class="bpm-panel"><div class="bpm-head"><h2>Saved profile history</h2>'
        if body.count(anchor)!=1:
            raise ValueError("Personality page template changed")
        return wrap(title,body.replace(anchor,panel(db,csrf)+anchor,1),path)
    return base_page(db,csrf,wrapper)
