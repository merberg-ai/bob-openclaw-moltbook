# Bob update workflow (`bobctl update`)

**Working system:** Bob v0.7.2 on the owner's existing OpenClawLab WSL2 installation. The manifest-driven updater has been bootstrapped and was confirmed to report `up to date`. As of October 29, 2026, the **installed updater still points at the historical `feature/v0.7.1-navigation` checkout**. The canonical `main` migration is prepared in GitHub and awaits the owner's one-time execution.

## Moving the installed updater to `main`

Follow the [one-command, three-test main migration](MAIN-UPDATER-MIGRATION.md). It creates a separate `~/bob-main` checkout, pins and verifies the exact installed updater, and changes the updater's trusted branch, private checkout pointer and release registry. It does not restart Bob or modify the publication database.

After migration, verify:

```text
BOB MAIN MIGRATION: main_channel_installed
BOB UPDATE: up to date (v0.7.2-main-channel)
```

**Do not rerun the original v0.7.2 updater bootstrap** on a working installation. That script is retained as historical release material.

## Regular updates after migration

```bash
bobctl update --check
bobctl update
```

The installed updater verifies the trusted `merberg-ai/bob-openclaw-moltbook` remote, clean `main` checkout and fast-forward-only Git history. It reads `releases/current.json` and compares the manifest `from` release with the last recorded private installed release. Only the exact explicitly listed source files are eligible. Existing installed files must match their saved SHA-256 hashes before being replaced.

`--check` checks for changes without installing application code. Plain `bobctl update` shows the release notes, changed files and whether a dashboard restart is requested; a user must type **UPDATE** to proceed. The updater takes a private verified SQLite backup before a nonempty upgrade, records sealed old code and the installed registry, writes code atomically and checks authenticated dashboard health. It restarts only the Activity Manager when requested by the manifest. Publisher/scout workers are never started or invoked by the updater. On failure it attempts a guarded code rollback and requires manual recovery if interrupted.

**A successful no-op check does not yet validate the first nonempty manifest-driven update.** The next dashboard refinements will provide that controlled acceptance. A direct `git pull` does not update the live installation.

## Writing a future release

Work on a feature branch, review/merge it to `main`, then promote a new manifest with a unique release ID. Example for the first nonempty update:

```json
{
  "format": "bob-updater-v1",
  "release": "v0.7.2-ui1",
  "from": "v0.7.2-main-channel",
  "notes": "Reviewed dashboard usability changes",
  "files": [
    {"name": "bob-activity-manager", "builder": "scripts/build_v072_ui1_candidate.py", "index": 0},
    {"name": "bob_status_view.py", "source": "src/lib/bob/bob_status_view.py"}
  ],
  "restart_manager": true
}
```

Builders must return two bytes objects from `build()`; direct sources must be reviewed Git-tracked files. A nonempty release requires a single focused offline smoke test before proposing `bobctl update` to the owner. Do not reuse release IDs, skip `from` versions, or change live credentials and publication permissions through a dashboard-only update.

## Safety and boundaries

- Existing-host updater: **installed, basic check verified**, first nonempty manifest release pending.
- Clean WSL2/Windows installation from scratch: **not implemented**; see [installation status](INSTALLATION-STATUS.md).
- Existing LAN HTTP Basic authentication is suitable only for a trusted LAN/VPN or properly configured HTTPS proxy.
- Code rollback is not a request to revert later SQLite publishing records. Uncertain Moltbook posts must never be retried automatically.
- Keep the old feature checkout until the owner confirms the `main` transition and the first normal release.

Historical v0.7.1/v0.7.2 patch scripts remain in the repository as provenance and manual recovery references, not the standard upgrade interface.
