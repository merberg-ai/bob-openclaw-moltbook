# v0.7.1 guarded installer integration: sandbox milestone

The operator accepted 211 unit tests and the read-only *effective* systemd preflight on OMEN. The service launches the pinned installed manager through a Python interpreter, not by direct shebang execution.

This step commits `scripts/rehearse_v071_guarded_installer.py`, a deliberately **non-deployable** installer-controller sandbox. It exercises checksum-verified two-file staging, release-pointer guard, transaction lock and persistent journal, ephemeral 127.0.0.1 HTTP health, code-only rollback, failed-recovery incident, and preservation of synthetic SQLite writes. It has no production install flag, systemctl call, real credentials, LAN health endpoint or real database access.

## Operator verification

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_guarded_installer.py --scenario success && python3 scripts/rehearse_v071_guarded_installer.py --scenario health-failure && python3 scripts/rehearse_v071_guarded_installer.py --scenario recovery-failure && python3 scripts/rehearse_v071_guarded_installer.py --scenario refuse-drift"
```

Expected regression count **217** (211 previous + six), subject to OMEN verification. All four scenarios should show `v0.7.1 GUARDED INSTALLER SANDBOX: PASS`.

## Remaining deployment blockers

This does **not** yet replace live files or restart the actual user systemd service. Before a production mode is written, implement a separate reviewed production installer with a durable install manifest, no-symlink/owner/path protections, rollback without overwriting SQLite, bounded real authenticated health checks, interrupted transaction operator recovery, expected Python interpreter/argv validation and an explicit consent gate. Verify that installer against a disposable real systemd user unit before any live deployment. Never mistake a green sandbox for deployment authorization.
