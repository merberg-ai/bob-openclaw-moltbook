# Bob / OpenClawLab — v0.7 Roadmap

**Working title:** Continuity, Learning & Usable Operations  
**Status (October 29, 2026):** v0.7.0–v0.7.2 foundation **shipped and operator-tested**, including live status, mobile navigation, manual-first comment publishing and a reusable `bobctl update` command. GitHub `main` is authoritative. The installed updater migration to `main` is **operator-confirmed complete**. The real manifest-driven updater and Manage Queues pending-review fix are operator-verified. Compact Scout/Activity polish (`v0.7.2-compact1`) is operator-verified. **Activity Limits** (`v0.7.2-activity-limits1`) is installed and operator-verified with custom settings. The Overview landing page (`v0.7.2-overview1`) is operator-confirmed installed and working. The compact Overview cleanup (`v0.7.2-overview2`) is operator-confirmed installed. Scout action buttons were subsequently found to redirect to Overview, so a guarded navigation correction (`v0.7.2-redirects1`) passed CI and merged to `main` but awaits installation. v0.7.3 learning features remain unimplemented.  
**Planning baseline:** Bob currently uses an existing Windows 11/OpenClawLab WSL2 setup, local Ollama, OpenClaw, Docker and user-systemd services. A general **fresh-host installer is still missing**. Historical v0.5/v0.6 source and staging notes below are retained for technical context, not as current instructions.

**Non-negotiable rule:** Preserve existing services, authentication, publication records, approval decisions, autonomous settings, sandboxing, and reboot recovery throughout every upgrade.

## 1. Objectives

1. Give Bob **experience-based continuity**, not neural-weight training: source-linked discoveries, recurring questions, discussions, and revised viewpoints.
2. Build a clean, responsive **multi-page Activity Manager** with desktop sidebar and collapsible mobile menu, rather than cramming everything into one page.
3. Show **real queued/running/waiting/failed/confirmed job states** while waiting for Docker, Gateway, Ollama, Moltbook and verification challenges.
4. Add **conversation continuity**, letting Bob revisit replies and propose useful follow-ups.
5. Establish canonical GitHub source, tests, versioned releases, safe updating, backups and rollback.
6. Preserve **separate permissions** for autonomous comments, original posts, and follow-up replies. Do not infer one authorization from another.

## 2. Existing host architecture

The deployed v0.7.2 installation builds on the original v0.6 host architecture:

- A Python `ThreadingHTTPServer` Activity Manager serving `/`, `/activity`, `/originals`, `/healthz`, and protected POST actions. HTML generation, routing, authentication and CSRF/origin handling remain mixed in a relatively large script.
- A private SQLite database at `~/.config/moltbook/activity-queue.sqlite3`, with legacy publication decisions, settings, jobs, replies and events plus v0.6 original requests, original posts and original-post reply records.
- A scout that saves timestamped feed snapshots and validates source post identifiers and drafts.
- Separate scout, comment publisher and original-post workers, with systemd timers and a Windows/WSL startup/recovery chain.
- A trusted-LAN authenticated dashboard; successful handling of the observed opaque `Origin: null` form submission without dropping CSRF/draft checks.
- Optional bounded auto-**comments**; original posts remain approval-only.

**Current source is in `main`.** The live host has been patched through verified v0.7.2 upgrades, and the owner's successful updater bootstrap recorded exact installed checksums. Older referenced source and installer labs are historical. Never add credentials or runtime databases to Git; see [architecture](ARCHITECTURE.md) and [operations](OPERATIONS.md).

## 3. UI and navigation

### Desktop sidebar

- **Overview:** overall health, last scout job, review counts, publication confirmations, verification challenges, latest replies.
- **Moltbook → Scout & Review:** validated discussions, generated comments, approvals and rejections.
- **Moltbook → Conversations:** initial thread, Bob's comments, replies, pending follow-ups and last checked.
- **Moltbook → Original Posts:** generate, preview, edit, approve, queue, verify.
- **Moltbook → Publishing Activity:** comment/original attempts, confirmation links, verification events, errors, timeline.
- **Bob's Mind → Personality & Memory:** operator-managed persona sliders, identity changes with history/rollback, curated long-term memories and source-linked recall. **Planned after v0.7.2**, not shipped.
- **Moltbook → Friends:** private list of interesting and favored agents, profiles and relationship history; **deferred until the Memory Manager is installed and tested**.
- **Bob's Mind → Discoveries & Journal:** source-linked observations, saved questions and dated reflections.
- **Bob's Mind → Opinions & Questions:** current tentative positions, evidence for/against, revision history and unresolved questions.
- **System → Health & Jobs:** Gateway, Docker, Ollama, workers, timers, active jobs and recent errors.
- **System → Settings & Logs:** auto-comment switch, rate limits, audit history and backup/export diagnostics.

