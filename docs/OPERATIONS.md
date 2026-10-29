# Bob operator guide (v0.7.2)

**Current state, October 29, 2026:** The owner's OpenClawLab (WSL2) host is running the verified v0.7.2 Activity Manager, working original-thought drafting, observed worker stages and manually prioritized comment publication. The reusable `bobctl update` command was installed and confirmed up to date. **Its one-time move from the historical feature branch to canonical `main` is prepared but still requires host execution.** See [main migration](MAIN-UPDATER-MIGRATION.md).

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
- Migrate the already-installed updater once using [main migration instructions](MAIN-UPDATER-MIGRATION.md). Do not delete the old feature checkout before checking the new channel.
- Subsequent reviewed releases use `bobctl update`, not historical version-specific patch scripts.
- The updater checks stored code hashes, creates and verifies a private SQLite backup before a nonempty release, performs atomic code swaps, and verifies the authenticated dashboard; it attempts code-only rollback on failure. It never invokes the publisher or resets posting records.
- A new-host Windows/WSL/OpenClawLab installer is **not yet available**; do not run the historical pinned upgrade scripts on a clean host. See [installation status](INSTALLATION-STATUS.md).

Do not paste passwords, API tokens, systemd environment files, `~/.config/moltbook/` databases or private report contents into GitHub issues. The web dashboard is not a new security identity: the publisher and dashboard still share an OS user on this host.

## Before starting v0.7.3

Finish the channel migration, collect and implement a small reviewed batch of dashboard tweaks, and use that batch to verify the **first nonempty manifest-driven update**. The v0.7.3 observations and opinion-learning features are not yet shipped and must remain distinct from authority to publish.
