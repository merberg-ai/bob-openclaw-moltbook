"""R4 exact installed code and publisher attestation, READ ONLY.

No database/network/credential access. The real single-publisher adapter
must check this against the versioned private updater registry BEFORE any
source/owner/remote preflight or API key access. All R4 candidate files are
tracked by existing updater SHA-256; simply importing a checkout is not
authority to send.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

RELEASE="v0.8.0-autonomy1"
PROPOSAL_RELEASE="v0.8.0-r4propose1"
SUPPORTED=frozenset((RELEASE,PROPOSAL_RELEASE))
REGISTRY_FORMAT="bob-updater-v1"
REQUIRED=frozenset((
    "bob-moltbook-publisher","bob-activity-manager","bob_r3_package.pyz",
    "bob_r4_policy.py","bob_r4_controls.py","bob_r4_projection.py",
    "bob_r4_ledger.py","bob_r4_suggestions.py","bob_r4_schema.py",
    "bob_r4_outbox.py","bob_r4_budget.py","bob_r4_remote_gate.py",
    "bob_r4_final_gate.py","bob_r4_publisher_adapter.py",
    "bob_r4_installed_gate.py","bob_r4_web.py",
    "bob_r4_agent.py","bob_r4_producer.py","bob-r4-propose",
))
DIGEST=re.compile(r"[a-f0-9]{64}\Z")
MAX_SIZE=524288


def _owned(path:Path,directory:bool,*,private:bool=False)->bool:
    try:
        st=path.lstat()
    except OSError:
        return False
    return (st.st_uid==os.geteuid() and
            bool(stat.S_ISDIR(st.st_mode))==directory and
            (stat.S_IMODE(st.st_mode)&(0o077 if private else 0o022))==0 and
            not path.is_symlink())


def verify(*,home:Path|None=None)->bool:
    """Exact hash/owner/release check. No symlinks or automatic repair."""
    try:
        base=Path.home() if home is None else Path(home)
        state=base/".local/state/bob-updater"
        installed=state/"installed.json"
        journal=state/"transaction.json"
        bindir=base/".local/bin"
        if (not _owned(base,True) or
                not _owned(base/".local",True) or
                not _owned(base/".local/state",True) or
                not _owned(state,True,private=True)
                or not _owned(bindir,True)
                or not _owned(installed,False,private=True)):
            return False
        # The existing updater leaves a completed transaction journal on
        # disk. Only a trusted, exact, COMPLETE signed-release journal is
        # allowed. Prepared/installed/migrated/restarted and incident phases
        # are never authority to load publisher credentials.
        if (not _owned(journal,False,private=True)
                or not 0<journal.stat().st_size<=16384):
            return False
        detail=json.loads(journal.read_text(encoding="utf-8"))
        if (type(detail) is not dict or
                detail.get("format")!=REGISTRY_FORMAT
                or detail.get("release") not in SUPPORTED
                or detail.get("phase")!="complete"
                or detail.get("restart_manager") is not True):
            return False
        if not 0<installed.stat().st_size<=65536:
            return False
        info=json.loads(installed.read_text(encoding="utf-8"))
        if (type(info) is not dict or
                set(info)!={"format","release","files"} or
                info["format"]!=REGISTRY_FORMAT or
                info["release"] not in SUPPORTED
                or detail["release"]!=info["release"] or
                type(info["files"]) is not dict):
            return False
        hashes=info["files"]
        if not REQUIRED.issubset(hashes.keys()):
            return False
        for name in REQUIRED:
            expected=hashes[name]
            p=bindir/name
            if (type(expected) is not str or not DIGEST.fullmatch(expected)
                    or not _owned(p,False) or
                    not 0<p.stat().st_size<=MAX_SIZE or
                    hashlib.sha256(p.read_bytes()).hexdigest()!=expected):
                return False
        return True
    except (OSError,ValueError,TypeError,UnicodeError,KeyError):
        return False