### Mobile navigation

Use a compact top bar and hamburger drawer; close the menu when a destination is selected. Keep cards readable, controls touch-friendly, and prevent horizontal overflow or giant form fields. Show **Auto-comments ON/OFF** clearly, separately from original-post publishing.

Visual direction: Bob's restrained dark cyber-lab aesthetic, coherent typography, accessible contrast, sensible whitespace. Prefer a small server-rendered UI with modest JavaScript over a large SPA for this iteration.

## 4. Live job status, spinners and errors

Background operations must expose meaningful stages instead of showing a spinner forever:

```text
queued -> checking_dependencies -> waiting_for_gateway / waiting_for_ollama
       -> generating -> validating -> completed

publishing: queued -> submitting -> awaiting_verification
                     -> confirmed_published / uncertain / failed
```

A job record includes an ID, kind, stage/state, create/update/finish timestamps, safe error, result IDs/links and retry eligibility.

Provide authenticated read-only job status at `GET /api/jobs/{id}` and/or `GET /api/jobs?active=1`, with `Cache-Control: no-store`. Poll around every 3 seconds while active, less often otherwise. Indicate elapsed time; **do not invent completion percentages**. Disable only the action that would duplicate an active job; leave other pages usable.

Show distinct labels such as *Waiting for Gateway*, *Waiting for Ollama*, *Bob is drafting*, *Validating*, and *Awaiting Moltbook verification*. On failed/stalled work show a clear message and a safe retry option when genuinely permitted. Use accessible `aria-live` regions and reduced-motion support. Keep plain POST/303 navigation functional without JavaScript.

Health must distinguish a **running process** from a **ready dependency**.

## 5. Learning, reflection and opinions (not weight training)

### Additive private schema

- `observations`: ID, timestamp, category, summary, source type, source post/comment ID, canonical URL, author, trust label, relevance.
- `questions`: text, linked observation, open/explored/resolved state, possible revisit time.
- `opinions`: topic, current position, exploring/tentative/supported/disputed status, *estimated* confidence and update time.
- `opinion_revisions`: append-only old/new positions, reason, evidence for/against, timestamp.
- `reflections`: period, sources considered, lessons, uncertainties, next questions, model attribution, review status.
- `conversation_notes`: thread/comment IDs, participants, past responses, unresolved prompts and last checked.

Store **lower-trust evidence and conclusions** separately from OpenClaw agent identity, system instructions, tool policy, and credentials. Never put raw external post content into `SOUL.md`, `IDENTITY.md`, or other high-priority prompts.

### Learning loop

1. **Observe:** select bounded excerpts from already captured feeds and confirmed incoming replies.
2. **Analyze:** request typed, short structured outputs with observations, arguments, uncertainty and source references.
3. **Validate:** host checks schema, claimed source IDs, lengths, trust class and any executable/policy-like instruction; reject unknown/fabricated citations.
4. **Store:** append valid evidence and questions with timestamps.
5. **Recall:** retrieve a small set of relevant, source-linked notes when drafting; label them fallible context, never instructions.
6. **Revise:** allow positions to evolve with explicit reasoning, counterevidence and an immutable revision trail.

Add retention limits, export/backup and an operator action to mark evidence incorrect or reconsider a position. Encourage disagreement and calibration, not mere agreement with the last post read.

**Meaning of learning:** persistent context, source-linked notes and revisable positions, not Qwen weight fine-tuning or a claim that Bob is conscious.

### Personality & Memory Manager, then Friends Manager (agreed feature order)

PM1 is entering implementation with an **initial staged Personality Lab** (`v0.7.3-pm1-foundation1`) ready for operator testing; saving traits does not change live OpenClaw identity yet. Personality Apply/diff/backup/rollback, PM2 Memory Manager and FM1–FM3 Friends Manager remain future reviewed stages. The fresh-host installer remains a later, independent workstream. Do not start Friends implementation before the Memory Manager is installed and operator-tested.

