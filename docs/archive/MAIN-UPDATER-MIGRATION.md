# Canonical `main` updater migration

**Status (October 29, 2026):** The owner reports the one-time migration **succeeded**. The installed updater now tracks canonical `main`; this document preserves the one-time procedure for historical/recovery reference. Do **not** rerun it on an already migrated installation.

## Historical one-time migration procedure (already completed on the owner host)

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc 'set -e; test -d "$HOME/bob-main" || git clone --branch main --single-branch https://github.com/merberg-ai/bob-openclaw-moltbook.git "$HOME/bob-main"; cd "$HOME/bob-main"; git pull --ff-only; python3 -m py_compile scripts/bob_release_updater.py scripts/migrate_bob_updater_to_main.py; python3 -m unittest discover -s tests -p "test_main_updater_migration.py" -q; python3 scripts/migrate_bob_updater_to_main.py --apply --confirm MIGRATE-BOB-UPDATER-TO-MAIN; "$HOME/.local/bin/bobctl" update --check'
```

This procedure performed **three focused offline tests** first. On success the migration should print:

```text
BOB MAIN MIGRATION: main_channel_installed
BOB UPDATE: up to date (v0.7.2-main-channel)
```

If either reports `REFUSED`, stop and inspect the result rather than repeating the operation. An interrupted migration can be recovered separately using `python3 ~/bob-main/scripts/migrate_bob_updater_to_main.py --recover --confirm RECOVER-BOB-UPDATER-MIGRATION` after reviewing its private transaction journal. This command is not for a successful migration.

## What changes

The migration validates both the existing installed feature-branch updater and a clean **main** GitHub checkout. It verifies the installed updater bytes and the entire private installed-file registry. The new updater binary differs by exactly **one branch constant**: `feature/v0.7.1-navigation` becomes `main`. It updates:

- `~/.local/bin/bob-release-updater` (trusted branch)
- `~/.config/bob-system/updater.json` (checkout becomes `~/bob-main`)
- `~/.local/state/bob-updater/installed.json` (release ID becomes `v0.7.2-main-channel` and updater file checksum)

It privately saves previous bytes and journals the operation. It validates authenticated dashboard health before and after the update. **No service restarts, publisher runs, database migrations, password changes, or new Moltbook posts occur.** The existing `~/bob-v071-preview` checkout remains untouched and available for inspection.

Afterward:

```bash
bobctl update --check
bobctl update
```

Both commands pull from the verified `main` checkout. `--check` never installs application code. The normal command requires typed `UPDATE` when a future nonempty release manifest exists, and refuses unrecognized installed file hashes.

This transition **does not** establish that a fresh-host installer exists, nor does it exercise the updater's first nonempty dashboard release. The former will be a separate milestone; the latter will be exercised by the forthcoming dashboard refinements.

## Repository policies

`main` is the source of truth for future reviewed releases. Don't delete the feature branch or remove the old checkout until the owner has observed the new up-to-date result and verified at least one ordinary release. Historical v0.7.1/v0.7.2 pinned patch scripts are archived for recovery, not the recommended update workflow.
