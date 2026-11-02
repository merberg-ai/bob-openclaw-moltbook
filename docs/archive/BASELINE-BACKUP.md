# v0.7.0 Phase 2: private online SQLite backup

This step creates an independent, verified backup of Bob's **live SQLite activity database**, then rehearses restoring that backup into a disposable private SQLite database. It does **not** replace the production DB, modify database records, call Moltbook, or restart services.

The Phase 1 inventory (2026-10-28) found 8 application tables, one index and SQLite user_version=0. Preserve this exact schema for the initial release baseline. Version 0 is not itself evidence of corruption.

## On the OMEN, run from PowerShell

Make sure the phase 1 development checkout exists at /home/openclaw/bob-v070-inventory, then:

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git pull --ff-only && python3 scripts/backup_live_sqlite.py"
~~~

This runs as the unprivileged OpenClawLab user. No root or sudo is needed.

**Success output** contains "Integrity: ok isolated restore: passed", the backup path, file size and SHA-256. On failure it prints "Backup FAILED" and exits with a nonzero code. Do not continue deployment work if the backup fails.

The backup is retained under:

~~~text
/home/openclaw/.local/state/bob-baseline/backups/bob-activity-<UTC>-<PID>.sqlite3
~~~

This directory is required to be mode 0700. Each backup file is mode 0600, and the script refuses symlink paths or non-private destination directories. Partial backup/restore files are cleaned up after failure or success.

## Verification procedure

1. Connect to the live database using SQLite mode=ro and query_only.
2. Use sqlite3.Connection.backup() to make a transaction-consistent snapshot, including committed data from SQLite WAL mode as appropriate.
3. Run PRAGMA integrity_check against the snapshot.
4. Restore the snapshot through SQLite's backup API into a **separate** temporary database.
5. Run integrity_check against that restored copy, and compare full schema fingerprints without printing SQL.
6. Publish the checked backup under a unique filename in the private directory. Leave the original database unchanged.

The backup includes private publishing records, posts, replies, challenge information, quotas and settings. **Never upload, paste, publish or git-commit the database backup.** Share only the non-sensitive command status and pass/fail indicators for review. A verified backup on this same machine is not protection against losing that machine; encrypted off-machine backup is a later operating step.

The rehearsal proves the backup can be restored into an isolated SQLite file; it does not yet prove the entire Bob deployment can be rolled back. Full service/code rollback remains a separate milestone.

## Offline tests

~~~bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
~~~

Synthetic tests cover completed backup/restoration, private file and folder modes, symlink refusal, insecure folder refusal, and corrupt databases. GitHub Actions runs these tests without touching Moltbook, the live SQLite file or an operator's Ollama.

## After the backup

Review missing application and Windows startup files, compare hashes with the v0.6 reference and later LAN-origin fixes, and design the sanitized source import. Do not run migrations until the baseline source and backed-up schema are established.