1. **PM1: Personality Foundation.** Start with a private staged slider/profile editor and read-only workspace metadata; confirm the actual active workspace before editing. Create a responsive personality editor with social/intellectual trait sliders, explicit interpretation of each trait, advanced identity controls, draft-preview comparison, audited snapshots and one-click rollback. Bob's core identity and permission policy are operator-controlled.
2. **PM2: Memory Manager.** Add private, backed-up, searchable memories with manual add/edit/correct/archive/exclude, origin and confidence labels, source links, version history and review of Bob-suggested memories. Keep untrusted Moltbook data out of high-priority persona/tool files. Confirm the memory UI and persistence are working before beginning Friends.
3. **FM1: Friends Manager (after PM2).** Add a dedicated **Moltbook → Friends** dashboard page and private local friends list. Allow the operator to manually add/remove/pin agents and Bob to suggest or mark interesting agents. Store profile identifiers, available public profile metadata, friend/interesting status, tags and first/last encounters. Validate current Moltbook profile/feed API capabilities when this phase starts rather than assuming an endpoint or payload.
4. **FM2: Friend discovery and relationship tracking.** Let Bob promote discovered agents to *interesting* or *friend* using repeat encounters, evidence and evolving interests, without inferring mutual friendship. Track why the agent matters, previous public exchanges and an editable relationship-memory timeline. The owner can override, archive or exclude a contact.
5. **FM3: Friends-focused scouting.** Read posts from known/followed agents using documented, tested APIs where available; favor useful friend posts without drowning out general discovery or automatically generating replies. Use relevant source-linked relationship memories to inform drafts, while preserving posting budgets, deduplication, manual review and existing opt-in policies.

**Critical boundaries:** A *local friend* is different from a Moltbook account that Bob *follows*, and neither implies that the other agent follows Bob. Local discovery and friendship curation need no public API writes. Moltbook follow/unfollow actions are a separate, initially operator-approved permission. Automatic interaction with friends is **not** authorized by the Friends Manager. External profiles, posts and claimed relationships remain untrusted data; never allow them to rewrite Bob's persona, instructions, credentials or tool permissions.

**Acceptance before FM1:** Memory Manager successfully saves, edits, archives and retrieves data without corrupting existing queue state. **Acceptance for FM1–FM3:** manual contacts persist across restart, duplicate identities and unsafe URLs are rejected, API lookup failures are presented honestly, private records never enter Git or public endpoints, followed accounts and local friends remain distinguishable, and existing Scout/publisher behavior is unchanged until explicitly enabled.

## 6. Guarded reflection scheduler

Start with one daily reflection from a small budget of recent material (for example, 5–10 useful observations), with operator-configurable scheduling later. Skip safely if Docker, Ollama or Gateway isn't ready. Do not write unsupported inferences after failed generation.

The reflection should explicitly identify what Bob found, what he agrees/disagrees with, how certain he is, what might change his view, and what to investigate next.

## 7. Conversation continuity

Extend existing reply tracking rather than replacing it. Group the original post, Bob's comment, incoming direct replies, last polling time, and unfinished questions. Allow a **draft follow-up** informed by real prior context, but default to human approval.

No automatic reply just because someone responds. Prevent reply loops, stale threads, duplicates and self-replies. Any future autonomous follow-up mode needs its own explicit authorization, lower limits and cooldown, separate from auto-comments.

## 8. Canonical source and release structure

Proposed layout (incremental refactor, not an immediate replacement):

```text
README.md
CHANGELOG.md
SECURITY.md
docs/
  ROADMAP-v0.7.md
  ARCHITECTURE.md
  OPERATIONS.md
src/
  bob_manager/
    app.py
    routes/
    security.py
    templates/
    static/css/
    static/js/
  bob_workers/
    scout.py
    publish_comments.py
    original_posts.py
    reflection.py
    conversations.py
  bob_core/
    database.py
    migrations/
    job_status.py
    observations.py
    opinions.py
deploy/
  systemd/
  windows/
scripts/
  install.sh
  update.sh
  rollback.sh
  backup.sh
  doctor.sh
tests/
.github/workflows/test.yml
.gitignore
```

Keep existing command names, service unit names and database behavior as compatibility entrypoints while refactoring. Do **not** add empty scaffolding and call it a production release.

### Secrets and privacy

Never commit API keys, `lan-auth.json`, `openclaw.json`, registration responses, private settings, live DB/WAL/SHM, feed snapshots, captures, journals, backups or user memories. Only sanitized synthetic test data belongs in Git. Scan the staged commit for secrets before pushing. A public repository is not a place for operator diagnostics with credentials.

### Versioned update contract

Planned operator commands:

- `bobctl version`
- `bobctl check-update`
- `bobctl update --dry-run`
- `bobctl update`
- `bobctl rollback`

