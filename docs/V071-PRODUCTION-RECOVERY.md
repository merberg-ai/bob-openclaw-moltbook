# v0.7.1 interrupted-production-transaction recovery

The production executor now has an explicit `--recover` mode requiring a separate `RECOVER-BOB-V071` confirmation string. It refuses absent, completed, incident or malformed journals; holds the exclusive deployment lock; checks sealed source checksums; refuses externally modified installed files; restores only the original executable and removes the newly introduced navigation module; restarts the existing user systemd service and verifies authenticated HTTP and installed hashes. It never rolls back SQLite.

**NOT RELEASE AUTHORIZATION:** This recovery mode targets live Bob and can restart the service. It must not be invoked as a test. Do not run `--apply` or `--recover` until the executor receives final end-to-end validation and explicit operator approval. Recovery is for interrupted transactions; it cannot resolve arbitrary incidents.

## Safe verification of the new code (no production change)

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/deploy_v071_activity_manager.py && python3 scripts/deploy_v071_activity_manager.py --backup /home/openclaw/.local/state/bob-baseline/backups/bob-activity-20261029T000527374127Z-170034.sqlite3"
```

This invokes only PLAN ONLY. It intentionally does not trigger live restart, auth read, or any database update.

## Remaining review before deploy

The v0.7.1 candidate systemd acceptance and consolidated authenticated release gate have passed. Before applying the production upgrade, review the exact executor and rollback against a disposable installed-path fixture including failure between replace and journal, restart failure, stale backup, and failed recovery. The previous disposable end-to-end baseline probe was brittle and has a subsequent source fix that has not yet been accepted on OMEN. No production release has occurred.
