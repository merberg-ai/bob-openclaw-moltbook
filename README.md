# Bob 💀 — OpenClaw + Moltbook

**A local-first AI agent experiment with autonomous scouting, controlled publishing, and an Activity Manager.** Bob runs in a dedicated WSL2 Linux environment, uses a local Ollama model through OpenClaw, and interacts with Moltbook via host-side workers and a guarded review/publishing queue.

> **Current state (October 29, 2026):** Bob **v0.7.2 is deployed and operator-tested** on Windows 11 / OpenClawLab (WSL2). The Activity Manager has responsive desktop/mobile navigation, secured Settings and credential reset, live health/worker stages, read-only activity reporting, and manual-first queued comment publishing. A real original-thought draft succeeded and a public read-only audit found **four visible comments** on Moltbook. Automatic comments still require a separate opt-in and have a configurable attempt cap, while original posts require explicit human approval. The operator has installed Activity Limits and selected custom budgets; uncertain publication results are never blindly retried.
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

These features describe the operator-tested installation. The existing-host manifest-driven updater has now completed multiple real releases, including the queue-management fixes; a clean-machine installer remains unbuilt.

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

**Next development order (planned, not installed):** PM1 **Personality Foundation** (traits/sliders and versioned identity editing) → PM2 **Memory Manager** (private, searchable memories with manual edits and review) → FM1–FM3 **Friends Manager** (manually added and Bob-discovered Moltbook agents, public profile lookup, relationship memories, and friend-focused scouting). Friends work begins **only after PM2 is installed and verified**. Follow/unfollow API actions and automatic interaction remain separately authorized. The fresh-host installer is deferred, not abandoned.

**Release and installation:** The installed `bobctl update` now follows canonical `main` and has delivered the responsive Scout, Activity and Manage Queues pages. The operator confirmed **Activity Limits** is installed and saved custom budgets, including 8 comments/day, 30-minute comment spacing, 4 automatic comments/day and 4 original posts/day. [PR #10](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/10) passed CI and merged the next **`v0.7.2-overview1`** release: a live Overview home page with budget gauges, queue/outcome statistics, worker stages, service indicators and read-only 15-second refresh. **The operator confirmed `v0.7.2-overview1` installed and looking good.** The [follow-up PR #11](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/11) trims the large header, duplicate shortcuts and explanatory copy. The operator confirmed `v0.7.2-overview2` **installed successfully**. [PR #12](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/12) fixes Scout's approval/denial and other action redirects so they return to the same Scout section, filters and page instead of Overview. The new `v0.7.2-redirects1` release is available through `bobctl update` but **not yet installed**. Scout moves to `/scout`; full historical reports stay at `/scout/full`. See [Overview release](docs/V072-OVERVIEW-DASHBOARD.md), [update workflow](docs/BOBCTL-UPDATE-WORKFLOW.md), and [fresh installation status](docs/INSTALLATION-STATUS.md). No `git pull` by itself updates production.

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
