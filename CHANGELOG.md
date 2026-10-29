# Changelog

## v0.7.3 pm1-foundation1 — Staged Personality Lab (installation pending)

- Adds **Bob's Mind → Personality** with eight 0–100 sliders and real-time non-LLM text interpretation.
- Authenticated CSRF-protected profile save and revision/restore history in private SQLite, separate from publishing permissions.
- Read-only default workspace `SOUL.md` / `IDENTITY.md` file metadata inventory. No identity file writes, live agent changes, Ollama calls, public Moltbook activity or extra worker processes.
- Synthetic regression suite covers validation, revision integrity, safe workspace file checks and original protected action methods. [PM1 release notes](docs/V073-PM1-PERSONALITY-FOUNDATION.md).
- One normal `bobctl update` followed by a browser check; actual Apply to Bob and safe identity diff/backup/rollback are planned for the next PM1 stage.


## v0.7.2 redirects1 — Section-preserving action navigation (operator-verified)

- [PR #12](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/12) passed offline CI and merged to `main`. The operator reported Scout Approve/Reject returning to the new Overview.
- Corrected Scout Approve/Reject/Reset, Queue, Verify, and Auto-enable/disable redirects to the same Scout filter/page and full-history context. Added strict local return-target allowlisting and section-aware error-page links.
- Audited other actions: Originals, Manage Queues and Activity Limits already return to their sections; password rotation deliberately returns a reauthentication message.
- Three-file Activity Manager release, no posting worker, authorization, limits or database changes. Operator confirmed installation and correct section navigation.

## v0.7.2 overview2 — Compact Overview cleanup (operator-verified)

- Removed the redundant Mission Control hero, duplicate section-navigation buttons, and long helper paragraphs. Kept daily budget gauges, local rate-slot timestamps, queue and publication data, service/worker cards and live refresh.
- Removed unused styles and JavaScript references to the deleted header to preserve automatic refresh.
- [PR #11](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/11) passed offline CI and merged to `main`. One-file `bob_overview.py` update from `v0.7.2-overview1`; operator confirmed it installed successfully and looks good.

## v0.7.2 overview1 — Live overview landing page (operator-verified)

- [PR #10](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/10) passed offline CI and merged to `main`. The operator confirmed the release installed successfully and the new Overview was looking good.
- Changed `/` from Scout to **Overview**, and moved compact review to `/scout`, retaining `/scout/full` and all original review/publish controls.
- Added responsive daily budget gauges, queued/manual/automatic and original-post counts, recorded publication outcomes, observed incoming replies, live service and worker cards, recent events, and rate-slot estimates.
- Spinners appear only for recently observed active worker stages, not queued/idle/stale workers. Refreshes every 15 seconds through a guarded read-only endpoint and respects reduced motion.
- No changes to workers, Activity Limits, publishing permission, database schema, or sensitive POST routes.

## v0.7.2 activity-limits1 — Settings and worker budgets (operator-verified)

- Split Settings into overview, Users & Access (preserving login/password rotation), and Activity Limits.
- Added validated configurable UTC comment attempts, minimum comment spacing, independent auto-comment sub-budget, original-post attempts and original-post spacing, enforced directly in each worker.
- Recommended 6/45/3/2/120 limits require explicit `APPLY LIMITS` save; installing code preserves conservative previous limits by default. Posting permissions, publisher timers, and no-automatic-retry protections remain unchanged.
- Reviewed through [PR #9](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/9) with green offline CI; the owner confirmed installation and saved custom limits (8 total comments/day, 30-minute comment spacing, 4 automatic/day and 4 originals/day).

## v0.7.2 compact1 — Compact Scout & Activity (operator-verified)

- Default Scout & Review and Published Activity views redesigned into eight-item pages, collapsible content, searches, state/visibility filters and category tabs to reduce mobile scrolling.
- Legacy unabridged pages preserved under `/scout/full` and `/activity/full`; Manage Queues full-report links updated.
- Existing approval, reset, publish queue, verification and autonomous-comment POST handlers preserved unchanged; GitHub offline suite passed and PR #8 merged to `main`.
- Release included three application files and the Activity Manager restart. The operator confirmed the updated UI works as expected.

## v0.7.2 queues2 — Pending review status fix (operator-verified)

- Operator screenshots confirm the queue management page is now installed following successful guarded incident reconciliation and retry of `v0.7.2-queues1-r1`.
- A review-pending Scout draft with an automatically queued comment was incorrectly labeled only `queued`, disappearing from the Pending filter.
- Keep review decision and publication state independent; show both badges, count archived pending separately, allow legitimate review, and refuse duplicate publication queue jobs. Original-post `draft` records also match Pending.
- Fix is a single-module replacement (`bob_dashboard_manage.py`) with Activity Manager restart only; it does not change publication records or archive flags.

## v0.7.2 queues1 — Deployed after guarded retry

- Added an authenticated, mobile-friendly **Manage queues** screen with Scout, Original Posts and Comment Activity tabs, server-side search/status/visibility filters, ten-item pages, compact previews and batch selection.
- Implemented bounded bulk approve/reject and explicitly confirmed **queue for publication** actions, preserving all publishing safeguards and prohibiting direct publication from the UI.
- Implemented reversible archive/restore flags without deleting source or publication records. Archiving a queued item does **not** cancel its future publication.
- Passed GitHub's offline acceptance and merged [PR #6](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/6). The initial `v0.7.2-queues1` deployment **failed**; the operator's read-only audit confirmed the previous manager and navigation restored and the new module absent. The original incident archive remains preserved. A guarded reconciliation, improved updater readiness check and new `v0.7.2-queues1-r1` release are prepared but not yet installed.

## v0.7.2 — Deployed (operator confirmed October 29, 2026)

- Responsive desktop/mobile multi-page Activity Manager, secure Settings password change and trusted-console login reset.
- Live 15-second System Status with real worker checkpoints, stale/unknown handling, bounded error summaries and authenticated API.
- Scout, comment publisher, original generation and original publication stages reflected without fake percent progress.
- Original-thought drafts accept strictly structured variants of title/body output while preserving content validation and human approval.
- Comment-verification responses without confirmed IDs remain `verified_unconfirmed`; public visibility is not inferred from an API success response. Added a bounded read-only public comment audit.
- Manual comment approvals take queue priority over automatically generated comments. Existing **two attempts per UTC day**, one-hour minimum spacing, and no-automatic-retry safeguards remain unchanged.
- The operator verified a successful original-thought draft, four Moltbook-visible published comments, and a clean four-test manual-first publisher update.

## v0.7.2 — Update infrastructure

- Implemented `bobctl update` and a verified one-time bootstrap for the existing host. The operator installed the bootstrap successfully and observed an up-to-date status.
- Merged the working v0.7.2 development branch to `main` via [PR #5](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/5).
- The operator reports the guarded updater migration from `feature/v0.7.1-navigation` to canonical `main` completed successfully. The old checkout remains available for reference.
- Established the no-op `v0.7.2-main-channel` release manifest. The first nonempty manifest-driven update will be the forthcoming dashboard-polish release.

## v0.7.0–v0.7.1 — Historical foundation

- Imported and reviewed sanitized host source with private inventory and verified SQLite backup tools.
- Implemented guided responsive navigation, release rehearsals, version-pinned production upgrades, health probes and code-only rollback workflows.
- Preserved Moltbook credentials, approval records, publication history and original-post consent boundaries outside GitHub.

## Not yet implemented

- A supported clean-host installer for Windows/WSL/OpenClawLab.
- v0.7.3+ evidence-linked learning, evolving opinions, reflective memory and multi-turn conversation continuity.

See [operator guide](docs/OPERATIONS.md), [main-channel migration](docs/MAIN-UPDATER-MIGRATION.md), and [installation status](docs/INSTALLATION-STATUS.md).