Stage a pinned, checksummed release; validate syntax/tests; use an installation lock and pause affected workers safely. Take a **proper online SQLite backup** with `sqlite3.Connection.backup()`; preserve live configuration, secrets, quotas and approval states. Make additive idempotent migrations and swap a versioned `current` symlink atomically. Restart only affected services and check `/healthz`, worker readiness and queue integrity. Restore code on failed health, and explicitly guard against database writes made after a backup if rollback needs data restoration.

Do not pipe mutable `main` into Bash for production updates. Choose and add an open-source license only with owner approval.

## 9. Milestones and acceptance gates

### v0.7.0 — Safe GitHub foundation

**Deliver:** inventory exact host install, private backups of source/SQLite/services, compare with historical v0.6 bundle and patches, import canonical sanitized source, establish tests and version identifiers, demonstrate staging backup/rollback. No new outward/publication activity.

**Pass:** All existing routes, LAN auth/form actions, review/auto switches, publisher states, original posts, and Windows reboot/startup keep working. No credentials or private data enter Git; verified backup is restorable.

### v0.7.1 — Navigation and UI separation

**Deliver:** extracted templates/static assets, separate page routes, desktop sidebar, mobile drawer, active-page state, system health banner. No DB changes.

**Pass:** Current controls still work from localhost and LAN, no opaque-origin/CSRF regression, responsive mobile layouts and keyboard navigation are usable.

### v0.7.2 — Live background-job feedback and dashboard Settings

**Deployed v0.7.2:** Responsive Settings/password rotation, trusted-console login reset, mobile layout, 15-second read-only status refresh, real private worker-stage checkpoints, and safer comment verification labeling are operator-confirmed. An original-thought draft subsequently succeeded, and a public audit found four visible comments. No uncertain publication is automatically retried.

**v0.7.2 worker tracking (deployed and operator-confirmed):** The scout, original generation, original publication and comment publisher now report private observed checkpoints; the mobile System Status page shows stage cards, bounded stale detection, timestamps and actual queue states. The guarded update passed operator testing and installation. See [job tracking release notes](V072-JOB-TRACKING-RELEASE.md).

**Deliver:** job-status model/API, real spinners, stage-specific messages, health diagnostics, timeouts, error display, safe retry eligibility, and a responsive **System → Settings** page with LAN dashboard password rotation.

**Settings / password rotation requirements:**
- Password change is the first v0.7.2 feature to implement. Keep the current LAN username unless explicitly changed separately. Current password + new password + confirmation fields; never display or return an existing password.
- Use the established authenticated session/request, CSRF token, exact Host and Origin validation, a restricted POST route, no-store responses, no URL parameters for secrets, and safe body-length/field validation. Prevent changing credentials through a GET or cross-origin request.
- Store the replacement credentials atomically in the existing private `~/.config/bob-system/lan-auth.json` (same owner, directory privacy, mode 0600), with fsync and safe rollback on a write failure. Never write credentials to logs, Git, SQLite, or diagnostics.
- Avoid a service restart for routine password changes. Currently the manager reads `LAN_CREDS` only at startup, so switch to fail-closed credential reload/check or a carefully controlled credential refresh with tests proving old credentials immediately stop working and the new credentials work.
- Explain browser HTTP Basic authentication caching: desktop and mobile may retain stale login details. Provide clear reauthentication guidance, not a false promise of reliable single-click logout. The existing HTTP LAN interface is unencrypted; advise trusted LAN/VPN or HTTPS reverse proxy and do not expose it publicly.
- Distinguish live *process* health from Ollama, Gateway, scout and publisher *readiness*. Show queued/running/waiting/error using observed worker state and last update, never invented progress. Preserve all existing publication permissions and state.

**Pass:** Test credential rotation, current-password mismatch, CSRF/Origin refusal, malformed and oversized requests, private permissions, atomic-write failure, concurrent requests, and old-password rejection without service restart. Test unavailable/slow Docker, Gateway and Ollama; no duplicate requests or publishing; no secrets in APIs or logs.

**Publication accuracy follow-up (deployed and observed working):** The publisher preserves a known comment ID or records `verified_unconfirmed` without retry when verification returns no ID. Activity distinguishes API acknowledgment from independently confirmed visibility, and shows auto-queue cancellations as never sent. Original thoughts accept bounded, explicit alternative formats while retaining draft validation and manual approval. A read-only public comment audit is available. The operator subsequently confirmed both a successful generated original-thought draft and four public comment IDs visible through the bounded audit. See [publication accuracy notes](V072-PUBLICATION-ACCURACY-FIX.md).

