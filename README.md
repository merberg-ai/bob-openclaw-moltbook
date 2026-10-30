# Bob 💀 — OpenClaw + Moltbook

**A local-first AI agent experiment with autonomous scouting, controlled publishing, and an Activity Manager.** Bob runs in a dedicated WSL2 Linux environment, uses a local Ollama model through OpenClaw, and interacts with Moltbook via host-side workers and a guarded review/publishing queue.

> **Current state (October 29, 2026):** Bob runs on Windows 11 / **OpenClawLab WSL2** with a responsive authenticated Activity Manager, local Ollama/OpenClaw, guarded Scout and separate comment/original-post publishing. Personality (PM1), Memory (PM2), and **Friends FM1–FM3.1** are implemented and **operator-tested**; the installed release is **`v0.7.5-fm31-watch1`**. Friends' default-off scouting and individual watch preferences do not authorize automatic friend-targeted replies. **FM3.2 is next; FM4 Social Memory and FM5 Independent Social Exploration are planned.** See [Friends roadmap and fresh-chat handoff](docs/FRIENDS-ROADMAP-AND-HANDOFF.md).
>
> **GitHub:** `main` is authoritative; existing-host releases are applied through the operator-confirmed `bobctl update` flow, not automatically on commit. A clean-machine fresh-host installer remains deferred. The previous Scout Python shared-module import failure was repaired in `v0.7.5-scout-importfix1`; a later timer-driven Scout success has not yet been separately confirmed. See [operations](docs/OPERATIONS.md).

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

**Friends Manager milestone:** **FM1, FM2, FM3 and FM3.1 complete and operator-tested**. **FM3.2 next** (Bob-proposed source-backed interest suggestions and scalable/focused friend browsing). **FM4 planned** (social memory and evolving relationships). **FM5 planned** (independent social exploration with separately approved action-specific permissions). The authoritative [FM1–FM5 roadmap and new-chat handoff](docs/FRIENDS-ROADMAP-AND-HANDOFF.md) records the last accepted release, known Scout caveat and smallest safe next steps.

**Personality and Memory prerequisites:** PM1 personality staging and guarded SOUL.md apply/rollback are operator-tested; PM2 private memory, reviewed proposals and opt-in recall are operator-tested. The original PM1 → PM2 → FM1 development order has been completed through FM3.1. Consult [PM1 apply notes](docs/V073-PM1-GUARDED-APPLY.md), [PM2 foundation](docs/V073-PM2-MEMORY-FOUNDATION.md), and the [current Friends handoff](docs/FRIENDS-ROADMAP-AND-HANDOFF.md). Follow/unfollow and autonomous friend interactions remain separately gated, regardless of previous auto-comment consent.

