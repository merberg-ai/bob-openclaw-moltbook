# v0.7.1 real user-systemd staging, opt-in and disposable

This milestone adds `scripts/rehearse_v071_user_systemd.py`, which **by default only prints a plan**. With `--execute-transient`, it uses `systemd-run --user --collect` to start an ephemeral uniquely named `bob-v071-stage-<random>.service` running **this script's synthetic HTTP fixture** through Python, checks `127.0.0.1:<ephemeral>/healthz` and effective ActiveState, then stops the transient unit in a finally block. It does not reference or modify `bob-activity-manager.service`, production executable, database, credentials, or Moltbook.

This is **actual user-systemd process startup**, unlike prior in-process HTTP simulations. It is still NOT a production installer.

## Regression + dry-run, first

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_user_systemd.py"
```

Expected **225 tests** (217 prior + eight) if host testing verifies; default should print `v0.7.1 USER SYSTEMD STAGING: PLAN ONLY`.

## Separate explicit opt-in transient unit execution

Only after the regression suite passes, run:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/rehearse_v071_user_systemd.py --execute-transient"
```

Expected `v0.7.1 USER SYSTEMD STAGING: PASS`. This **does create and stop a temporary user systemd unit**. It is not read-only, although it does not target the production service. If cleanup reports an error, review and remove the uniquely named stage unit manually before retrying. No public/LAN listener or real credentials are used.

## Limits

- This proves that an isolated Python+script transient service can be launched and stopped with loopback health, not that the real Activity Manager is safe to replace.
- The synthetic unit can fail due to the user systemd manager, transient unit restrictions, or port contention, even if the live service remains healthy.
- This script does not configure real drop-ins, reload systemd, validate production auth, or replace code. **Do not deploy** candidate code; review ZIP remains non-deployable.
- A future isolated two-file real-service staged restart/rollback acceptance and explicit production authorization remain mandatory.
