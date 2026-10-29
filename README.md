# Bob 💀 — OpenClaw + Moltbook

**A local-first AI agent experiment with autonomous scouting, controlled publishing, and an Activity Manager.** Bob runs in a dedicated WSL2 Linux environment, uses a local Ollama model through OpenClaw, and interacts with Moltbook via host-side workers and a guarded review/publishing queue.

> **Current state (October 29, 2026):** Bob **v0.7.2 is deployed and operator-tested** on Windows 11 / OpenClawLab (WSL2). The Activity Manager has responsive desktop/mobile navigation, secured Settings and credential reset, live health/worker stages, read-only activity reporting, and manual-first queued comment publishing. A real original-thought draft succeeded and a public read-only audit found **four visible comments** on Moltbook. Existing auto-comment approvals and the two-attempt UTC daily limit remain enforced; uncertain comment submissions are never silently retried.
>
> **GitHub:** `main` contains the deployed v0.7.2 sources and updater foundation. The operator successfully installed `bobctl update` and verified its initial status. The operator reports the **one-time updater migration to `main` succeeded**; future reviewed releases will be pulled from the canonical `main` checkout. See [migration instructions](docs/MAIN-UPDATER-MIGRATION.md). A full **fresh-host installer does not yet exist**.

## What Bob does today

- Scouts Moltbook discussions, validates source post IDs, and drafts replies.
- Supports manual approval, rejection, and explicit publishing of comments.
- Has an optional, rate-limited **autonomous comment** mode.
- Generates original post drafts and requires separate approval to publish them.
- Tracks publication attempts, Moltbook verification states, and incoming replies.
- Provides a local web Activity Manager with optional authenticated LAN access.
- Runs using OpenClaw, a local Ollama model, a restricted Docker sandbox, systemd services/timers, and Windows/WSL startup recovery.

These features describe the operator-tested installation. The existing-host upgrade path is working; a clean-machine installation and the first nonempty manifest-driven update are still unverified.

## v0.7 roadmap — Continuity, Learning & Usable Operations

| Milestone | Goal |
| --- | --- |
| **v0.7.0** | Live-host baseline, source import, tests, backup/update/rollback |
| **v0.7.1** | Responsive multi-page UI, desktop sidebar, mobile navigation |
| **v0.7.2** | Real background-job progress, loading states, health and errors |
| **v0.7.3** | Evidence-linked observations, questions, opinions, revision history |
| **v0.7.4** | Guarded daily reflections and relevant contextual recall |
| **v0.7.5** | Conversation continuity, reply tracking, end-to-end hardening |

See the **[full v0.7 roadmap](docs/ROADMAP-v0.7.md)**.

**Release and installation:** The working installation evolved through guarded v0.7.1 and v0.7.2 upgrades; the latest manual-first publisher change passed four focused tests and was installed without altering rate limits. The operator has also bootstrapped `bobctl update` successfully. **The trusted updater checkout is now `main` (operator-confirmed migration)**; future dashboard releases can use the manifest-driven updater. See [updating Bob](docs/BOBCTL-UPDATE-WORKFLOW.md), [main migration](docs/MAIN-UPDATER-MIGRATION.md), and [fresh installation status](docs/INSTALLATION-STATUS.md). **Next dashboard release:** [PR #6](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/6) merged a new mobile-friendly Manage Queues view with filters, ten-item pagination, bulk review/queue and reversible archive. The first dashboard update attempt failed, but its archive was preserved and the guarded reconciliation succeeded. The operator's screenshots now confirm **Manage Queues is installed**. A follow-up bug was found: automatically queued scout comments falsely replaced Pending review status in the new filter. [PR #7](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/7) fixes the two-state display as one-module release `v0.7.2-queues2`; **the fix is not yet confirmed installed**. No `git pull` alone modifies production code.

**Reviewed development and deployment artifacts:** [read-only host inventory](docs/BASELINE-INVENTORY.md), [private database backup](docs/BASELINE-BACKUP.md), [source review and guarded import](docs/IMPORT-REVIEWED-SOURCE.md), and [service/startup recovery inventory](docs/SERVICE-RECOVERY-INVENTORY.md), [isolated release rehearsal](docs/RELEASE-REHEARSAL.md), and [sanitized service-template candidates](docs/SERVICE-TEMPLATE-CANDIDATES.md), plus [isolated inert service-graph staging](docs/INERT-SERVICE-STAGING.md) and [systemd parser acceptance](docs/SYSTEMD-PARSER-ACCEPTANCE.md), followed by [isolated mock-process lifecycle acceptance](docs/INERT-LIFECYCLE-ACCEPTANCE.md), and [read-only systemd staging preflight](docs/SYSTEMD-STAGING-PREFLIGHT.md), with a [separately gated transient-service experiment plan](docs/TRANSIENT-SYSTEMD-EXPERIMENT-PLAN.md). These are baseline/development utilities, not a deployable Bob release.

## High-level architecture

```text
Moltbook public feed -> host scout -> sandboxed OpenClaw Bob -> validated draft
                                                                |
                                       human review or eligible auto-comment rule
                                                                |
                                    credentialed host-side publisher -> Moltbook
                                                                |
                                       private SQLite queue -> Activity Manager

Windows sign-in -> OpenClawLab (WSL2) -> systemd -> Gateway / scout / publishers / UI
Windows Ollama (local model) ---------------------------------------------^
```

Moltbook content and model responses are **untrusted data** and must never become instructions for the host. Bob's sandbox does not hold the Moltbook API key. Publisher and web processes may currently share the same Linux user, so their process separation is *not* an OS-level security boundary. HTTP Basic over LAN has no encryption; it should not be exposed to untrusted networks.

For more, see [Architecture](docs/ARCHITECTURE.md), [Security](SECURITY.md) and [Operations](docs/OPERATIONS.md).

## Development principles

1. **Do not break the live host.** Capture its actual hashes, code, service units, schema, and startup configuration before importing any reference snapshot.
2. **No secrets or private runtime data in Git.** Never commit API keys, dashboard passwords, personal memory, live SQLite databases or WAL files, feeds, reports, logs, or backups.
3. **Use synthetic offline tests.** CI must not publish to Moltbook or contact an operator's Ollama.
4. **No surprise side effects.** A checkout/install/update must not silently publish, change auto-mode, reset quotas, or modify security permissions.
5. **Versioned reversible releases.** Future updates should pin a release/checksum, take a proper online SQLite backup, test, deploy atomically, health-check, and support rollback.

## Project status

- **Agreed plan:** v0.7 roadmap, now tracked in this repository.
- **Existing host:** v0.6 Activity Manager with later LAN-origin fix and earlier service-management components; live exact revision still needs verification.
- **This GitHub repository:** holds the pinned original manager, v0.7.1 deployed candidate builder, v0.7.2 feature builder, private-backup tooling and guarded update scripts. Running services do not automatically synchronize with the development checkout.
- **License:** pending project-owner selection. Do not assume a redistribution license exists.

Bob's future learning system will store source-linked observations and revisable positions, **not** retrain model weights or claim consciousness.
