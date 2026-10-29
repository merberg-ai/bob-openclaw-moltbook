# Bob 💀 — OpenClaw + Moltbook

**A local-first AI agent experiment with autonomous scouting, controlled publishing, and an Activity Manager.** Bob runs in a dedicated WSL2 Linux environment, uses a local Ollama model through OpenClaw, and interacts with Moltbook via host-side workers and a guarded review/publishing queue.

> **Deployment status (operator-reported October 28, 2026):** Bob Activity Manager **v0.7.2 is installed and working** in OpenClawLab. The responsive navigation, Settings/mobile styling, interactive local credential reset, and live-refreshing System Status view have been tested by the operator. The dashboard displays recorded queue states but **granular worker progress and trustworthy retry eligibility are not yet implemented**. The operator separately observed many `canceled` comments and a failure when requesting an original thought; both remain **uninvestigated**, with no established cause. Existing Moltbook publication permissions and SQLite records must be preserved in future work.

## What Bob does today

- Scouts Moltbook discussions, validates source post IDs, and drafts replies.
- Supports manual approval, rejection, and explicit publishing of comments.
- Has an optional, rate-limited **autonomous comment** mode.
- Generates original post drafts and requires separate approval to publish them.
- Tracks publication attempts, Moltbook verification states, and incoming replies.
- Provides a local web Activity Manager with optional authenticated LAN access.
- Runs using OpenClaw, a local Ollama model, a restricted Docker sandbox, systemd services/timers, and Windows/WSL startup recovery.

These features describe the **working host installation**; they have not yet been reproduced from a tagged GitHub release.

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

**Deployment history:** v0.7.1 was deployed using `scripts/deploy_v071_activity_manager.py`; v0.7.2 Settings/password and status were subsequently installed with `scripts/update_v072_dashboard.py`, `scripts/patch_v072_settings_style.py`, and `scripts/patch_v072_live_status.py`. The operator has confirmed the mobile layout and status page work. These are **historical, version-pinned installers**, not a general `git pull`-to-production mechanism. New commits are not installed until a separately authorized update runs. **Next:** consolidate release inventory and make `bobctl update` version-aware, then complete real worker-stage feedback and investigate the deferred canceled-comment/original-draft failures.

**Current implementation (development branch):** [read-only host inventory](docs/BASELINE-INVENTORY.md), [private database backup](docs/BASELINE-BACKUP.md), [source review and guarded import](docs/IMPORT-REVIEWED-SOURCE.md), and [service/startup recovery inventory](docs/SERVICE-RECOVERY-INVENTORY.md), [isolated release rehearsal](docs/RELEASE-REHEARSAL.md), and [sanitized service-template candidates](docs/SERVICE-TEMPLATE-CANDIDATES.md), plus [isolated inert service-graph staging](docs/INERT-SERVICE-STAGING.md) and [systemd parser acceptance](docs/SYSTEMD-PARSER-ACCEPTANCE.md), followed by [isolated mock-process lifecycle acceptance](docs/INERT-LIFECYCLE-ACCEPTANCE.md), and [read-only systemd staging preflight](docs/SYSTEMD-STAGING-PREFLIGHT.md), with a [separately gated transient-service experiment plan](docs/TRANSIENT-SYSTEMD-EXPERIMENT-PLAN.md). These are baseline/development utilities, not a deployable Bob release.

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
