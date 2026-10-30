## R2 shadow2 transport repair (2026-10-30; operator acceptance pending)

**Why:** The owner's live `openclaw agent --json --message-file` diagnostic returned exit 0, `status: ok`, and one valid JSON reply at `result.payloads[0].text`. The installed shadow1 subprocess did **not** request `--json` and treated raw stdout as the five-field decision object, producing `model_invalid_or_unavailable`. This supports a transport mismatch; the exact original raw response was deliberately not saved. Shadow1 correctly made zero Moltbook writes. See issue #58.

**Maintenance release:** `v0.8.0-shadow2` chains **only** from owner-installed `v0.8.0-shadow1`, updates the deterministic Python archive and shadow launcher, does **not** restart Activity Manager, and does not modify the v0.7 Scout, publisher, queues or credentials. The parser requests `--json`, checks the OpenClaw status/result envelope and exactly one text payload, then runs the same strict source-bound decision validator. Error events now use fixed sanitized categories without logging model text, stderr, or credentials.

**Important operator sequence, after reviewed PR and green CI:**
1. The owner already stopped `bob-v08-shadow.timer` during diagnosis. Run `bobctl shadow-deactivate` and type `DEACTIVATE-SHADOW` to remove the **verified shadow1** timer, pointer and immutable archive. Check `bobctl shadow-status` says `inactive`. Stopping the timer is **not** equivalent to deactivation.
2. Only after confirmed inactive: `bobctl update --check` should offer exactly `v0.8.0-shadow2` from installed `v0.8.0-shadow1`. Run `bobctl update` and type `UPDATE` once.
3. `bobctl shadow-status` should show `release: v0.8.0-shadow2`, `installed: inactive`. Run `bobctl shadow-activate`, type `ACTIVATE-SHADOW`, then `bobctl shadow-status`.
4. Run `bobctl shadow-once` exactly once. A valid result is `state: shadow_decision`, with `acted: false`; `no_new_verified_sources` means all known Scout sources were already consumed. If still invalid, inspect **sanitized** reason on Shadow Inbox, do not keep retrying.
5. Shadow1's previously failed selections are **not automatically replayed**. Its private shadow event database is retained intact. Do not clear events, unseal reports, or attempt re-publication to force an acceptance.

**Boundaries:** `bobctl shadow-deactivate` before the upgrade is mandatory: old shadow1 activation state cannot be silently migrated in place. Shadow2 recognizes only a prior **inactive** shadow1 activation journal and explicitly activates its own archive. If any step refuses, STOP, preserve journals, and do not reset Git or reinstall.

---

## R2 v0.8 shadow installation and acceptance (next-channel candidate)

**Prerequisite:** the owner has already installed and accepted `v0.7.8-updater2` on the OMEN. R2 is the separately reviewed `v0.8.0-shadow1` release on the `next` branch. Do **not** run these commands merely because the candidate exists; first confirm its PR/CI and merged manifest, and that the installed registry still reports v0.7.8.

The first R2 upgrade retains v1 flat-file release guards while supplying a deterministic reviewed Python archive. It is **not** the generalized v2 multi-service updater promised for the eventual R3 cutover. To avoid silently changing user timers during an updater transaction, versioned shadow timer activation is a separate, deliberately authorized local operation. This is one **software release**, not a sequence of small package updates.

After code acceptance and explicit operator authorization:

1. `bobctl update --channel next`: type `SWITCH-NEXT`. Changes **source checkout and private channel configuration only**, not production code, database, permissions, or services.
2. `bobctl update`: verify `v0.7.8-updater2 -> v0.8.0-shadow1`, nine reviewed files, authenticated dashboard restart; type `UPDATE`. The updater backs up the existing SQLite queue and can code-rollback the install if health checks fail. Old Scout, original worker, and publisher timers remain unchanged.
3. In the authenticated Activity Manager, visit **Bob v0.8 · Shadow Now** and **Shadow Inbox**. Before activation, the shadow timer may show inactive/unknown and the event list may be empty; that is expected.
4. `bobctl shadow-activate`: type `ACTIVATE-SHADOW`. Validates installed release hashes and separately copies the reviewed archive into `~/.local/share/bob/releases/v0.8.0-shadow1/`; installs and enables only `bob-v08-shadow.timer` as a user systemd timer, with a private activation journal and the exact archive hash pointer. Old timers keep working. `bobctl shadow-status` is read-only; `bobctl shadow-once` requests **one hypothetical decision** from the actual OpenClaw main agent against verified saved Scout data and never publishes.
5. The legacy Gateway has no new authority. For a **private, session-scoped MD1 test**, `bobctl shadow-experience` (type `ASK-BOB`) starts exactly one isolated session of the real OpenClaw main agent, injecting a bounded read-only evidence digest into that single session's prompt. It does **not** edit `MEMORY.md` or `SOUL.md`, affect other normal Gateway sessions, make Moltbook requests or grant tools. Verify Bob distinguishes observed selections, publisher states and unknown public visibility. General persistent context for normal Gateway/CH1 chat is **not implemented in R2** and remains a separately scoped bridge to design later. OpenClaw loads `MEMORY.md` into multiple fresh sessions, so global workspace injection was explicitly rejected.

**Safety gates:** Shadow action output must always say `acted: false`. No v0.8 code has Moltbook write permission or credentials. At least three successful representative saved-source decisions/observations including a scheduled tick should be inspected, with invalid or empty sources correctly skipped. Do not claim a scheduled run from budget eligibility; the Now page uses read-only systemd timer metadata. A server-local shadow decision and an auto-comment from the still-running v0.7 publisher are distinct and must remain so.

**Rollback:** `bobctl shadow-deactivate` (type `DEACTIVATE-SHADOW`) stops the v0.8 timer and deletes only verified R2-owned unit/archive/pointer files. Only then, when necessary, `bobctl update --rollback-to v0.7.8-updater2` (type `ROLLBACK-v0.7.8-updater2`) invokes the updater's exact original-code archive rollback, with post-restart health checks. It deliberately **does not restore an old SQLite backup**, which could discard real publication history. The source checkout/channel remains `next` until independently switched back to `main`. If activation or recovery reports an incident, do not delete journals or forcibly reset the registry: inspect state before another attempt.

R2 does **not** cut over any of v0.7's publisher responsibilities, change Bob's global memory, or enable persistent experience context in normal Gateway chats. New follows, upvotes, comments, replies and original-post automation remain unapproved.

---

## v0.8 R1 updater preparation (candidate, not installed)

**Catch-up correction (October 30):** The operator's read-only installed updater registry reported `v0.7.6-oc41-polish1`, with verified installed hashes, despite the earlier FM4.1 acceptance record. The staged `v0.7.8-updater2` therefore installs the three previously accepted FM4.1 files **and** `bob-release-updater`/`bobctl` in **one** verified release, directly from the observed OC4.1 registry. The Activity Manager **will restart** to activate the Social Memory page. Existing Scout/publisher/Gateway timers, credentials, permissions and Moltbook publishing behavior are not changed. The normal verified private SQLite backup, integrity checks and rollback still apply. This catch-up manifest is specifically for the reported host baseline; other hosts at FM4.1 need a separate compatible release path, not a manually rewritten registry.

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
