# v0.7.1 host preflight: read-only deployment gate

The browser UI has passed operator visual review. Before designing a live update, confirm that the manager on OMEN still matches the **exact pinned source**, that an independently verified SQLite backup is fresh/private/intact, and that the current Activity Manager is running.

**This is not an installer**. It makes no edits, restarts, publishing requests, database writes, or release switches. A PASS does **not** authorize deployment: the service entrypoint and credentials isolation still require independent review.

## Run on OMEN after taking a fresh backup

First create a new backup using the existing v0.7.0 workflow documented in [BASELINE-BACKUP.md](BASELINE-BACKUP.md). Copy its *exact local path*, but **never share the backup or its contents**.

From the v0.7.1 checkout in OpenClawLab:

```bash
git pull --ff-only
python3 -m unittest discover -s tests -p 'test_*.py' -q
python3 scripts/preflight_v071_live.py --backup "$HOME/.local/state/bob-baseline/backups/REPLACE-WITH-EXACT-FILENAME.sqlite3"
```

The script assumes the installed manager is `~/.local/bin/bob-activity-manager`. If the installed service uses a different verified executable, pass `--live-manager /absolute/path`. **Do not move or overwrite it to make a failing check pass.**

It prints only PASS/REFUSED for:
- Exact pinned v0.7.0 source hash (ensures no unknown live-manager drift).
- Owner-private 0600 regular backup under owner-private 0700 parent, created within 24 hours, with SQLite integrity check.
- `systemctl --user show bob-activity-manager.service` reporting loaded/active/running.

A failed check exits nonzero. A symlink, outdated/insecure/corrupted backup, modified manager, or stopped service is a **stop signal**. A manager hash mismatch may reflect a different legitimate live revision: investigate privately rather than forcing installation. Backup contents and systemd ExecStart/Environment values are never printed.

## Remaining mandatory gates

1. Inspect the real service entrypoint and release-directory layout privately, without uploading secret-bearing systemd lines.
2. Build and test a versioned **two-file** updater: generated manager plus `navigation_shell.py` must travel together.
3. Verify old-source/code-only rollback, LAN Basic auth, Origin/CSRF, approval and publishing affordances in safely isolated acceptance tests without sending Moltbook actions.
4. Require explicit operator approval before any live service restart or switch.
5. Verify health after the authorized switch; on failure restore the old executable(s), not an outdated SQLite snapshot.

The review ZIP still says `deployable: false`. Never use it directly as a live installer.