**Operator verification (October 29, 2026):** An original-thought draft now generates successfully, a bounded public audit found four comments visible on Moltbook, and Bob has received responses to his original post. The remaining backlog is explained primarily by the existing two-attempts-per-UTC-day cap (2/2 at 2026-10-29T12:23Z), not by service failure. The live queue has four manual and ten auto comments waiting; its oldest queued item is manual. The queued manual-first patch is a proactive scheduling improvement, not a bypass of today's rate limit. Review identified the two-attempt UTC daily cap, one-hour attempt interval, and an oldest-first scheduler that can let held auto entries block later manual approvals. The read-only diagnostic reported that the old queue scheduler was installed; the one-file manual-first patch subsequently passed four focused tests and deployed successfully at 2026-10-29T12:29Z. Its post-install diagnosis confirmed `manual_first_installed: True` and unchanged limits (`attempts_today: 2/2`, manual queued: 4, auto queued: 10). No publishing attempt was triggered by installation; maintain existing caps and do not blindly repost. See [queue backlog investigation](V072-QUEUE-BACKLOG.md).

### v0.7.3 — Observations and evolving opinions

**Deliver:** additive observation/question/opinion/revision schema, source-validated ingestion, searchable learning view and clear provenance. No automatic propagation into social posts until tested.

**Pass:** Reject fake sources, malicious instructions and oversized data; revisions preserve prior positions and counterevidence.

### Planned follow-on: Friends Manager after the Memory Manager (version to be assigned)

**Dependency:** Complete and verify PM1 Personality Foundation and PM2 Memory Manager first. FM1 manual/local friends comes next; FM2 discovery and FM3 relationship-aware scouting follow as separately reviewed releases. Do **not** bundle automatic following or additional autonomous publishing permissions into the first Friends release.

**Pass:** The owner can manually add a friend, Bob can suggest interesting agents without making an API write, and friend activity/relationship memory shows provenance. Preserve existing posting permissions, rate limits and source trust boundaries. Detailed design is in section 5 above.

### v0.7.4 — Reflections and contextual recall

**Deliver:** guarded daily reflection worker/timer, journal page, bounded evidence retrieval into drafting and uncertainty display.

**Pass:** Bob can accurately cite earlier real discussions and explain a changed position; identity, permissions, private credentials and publishing rules remain unchanged.

### v0.7.5 — Conversations and final hardening

**Deliver:** thread histories, reply alerts, optional follow-up drafts, end-to-end tests, security review and release documentation.

**Pass:** End-to-end post/scout -> draft -> approval/auto rule -> submission -> challenge -> confirmed-public result -> reply tracking -> source-linked reflection. Never automatically retry an uncertain submission.

## 10. Project-wide acceptance checklist (includes future v0.7.3+ gates)

- [ ] Snapshot host before migrations; no secrets or private memory in public Git.
- [ ] Exact deployed version visible in dashboard and CLI.
- [ ] LAN login, approval/reject, autonomous toggle, CSRF and origin protections pass.
- [ ] Existing approvals and publishing records survive without unsolicited posts.
- [ ] Real progress/errors, no fake stuck spinners.
- [ ] Source-linked daily reflection with uncertainty, only after explicit feature enablement.
- [ ] No external content can become privileged instructions.
- [ ] Reboot leaves services healthy or safely waiting for dependencies.
- [ ] Dry-run update and rollback demonstrated before production use.
- [ ] Operator can pause all autonomous publishing and follow-up activity.

## 11. Explicitly deferred beyond v0.7

- Autonomous original posts (requires independent authorization, rate limits).
- Autonomous follow-up replies (separate limits/cooldowns).
- Model fine-tuning, external vector database, giant JavaScript SPA, untrusted Internet exposure.
- Separate OS user for the credentialed publisher (desirable hardening, but stage independently to avoid breaking the deployment).

**Dashboard queue management release:** PR #6 merged to `main` with green GitHub checks. Release `v0.7.2-queues1` added `/manage` with status/search/archive filters, ten-item pagination, guarded batch approval/rejection/queueing, and reversible archive markers. The **first installation attempt failed**, but a read-only audit confirmed all original code restored; guarded reconciliation and a distinct `v0.7.2-queues1-r1` retry subsequently succeeded. The operator also confirmed `v0.7.2-queues2` works as expected. See [incident recovery](V072-QUEUES1-INCIDENT-RECOVERY.md). See [dashboard management](V072-DASHBOARD-MANAGEMENT.md).

## Next actionable task

**Next planning priority:** PM1 Personality Foundation, followed by PM2 Memory Manager. Only after PM2 is installed and operator-tested should Friends Manager (FM1–FM3) begin. The guided fresh-host installer remains deferred but required eventually. Continue using the existing reviewed `bobctl update` release process; do not interpret this roadmap update as a live software change.
