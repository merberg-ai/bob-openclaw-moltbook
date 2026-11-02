# v0.7.1 Production Deployment Controller: read-only planning gate

The original-manager real-systemd rollback acceptance passed 238 tests on OMEN. This phase adds `scripts/plan_v071_production_deployment.py` to evaluate the **current** effective production user service, pinned installed manager, recent private SQLite backup, and the actual two-file candidate package without touching installed files or restarting anything.

No production deployment execution mode exists. A green plan is **not** permission to install. The controller exposes only summary booleans and candidate SHA-256 hashes, never the service's inline environment or secrets.

## Operator acceptance

First create a fresh verified private backup on OMEN if the previous backup is old:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/backup_live_sqlite.py"
```

Keep the printed backup path private. Then run the regressions and substitute that exact path into the second command:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/plan_v071_production_deployment.py && python3 -m unittest discover -s tests -p 'test_*.py' -q"
```

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/plan_v071_production_deployment.py --backup /home/openclaw/.local/state/bob-baseline/backups/REPLACE-WITH-ACTUAL.sqlite3"
```

Expected 244 regression tests (238 previous + six) and `v0.7.1 PRODUCTION CONTROLLER PLAN: PASS`, subject to OMEN verification.

## Before a deployment executor can be added

A separately reviewed executor must persist a fsynced recovery manifest before changing any code, stage files on the installed filesystem with no symlink traversal, validate owner and modes, preserve the effective Python interpreter/working directory/environment, avoid clobbering concurrent modifications, bound restart and authenticated health probing, check actual systemd state, and restore original code on failure without overwriting newer database data. The recurring preview synchronization ValueError needs a separate diagnostic. **Operator approval for actual production restart is required in a later phase.**
