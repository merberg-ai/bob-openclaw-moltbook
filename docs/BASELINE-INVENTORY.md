# v0.7.0: First live-host inventory

**Status:** Phase 1, inventory only. No backups, installers, source imports, migrations, or deployments are performed by this command.

The original reference bundle may differ from what is actually running in OpenClawLab. Capture the real installed scripts and metadata before adopting any source as canonical.

## One-time capture from OpenClawLab

Run in the **OpenClawLab WSL2 Linux distro as user `openclaw`**, not as root. This is a new checkout; it does not modify the existing installation.

```bash
git clone --depth 1 --branch feature/v0.7.0-host-inventory \
  https://github.com/merberg-ai/bob-openclaw-moltbook.git \
  ~/bob-v070-inventory
python3 ~/bob-v070-inventory/scripts/inventory_live_host.py
```

The script uses only the Python standard library, and does not call Moltbook, Ollama, OpenClaw or Docker. It performs optional **read-only** `systemctl show` calls but never starts/stops a unit. It checks a fixed set of installed-executable directories, known user/system systemd directories and the activity SQLite database path.

The output is a timestamped, mode-`0600` JSON file in mode-`0700` directory:

```text
~/.local/state/bob-baseline/inventory-<UTC>-<PID>.json
```

Only file hashes, sizes, modes and modification times are collected. Service file content (including `Environment=` lines), script source, credentials, private SQLite rows, original-post text, feed snapshots and logs are **not** included. Database *schema metadata* (object names, column names/types, `user_version`) is read using SQLite `mode=ro`; there is no DB backup yet.

**Keep the inventory out of GitHub, issues, public pastebins, and repositories.** It contains local filesystem paths and structural details, and should remain private. Upload it privately for review if desired.

If scripts live in an unusual directory, add `--include-code-dir /specific/directory`. This is a nonrecursive scan of executable-looking `bob*` and `moltbook-*` file names, not a search of all personal files. If the SQLite database moved, use `--database /path/to/activity-queue.sqlite3`.

If `systemctl` is unavailable, `--skip-unit-states` skips service state probes; file hashes and schema are still collected.

## On the Windows host

WSL cannot reliably inventory Windows startup tasks, scheduled tasks or the Windows launcher just by reading its Linux filesystem. Record their executable file paths and SHA-256 hashes separately, without exporting launcher contents or secrets. This is intentionally a separate acceptance step.

## Safety review before the next phase

1. Confirm the report contains the expected live executables, timers and service units.
2. Identify missing installed code paths without collecting private state.
3. Confirm the SQLite schema was read (or investigate a missing/relocated DB).
4. Compare live file hashes with the v0.6 reference and later LAN-origin patch.
5. **Only then** design a private SQLite online backup and test its restoration, before any modification of host code.
6. Import *sanitized source* plus offline tests on a development branch, not private report files.

## Offline test

```bash
python3 -m unittest discover -s tests -p 'test_inventory_*.py' -v
```

Tests use a temporary synthetic SQLite database, fake service unit files and fake scripts, and do not contact external services.
