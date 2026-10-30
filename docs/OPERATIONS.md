## v0.8 R1 updater preparation (candidate, not installed)

The pending `v0.7.8-updater2` release upgrades only `bob-release-updater` and `bobctl` from the operator-accepted `v0.7.7-fm41-social1`. It does **not** restart the Activity Manager, change services or timers, install new workers, grant new publishing permissions or modify Moltbook content. Its existing updater transaction still performs a verified private SQLite backup and authenticated dashboard health check before writing code.

Once this release has passed CI, merged to `main`, and the operator elects to install it, use the existing **single** `bobctl update` confirmation. The updater's current two-field `updater.json` remains valid and defaults to `main`. The first `next` branch is created only after the R1 release is operator-accepted.

**Later, when instructed for the R2 shadow release:** `bobctl update --channel next` requires the exact `SWITCH-NEXT` confirmation. This command changes only the trusted clean source checkout and private updater channel configuration; it does **not** deploy a release. `bobctl update --channel main` reverses the selection. A normal `bobctl update` remains a separate, explicitly approved installation.

R1 recognizes `bob-updater-v2` manifests only in the currently supported flat-file compatibility shape. Versioned package deployment, migrations and managed service transitions belong to R2 and require their own tested updater implementation. Do **not** interpret R1 format recognition as permission to execute arbitrary v2 fields.

See [v0.8 roadmap](ROADMAP-v0.8.md). No user command is required solely because this documentation landed.

---

# Bob operator guide (v0.7.2)

**Current state, October 29, 2026:** The owner's OpenClawLab (WSL2) host is running the verified v0.7.2 Activity Manager, working original-thought drafting, observed worker stages and manually prioritized comment publication. The reusable `bobctl update` command was installed and confirmed up to date. **The operator reports its one-time migration to canonical `main` completed successfully.** See [main migration](MAIN-UPDATER-MIGRATION.md).

## Routine operator commands

Run from the `openclaw` account inside OpenClawLab:

| Command | Effect |
| --- | --- |
| `bobctl status` | Service overview and publication-state counts |
| `bobctl doctor` | Read-only Docker, local Ollama, Gateway and Activity Manager readiness |
| `bobctl publisher-status` | Read-only publisher state counts and timer status |
| `bobctl publisher-logs` | Recent user-systemd publisher logs |
| `bobctl update --check` | Fast-forward the trusted Git checkout and report pending release, **no application deployment** |
| `bobctl update` | Show an available reviewed release and request typed `UPDATE` before any live code update |
| `bobctl update --recover` | Recover an **interrupted** updater transaction only, with explicit approval |

`bobctl publisher-run` is **not a diagnostic command**: it invokes the publisher and might attempt a real Moltbook comment when eligible. Use it only after explicitly deciding to publish.

The Activity Manager normally runs on `127.0.0.1:18790`, with the operator-configured trusted-LAN binding for other devices. Keep its HTTP Basic login on a trusted LAN/VPN, or terminate HTTPS at a properly configured reverse proxy; do not expose unencrypted credentials publicly.

## Publication and queue safety

Comment attempts are rate limited to **two per UTC day** and at least **one hour apart**, shared by manual and eligible automatic comments. In late October 2026, the owner confirmed these limits, four public comments visible to a read-only audit, a successful original-thought draft, and live manual-first queue ordering. When the daily cap is exhausted, additional jobs stay queued until the next permitted window. `cancelled` automatic comments were canceled while queued during prior auto-posting toggles; they are not proof of failed network submissions.

`scripts/diagnose_comment_queue.py` in the GitHub checkout reports paused/auto mode, queue breakdown and the current rate limiter without database writes or Moltbook calls. `scripts/audit_comment_visibility.py` performs a bounded public listing check and never retries a possible duplicate. An API challenge acknowledgment without a confirmed comment ID is **not** labeled publicly visible; verification uncertainty does not authorize a repost.

Original thoughts remain draft-first and require separate human review before publication. Optional autonomous comment permission does not authorize original posts or conversation follow-ups.

## Releases, recovery and backups

- `main` is the canonical reviewed source branch, and [`releases/current.json`](../releases/current.json) is the release manifest.
- The installed updater now tracks canonical `main` following the operator-confirmed migration. The [historical migration procedure](MAIN-UPDATER-MIGRATION.md) must not be rerun; keep the old feature checkout available for reference.
- Subsequent reviewed releases use `bobctl update`, not historical version-specific patch scripts.
- The updater checks stored code hashes, creates and verifies a private SQLite backup before a nonempty release, performs atomic code swaps, and verifies the authenticated dashboard; it attempts code-only rollback on failure. It never invokes the publisher or resets posting records.
- A new-host Windows/WSL/OpenClawLab installer is **not yet available**; do not run the historical pinned upgrade scripts on a clean host. See [installation status](INSTALLATION-STATUS.md).

Do not paste passwords, API tokens, systemd environment files, `~/.config/moltbook/` databases or private report contents into GitHub issues. The web dashboard is not a new security identity: the publisher and dashboard still share an OS user on this host.

## Before starting v0.7.3

The canonical `main` migration and first nonempty manifest-driven updates have been operator-verified. The next merged dashboard release, `v0.7.2-compact1`, shortens Scout/Activity pages while retaining the full legacy views; host installation is pending. The v0.7.3 observations and opinion-learning features are not yet shipped and must remain distinct from authority to publish.