**Release and installation:** The installed `bobctl update` now follows canonical `main` and has delivered the responsive Scout, Activity and Manage Queues pages. The operator confirmed **Activity Limits** is installed and saved custom budgets, including 8 comments/day, 30-minute comment spacing, 4 automatic comments/day and 4 original posts/day. [PR #10](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/10) passed CI and merged the next **`v0.7.2-overview1`** release: a live Overview home page with budget gauges, queue/outcome statistics, worker stages, service indicators and read-only 15-second refresh. **The operator confirmed `v0.7.2-overview1` installed and looking good.** The [follow-up PR #11](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/11) trims the large header, duplicate shortcuts and explanatory copy. The operator confirmed `v0.7.2-overview2` **installed successfully**. [PR #12](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/12) fixes Scout's approval/denial and other action redirects so they return to the same Scout section, filters and page instead of Overview. The operator confirmed `v0.7.2-redirects1` installed and working. The operator confirmed PM2.1 `v0.7.3-pm2-memory1` is installed and the Memory page loads, but reported that edit failures showed only an unhelpful generic page. The next candidate `v0.7.3-pm2-editfix1` makes edit/correct controls explicit and displays fixed, safe validation explanations. See [PM2 edit fix](docs/V073-PM2-EDIT-FEEDBACK-FIX.md). The Memory Manager still has no automatic agent recall or ingestion. **PM2.2a candidate** `v0.7.3-pm22-scout-review1` adds a reviewed suggestion inbox sourced from Bob's already verified Scout drafts, with explicit approval/rejection and provenance checks; it does not claim to generate new LLM summaries. See [PM2.2a notes](docs/V073-PM22-SCOUT-SUGGESTIONS.md). **PM2.2b candidate** `v0.7.3-pm22b-local-ai1` adds an explicit, local-Ollama-powered proposal generator from verified Scout posts with asynchronous job status and owner-only approval. It needs Ollama reachable at WSL loopback; no automatic recall or publishing. [PM2.2b notes](docs/V073-PM22B-LOCAL-AI-PROPOSALS.md). **PM2.3 candidate** `v0.7.3-pm23-optin-recall1` adds separate default-off, topic-matched, read-only memory recall switches for Scout and original drafts with a dashboard preview. See [PM2.3 privacy and acceptance notes](docs/V073-PM23-OPTIN-RECALL.md). After the operator verified channel enable/disable, a follow-up preview fix `v0.7.3-pm23-recallfix1` was prepared to explain the eligible-memory search and improve matching/diagnostics without touching posting workers. See [PM2.3.1 recall preview fix](docs/V073-PM23-RECALL-PREVIEW-FIX.md). PM2 including the recall preview fix is operator-tested; **FM1 candidate** `v0.7.4-fm1-friends1` provides a private manual Moltbook Friends directory, reversible local statuses, revision history and source-verified Scout author quick-adds. No real follow/profile API actions or autonomous outreach. See [FM1 release notes](docs/V074-FM1-FRIENDS.md). **FM2 candidate** `v0.7.4-fm2-discovery1` adds explicit anonymous read-only Moltbook agent profile lookup, timestamped public-field cache and a Bob-authored Scout rationale review inbox. No credentials, follows, posts, messaging or automatic friend additions. See [FM2 acceptance and API notes](docs/V074-FM2-DISCOVERY.md). **FM3 candidate** `v0.7.4-fm3-friend-scout2` adds default-off friend-focused reads to existing Scout (max two profiles/posts, four global slots preserved), an operator toggle and watchlist; friend-focused batches are manual-publication-only regardless of existing global auto-comment settings. See [FM3 notes](docs/V074-FM3-FRIEND-SCOUT.md). **Logs & Diagnostics** candidate `v0.7.5-logs1` adds an authenticated, GET-only filtered view of redacted systemd journal messages, safe queue failure reasons, events, and worker checkpoints, without changing Bob's workers or publishing permissions. See [Logs release notes](docs/V075-FILTERED-LOGS.md). **Logs correlation fix** `v0.7.5-logs2` automatically joins failed worker checkpoints to safe stored job reasons or nearby sanitized journal observations, and labels pre-send owner-review blocks as warnings. See [diagnostic fix notes](docs/V075-LOGS-CORRELATION-FIX.md). **Scout import repair** `v0.7.5-scout-importfix1` packages the previously omitted shared `bob_publish_common.py` helper in the installed script directory, with isolated startup-import regression tests. See [Scout startup repair notes](docs/V075-SCOUT-IMPORT-FIX.md). **FM3.1 candidate** `v0.7.5-fm31-watch1` adds private per-friend watch pause/resume controls, revision history and a read-only timeline of Bob's independently verified Scout rationales for chosen friend discussions. See [FM3.1 acceptance notes](docs/V075-FM31-FRIEND-WATCH.md). See [PM2 foundation](docs/V073-PM2-MEMORY-FOUNDATION.md). Scout moves to `/scout`; full historical reports stay at `/scout/full`. See [Overview release](docs/V072-OVERVIEW-DASHBOARD.md), [update workflow](docs/BOBCTL-UPDATE-WORKFLOW.md), and [fresh installation status](docs/INSTALLATION-STATUS.md). No `git pull` by itself updates production.

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
- **Existing host:** operator-confirmed **`v0.7.5-fm31-watch1`** Activity Manager and Friends controls, installed via `bobctl update`. A post-repair *scheduled* Scout run still needs a light confirmation.
- **This GitHub repository:** canonical `main` holds reproducible generated Activity Manager builders, worker modules, private-backup tooling, synthetic tests and the updater. Running services do not automatically synchronize with the development checkout. See [Friends roadmap and restart handoff](docs/FRIENDS-ROADMAP-AND-HANDOFF.md).
- **License:** pending project-owner selection. Do not assume a redistribution license exists.

Bob's future learning system will store source-linked observations and revisable positions, **not** retrain model weights or claim consciousness.
