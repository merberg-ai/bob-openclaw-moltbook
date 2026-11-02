# v0.7.1 end-to-end disposable systemd install integration

The opt-in script `scripts/rehearse_v071_end_to_end_systemd.py` combines the actual pinned regular-file installation transaction, real generated candidate, original manager recovery and uniquely named disposable user-systemd units. Both versions run from the **same temporary installed manager pathname** and synthetic HOME/SQLite. HTTP checks cover /healthz, /, /activity, /originals and POST refusal. The failed-health scenario injects a failure verdict after the candidate has passed real HTTP. The restart-failure scenario simulates inability to start the candidate, restores original bytes, then checks the original manager's HTTP health.

It is a controlled rehearsal only. No production unit, database, credentials, public/LAN binding, service configuration or installed files are used. The HTTP checks are from a disposable read-only handler; real production authenticated LAN health is still NOT implemented.

## First verify regressions (no transient unit)

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/rehearse_v071_end_to_end_systemd.py && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_end_to_end_systemd.py"
```

Expected **266** tests (260 previous plus six) and PLAN ONLY, pending host validation.

## Then explicitly opt in to disposable systemd units

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/rehearse_v071_end_to_end_systemd.py --execute-transient --scenario healthy && python3 scripts/rehearse_v071_end_to_end_systemd.py --execute-transient --scenario failed-health && python3 scripts/rehearse_v071_end_to_end_systemd.py --execute-transient --scenario restart-failure"
```

Expected three `v0.7.1 END-TO-END SYSTEMD INSTALL: PASS` reports. The failed-health and restart-failure reports should show `outcome: baseline_recovered`, actual original manager HTTP health, and restored code bytes. If cleanup reports refusal, do not retry before investigating any remaining uniquely named test units.

## Production blockers

This does not exercise actual production authentication, nor does it implement a production deployment executor. The recurring sync-time read-only preview ValueError is unresolved. A separate authorization, live revalidation, crash-durable recovery state stored outside disposable directories and authenticated health must precede production execution.
