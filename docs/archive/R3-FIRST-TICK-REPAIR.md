# R3 timer active but no NEXT: first-tick bootstrap repair

The real OMEN's owner-run `systemctl --user list-timers --all bob-r3-propose.timer` showed the timer present but with `NEXT -` and `LAST -`; a one-hour journal query for the proposal service had no entries. The existing user timer's only scheduling rule is `OnUnitInactiveSec=35min`, which requires an earlier service deactivation. A brand-new service without a previous run has no starting point. The scheduler was installed correctly, but its first cycle was not scheduled. The legacy publisher and Scout have not been interrupted and R3 publishing is still hard Off.

**Fix:** Add `[Timer]\nOnActiveSec=2min` as a single, SHA-checked **user timer drop-in**. The existing `OnUnitInactiveSec=35min` remains in the original unit, preserving subsequent cadence. The original two installed unit files and the private handoff journal remain byte-for-byte unchanged. On each subsequent timer activation, the first-run anchor also exists. This **does not** invoke a model immediately, grant Moltbook credentials, enable a new publisher or permit R3 comments. The first natural run can be a skipped/none/refused outcome if no eligible Scout source or model response exists.

The source-only repair is `scripts/repair_r3_first_timer.py`, with three commands. **The script is not part of the existing signed cutover1 release; it runs from the trusted clean source checkout after review and merge.**

- `--check`: read-only. Demands the verified installed cutover1 hard-Off release, a completed exact original handoff journal, unchanged installed user units, inactive old R2 shadow timer, idle proposal/legacy publisher services, active enabled R3/Scout/legacy publisher timers, and no competing R3 publisher. It refuses unknown extra drop-ins.
- `--apply`: requires terminal owner confirmation `REPAIR R3 FIRST TIMER`, performs the same checks and writes exactly `~/.config/systemd/user/bob-r3-propose.timer.d/10-first-run.conf`. It reloads user systemd and restarts **only** the proposal timer, then checks systemd exposes a monotonic next deadline. It does not start the proposal service manually, change the existing publisher/Scout timers, or touch SQLite.
- `--undo`: independently typed `UNDO R3 FIRST TIMER`, removes only the verified exact drop-in and reloads/restarts the proposal timer, leaving the original handoff journal intact. If returning to R2 Shadow is needed, run this **before** the existing owner-approved `r3_service_handoff.py --recover`. Original handoff recovery was developed before bootstrap and does not know the extra drop-in.

## Intended owner acceptance after PR merge

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/repair_r3_first_timer.py --check
python3 scripts/repair_r3_first_timer.py --apply
systemctl --user list-timers --all bob-r3-propose.timer
```

Before applying, make sure the read-only check passes. The apply step asks for the exact typed confirmation and is **not** automatically executed by the repo or an update. Afterward, the important result is an actual date/time under `NEXT`, not just `active`. Later, inspect `journalctl --user -u bob-r3-propose.service --since "1 hour ago" --no-pager -n 30` for the natural trigger. No forced service invocation or public Moltbook canary.

## Safety and failure handling

If the check refuses, stop and report the status. Do not edit original timer unit files manually: their hashes are part of the proven handoff journal. If a partial repair left the exact verified drop-in, recheck and follow the owner-only repair or undo path; never override changed/symlinked files. If systemd shows no next activation after repair, the source script returns failure even though the drop-in may have been created, so investigate before attempting any further systemd operation. This repair is a new on-host unit configuration change requiring explicit owner approval, not something silently inferred from successful earlier R3 installation.
