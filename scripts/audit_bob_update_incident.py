#!/usr/bin/env python3
"""Read-only forensic inspection of a refused Bob release transaction.

Does not read or print contents of scout drafts, post text, credentials,
publication data, or private backup files. No SQLite writes, POSTs, restarts,
or journal edits. The only output is structural and SHA-256 consistency status.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import sys

import bob_release_updater as updater

HEX = re.compile(r"[0-9a-f]{64}\Z")


def private_json(path):
    updater.safe_private(path)
    if path.stat().st_size > 32768:
        raise ValueError("oversized transaction metadata")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    print("BOB UPDATE INCIDENT AUDIT (read-only, no changes)")
    try:
        installed = updater.registry()
        planned = updater.manifest(updater.checkout_from_config())
        journal = updater.read_journal()
        if not journal:
            raise ValueError("no transaction journal present")
        print("installed_release:", installed["release"])
        print("release_in_journal:", journal["release"])
        print("transaction_phase:", journal["phase"])
        print("registered_live_hashes:", "MATCH" if updater.live_ok(installed) else "DRIFT")
        if journal["release"] != planned["release"]:
            raise ValueError("journal release differs from current manifest")
        tx = updater.STATE_DIR / ("tx-" + journal["release"])
        updater.safe_private(tx, directory=True)
        originals = private_json(tx / "original.json")
        candidates = private_json(tx / "candidate.json")
        previous = private_json(tx / "registry-before.json")
        if (not isinstance(originals,dict) or not isinstance(candidates,dict)
                or not isinstance(previous,dict)
                or set(originals) != set(candidates)
                or set(originals) != {f["name"] for f in planned["files"]}):
            raise ValueError("release archive structure mismatch")
        if previous != installed:
            print("registry_before:", "DIFFERS")
            raise ValueError("registry does not equal archived baseline")
        print("registry_before:", "MATCH")
        states = {}
        for name in sorted(originals):
            if not updater.TARGET.fullmatch(name):
                raise ValueError("unexpected archive entry")
            oldsha = originals[name]
            newsha = candidates[name]
            if (oldsha != "absent" and (not isinstance(oldsha,str) or
                                        not HEX.fullmatch(oldsha))):
                raise ValueError("invalid original digest")
            if not isinstance(newsha,str) or not HEX.fullmatch(newsha):
                raise ValueError("invalid candidate digest")
            if oldsha == "absent":
                backup_exists = (tx / ("old-" + name)).exists()
                if backup_exists:
                    raise ValueError("unexpected archive of absent source")
            else:
                oldfile = tx / ("old-" + name)
                updater.safe_private(oldfile)
                if updater.digest(oldfile.read_bytes()) != oldsha:
                    raise ValueError("previous code archive has changed")
            target = updater.BIN / name
            if target.is_symlink():
                state = "UNEXPECTED SYMLINK"
            elif not target.exists():
                state = "absent" if oldsha == "absent" else "MISSING ORIGINAL"
            elif not target.is_file() or target.stat().st_uid != os.getuid():
                state = "INVALID TYPE OR OWNER"
            else:
                sha = updater.digest(target.read_bytes())
                state = ("baseline" if sha == oldsha else
                         "candidate" if sha == newsha else "UNKNOWN MODIFICATION")
            states[name] = state
            print("file", name, ":", state)
        clean = all(s == "baseline" or s == "absent" for s in states.values())
        if not clean:
            print("outcome: CODE STATE REQUIRES MANUAL RECOVERY")
            return 2
        print("outcome: ORIGINAL CODE PRESENT; INTERRUPTED JOURNAL STILL NEEDS GUARDED RECONCILIATION")
        print("No changes made. Keep transaction archive intact.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("outcome: REFUSED", type(exc).__name__)
        print("Do not retry the update or remove transaction files.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
