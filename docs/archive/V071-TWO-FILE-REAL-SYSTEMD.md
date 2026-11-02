# v0.7.1 real user-systemd two-file candidate and recovery rehearsal

This increment launches the **actual checksum-pinned generated manager and sibling navigation module** inside the existing read-only preview harness using a disposable HOME, fake SQLite, disabled POST routes and a uniquely named user-systemd transient unit. It probes /healthz and the three UI routes, then stops the candidate. The alternate failure-injection scenario subsequently starts a **separate synthetic recovery HTTP fixture**, validates it and stops it. No live Activity Manager service, secrets, or publishing endpoint are accessed.

**Scope distinction:** The recovery fixture is NOT the original manager running under systemd. This is a candidate boot and synthetic recovery integration test, not yet a full two-file code rollback proof or production installer. The prior release-pointer and journal synthetic rehearsals cover code rollback separately. Do not mistake a green result here for production permission.

## First: regression and plan only

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_two_file_systemd.py"
```

Expected: **232 tests** (225 previous plus seven) if the host confirms; default prints PLAN ONLY.

## Explicit opt-in: real disposable systemd units

Healthy candidate:
```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/rehearse_v071_two_file_systemd.py --execute-transient --scenario healthy"
```

Injected health failure and separate recovery HTTP fixture:
```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && python3 scripts/rehearse_v071_two_file_systemd.py --execute-transient --scenario failed-health"
```

Both should print `v0.7.1 TWO-FILE SYSTEMD: PASS`. The second reports `outcome: synthetic_recovery_healthy`, explicitly not baseline manager restored. A failed unit cleanup must be investigated before retrying. The command may create and stop two uniquely named transient user units; it never writes production unit files.

Next: run a true baseline-manager restart in a disposable environment with the same socket and synthetic state, atomic source switch, journal, post-switch health and recovery acceptance. Only then design and separately authorize a production deployment.
