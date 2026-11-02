# Scout startup import repair (v0.7.5-scout-importfix1)

**Upgrade:** `v0.7.5-logs2` → `v0.7.5-scout-importfix1`.

## Confirmed operator failure

The operator's WSL2 systemd user unit `bob-moltbook-scout.service` ended with `ExecMainStatus=1`, while `bob-moltbook-scout.timer` remained enabled. Last successful saved Scout checkpoint and feed were from a **different, earlier run** (`20261029T224411Z`), explaining the empty Logs page and absence of a failed Scout feed.

A no-execution Python import smoke test reproduced the direct failure:

```
from bob_memory_recall import readonly_render as approved_memory_context
  ...
from bob_publish_common import DB, event, now
ModuleNotFoundError: No module named 'bob_publish_common'
```

The `bob_publish_common.py` shared SQLite/Scout integrity helper exists in the repository at `src/lib/bob/bob_publish_common.py`, but it was omitted from the v0.7.2 updater's initial managed-file registry and therefore not installed beside `bob-moltbook-scout` and the newer helper modules in `~/.local/bin`. A prior long-lived dashboard process could still have the module through another launch path or loaded module cache. A clean Scout subprocess cannot import it.

## Focused remedy

Install **only** the already-reviewed, unchanged shared helper from the existing repository source as **`~/.local/bin/bob_publish_common.py`** through the standard guarded updater. This makes the dependency importable from the Scout script directory, rather than relying on an interactive shell, user site-packages or a systemd-specific `PYTHONPATH`.

The updater refuses to overwrite an unregistered existing file at that exact target path. The operator's failing import strongly indicates it is absent, but if preflight or installation reports an unmanaged destination, stop and inspect instead of force-overwriting it.

The single-file manifest restarts **Activity Manager** for a clean import environment, uses the existing verified private DB backup and code rollback, but **does not** start Scout, publish a comment, reset the systemd failed state, reconfigure timers, edit secrets, migrate the DB or change permissions.

A new regression test constructs an isolated `~/.local/bin`-style directory, verifies that Scout **fails without the module**, and verifies that Scout, the comment publisher and original worker all **import successfully with the module present** without executing their main functions or touching the live network.

## Simple operator acceptance

1. In OpenClawLab, run `bobctl update`. Confirm `v0.7.5-scout-importfix1`, one file, from `v0.7.5-logs2`, and type `UPDATE`.
2. Rerun the same **read-only import check** that previously failed:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 - <<'PY'
   from pathlib import Path
   import runpy,sys
   script=Path.home()/'.local/bin/bob-moltbook-scout'
   sys.path.insert(0,str(script.parent))
   runpy.run_path(str(script),run_name='scout_import_check')
   print('PASS: Scout import path repaired')
   PY
   ```

3. **Only once imports pass:** check status with `systemctl --user status bob-moltbook-scout.service --no-pager`. The old `failed` state may persist from the previous execution; it isn't cleared by installing a module. To clear the stale flag without running Scout, `systemctl --user reset-failed bob-moltbook-scout.service`. This does **not** trigger a fetch, timer invocation or publication.
4. Check the next ordinary timer invocation. Verify Scout produces a new checkpoint and reaches its normal completed (or appropriate no-new-posts) state. Friend-focused scouting settings and all other publishing safeguards remain unchanged.

## Follow-up

Separately add a hardened persistent **startup-failure summary** to the worker wrapper or systemd `ExecStart` preflight so exceptions that occur **before module initialization** are visible without relying on journal retention. Any logging file must have strict private permissions, sanitized known error codes, no raw third-party data or credentials, and bounded retention.
