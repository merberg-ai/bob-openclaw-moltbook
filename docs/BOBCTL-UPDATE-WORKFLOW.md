# Bob's reusable updater: `bobctl update`

**Status:** Committed to GitHub for one-time installation. The owner-reported live baseline is v0.7.2, including manual-first publishing. The installed `bobctl` does **not** yet know `update`; the one-time bootstrap below adds it. No changes are deployed by a GitHub commit.

## One-time installation

Run in Windows PowerShell using the ordinary `openclaw` WSL user:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "set -e; cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/bob_release_updater.py scripts/bootstrap_bob_updater.py src/bin/bobctl && python3 -m unittest discover -s tests -p 'test_bob_updater_smoke.py' -q && python3 scripts/bootstrap_bob_updater.py --apply --confirm INSTALL-BOB-UPDATER && ~/.local/bin/bobctl update --check"
```

This is **one focused five-test acceptance**, not the entire project suite. The bootstrap refuses unexpected installed files, checks the currently running authenticated dashboard, creates a new verified SQLite backup, registers the exact current installed code and replaces only `~/.local/bin/bobctl` plus the new `~/.local/bin/bob-release-updater`. It does **not** restart any service, publish, change auto-posting, or touch SQLite data. It writes a private configuration record pointing to the current clean GitHub checkout and a private hash registry. The installer refuses an existing deployment or partially written journal. If it reports `REFUSED`, stop rather than rerunning.

The expected final output is:

```
BOB UPDATER BOOTSTRAP: installed
BOB UPDATE: up to date (v0.7.2-updater-bootstrap)
```

## Ongoing workflow

After the one-time bootstrap, use **one command** from the OpenClawLab terminal:

```bash
bobctl update
```

That command verifies a clean checkout on the expected `feature/v0.7.1-navigation` branch with the expected GitHub origin, fast-forwards it from GitHub, reads `releases/current.json`, and checks its declared `from` release against a private installed-release registry. It checks SHA-256 hashes of every registered installed file. When no release is pending, it says **up to date** and changes no production files. When a new release is pending, it prints the release description, exact files to replace and whether Activity Manager will restart, then asks the operator to type **UPDATE**. Without that exact confirmation, no production code is installed.

For a read-only check without the interactive installation prompt:

```bash
bobctl update --check
```

**An ordinary `git pull` never deploys a new version.** The updater won't copy arbitrary files because it only accepts an explicit `releases/current.json` release manifest, local script or builder paths in the reviewed repository, a matching previous release, and expected file hashes.

For a declared update, the engine creates and restore-verifies a private SQLite backup before changing any application files, archives original code privately, uses owner-private atomic writes, and performs authenticated dashboard health probes. It restarts **only** `bob-activity-manager.service` when a release manifest explicitly requests that restart. It never starts a worker or triggers a Moltbook POST. It checks updated files and the dashboard before recording completion. An interrupted transaction requires manual `bobctl update --recover`, exact confirmation, and unchanged sealed archive data; it must not be retried blindly.

## Creating future releases on GitHub

Future dashboard/UI changes get one reviewed manifest change rather than a new installer. Example:

```json
{
  "format": "bob-updater-v1",
  "release": "v0.7.3-ui1",
  "from": "v0.7.2-updater-bootstrap",
  "notes": "Mobile dashboard layout improvements",
  "files": [
    {"name": "bob-activity-manager", "builder": "scripts/build_v073_dashboard_candidate.py", "index": 0},
    {"name": "navigation_shell.py", "builder": "scripts/build_v073_dashboard_candidate.py", "index": 1}
  ],
  "restart_manager": true
}
```

Builder scripts must have a `build()` function returning `(manager_bytes, navigation_bytes)`. Direct tracked modules can instead use e.g. `{"name":"bob_status_view.py","source":"src/lib/bob/bob_status_view.py"}`. The updater installs **only** manifest files and rejects unexpected paths, duplicate targets, uncommitted files, a changed repository remote, installed-source drift and out-of-sequence releases.

Release IDs are immutable. Do not reuse a completed ID for a different manifest. This first release intentionally contains no pending changes. The next dashboard changes can use the first actual manifest-driven update.

## Important boundaries

This is still a local GitHub-to-Bob updater, **not** an internet-accessible self-update HTTP endpoint. Only the trusted local `openclaw` shell can authorize production installation. The repo's GitHub branch remains historically named `feature/v0.7.1-navigation` until deliberately migrated; this updater pins that branch rather than silently switching it. The existing LAN dashboard is HTTP and should remain restricted to a trusted LAN/VPN until HTTPS is enabled.

The updater doesn't change passwords, Moltbook credentials, publishing limits, database schema, job approvals, or existing historical records.
