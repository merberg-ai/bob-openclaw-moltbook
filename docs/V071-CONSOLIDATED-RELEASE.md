# v0.7.1 consolidated release workflow

A single release-readiness command now checks the actual pinned installed manager, effective user-systemd service, fresh private SQLite backup, the generated two-file release package, the currently running authenticated local dashboard GET routes, and the full regression suite. The production executor script is **present for code review but MUST NOT be invoked with --apply yet**. This is a deliberate approval boundary, not another invitation to begin production changes.

The executor is `scripts/deploy_v071_activity_manager.py`. It implements an opt-in two-file regular-file replacement at the actual installed script path, a private fsynced deployment journal and sealed source copies, single-process deployment locking, controlled user-systemd restart, bounded authenticated HTTP health, code-only rollback, and refusal if unexpected installed bytes are discovered. A successful transaction leaves a terminal journal that blocks accidental redeployment. It does not revert newer SQLite writes.

**Outstanding before authorizing --apply:** confirm live port is still 18790, real credentials file is available privately, and current binding/Host settings permit the loopback authenticated probe; test end-to-end on the OMEN disposable systemd harness and review interrupted-write recovery. The production executor deliberately fails closed on an incomplete journal; it does not yet implement automatic resume from an operator process crash. The observed read-only preview synchronization ValueError is separate and should be diagnosed, not quietly ignored. Do not share the private auth file or database backups.

## One consolidated read-only command

Use the private backup path printed by `backup_live_sqlite.py` and refresh the backup if it is older than 24h:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/v071_release_gate.py scripts/deploy_v071_activity_manager.py && python3 scripts/v071_release_gate.py --backup /home/openclaw/.local/state/bob-baseline/backups/REPLACE-WITH-CURRENT.sqlite3"
```

Expected **277 tests** (267 previously verified, four consolidated gate tests, six executor contract tests), and `v0.7.1 CONSOLIDATED RELEASE GATE: PASS`, to be confirmed by OMEN. No transient systemd units are created and no service is restarted. Do not run the --apply option until a separate explicit production approval after review.

## Known limitation

This command is read-only but includes actual HTTP GETs using the existing private Basic auth values locally. No credentials are printed, uploaded, or passed on the command line. For diagnostic refusals prefer reporting only the summary booleans.
