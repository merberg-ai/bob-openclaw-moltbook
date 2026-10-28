# v0.7.0: Isolated release and rollback rehearsal

**This is a source-only simulation, not an installer or live Bob update.** It is intentionally designed to work with the nine reviewed Python source files in the development checkout. It cannot start, stop, restart, enable or disable services, contact Moltbook/Ollama, access live credentials or inspect the live SQLite database.

## Verified service state before this stage

Operator's OpenClawLab check (2026-10-28) reported:

- User `openclaw-gateway.service` and `bob-activity-manager.service` **active/running, enabled**.
- User `bob-moltbook-scout.timer`, `bob-moltbook-publisher.timer`, `bob-original-worker.timer`, and `bob-startup-reconcile.timer` **active/waiting, enabled**.
- Their worker/reconcile `.service` units are **inactive/dead, static**, consistent with timer-triggered oneshot jobs (status alone does not prove every job succeeds).
- Legacy system `bob-moltbook-scout.timer` **inactive/dead, disabled** and `bob-moltbook-scout.service` **inactive/dead, static**. They are duplicate names in different scopes, **not concurrent active scouts**. Leave these legacy units intact until a real reboot/rollback plan is validated.
- Linux `openclaw` user lingering **yes**. It does not by itself start WSL before Windows user sign-in.
- Windows Startup-folder `Bob OpenClaw Startup` PowerShell wrapper references WSL, OpenClawLab and systemd; `OpenClaw Companion` is a separate executable. No matching Windows scheduled tasks or Run entries were found. Unattended cold-boot readiness remains unproven.

## One PowerShell command

Run from the OMEN while Bob continues running:

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && GIT_TERMINAL_PROMPT=0 git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_release_rollout.py"
~~~

The tool verifies the exact nine reviewed-source SHA-256 values and Python syntax, uses a fresh `TemporaryDirectory`, stages two isolated copy-only release trees, writes immutable-style JSON checksums, simulates an atomic `current` symlink switch, creates **synthetic SQLite** records and an **online synthetic SQLite backup**, intentionally fails a simulated health gate, and rolls the code pointer back while preserving a synthetic write made after the backup. All temporary files are automatically removed.

Passing this rehearsal proves **basic atomic pointer/SQLite-backup mechanics only**. It does not prove deploy permissions, unit templates, executable API integration, actual worker drains, service restart behavior, Windows recovery, live schema migrations, or database rollback safety. Nothing here is approved for deployment to production.

## Remaining acceptance before a real updater

1. Privately stage/review and sanitize exact installed service unit/drop-in definitions. Unit names and state alone are insufficient to reconstruct equivalent templates.
2. Build an independent staging installation outside the live `~/.local/bin`, systemd and activity database directories; wire test-only configuration, never real publishing credentials.
3. Prove pause/drain semantics for workers and publisher uncertain-delivery states, online live-backup procedure, additive migration handling, idempotent stop/start and health checks.
4. Test staged upgrade and rollback with the actual installed service templates, then separately test Windows user-login and cold-boot startup behavior.
5. Only after operator acceptance, implement `bobctl check-update`, `update --dry-run`, `update`, and `rollback` for pinned signed/checksummed releases.

**Do not disable the old system-level scout solely because its unit definition still exists; it is currently inactive and its timer disabled.**
