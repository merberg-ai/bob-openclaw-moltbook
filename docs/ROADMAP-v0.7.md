# Bob / OpenClawLab — v0.7 Roadmap

**Working title:** Continuity, Learning & Usable Operations  
**Status:** Approved roadmap; v0.7.0 reviewed-source import, private baseline, startup/service inventory and isolated release simulation are in progress on draft feature branch  
**Planning baseline:** Working v0.6 Activity Manager + later LAN-origin hotfixes, v0.5 publishing, v0.4 reboot/startup recovery and v0.3 `bobctl` health checks. **Nine exact installed source files were SHA-verified and imported to the v0.7.0 development branch; full service templates and production release/rollback remain pending.**

**Non-negotiable rule:** Preserve existing services, authentication, publication records, approval decisions, autonomous settings, sandboxing, and reboot recovery throughout every upgrade.

## 1. Objectives

1. Give Bob **experience-based continuity**, not neural-weight training: source-linked discoveries, recurring questions, discussions, and revised viewpoints.
2. Build a clean, responsive **multi-page Activity Manager** with desktop sidebar and collapsible mobile menu, rather than cramming everything into one page.
3. Show **real queued/running/waiting/failed/confirmed job states** while waiting for Docker, Gateway, Ollama, Moltbook and verification challenges.
4. Add **conversation continuity**, letting Bob revisit replies and propose useful follow-ups.
5. Establish canonical GitHub source, tests, versioned releases, safe updating, backups and rollback.
6. Preserve **separate permissions** for autonomous comments, original posts, and follow-up replies. Do not infer one authorization from another.

## 2. Current reference architecture

The previously built v0.6 bundle describes:

- A Python `ThreadingHTTPServer` Activity Manager serving `/`, `/activity`, `/originals`, `/healthz`, and protected POST actions. HTML generation, routing, authentication and CSRF/origin handling remain mixed in a relatively large script.
- A private SQLite database at `~/.config/moltbook/activity-queue.sqlite3`, with legacy publication decisions, settings, jobs, replies and events plus v0.6 original requests, original posts and original-post reply records.
- A scout that saves timestamped feed snapshots and validates source post identifiers and drafts.
- Separate scout, comment publisher and original-post workers, with systemd timers and a Windows/WSL startup/recovery chain.
- A trusted-LAN authenticated dashboard; successful handling of the observed opaque `Origin: null` form submission without dropping CSRF/draft checks.
- Optional bounded auto-**comments**; original posts remain approval-only.

**Reference source is not the same as current deployed source.** The user's OMEN installation received later patches. Before code import, capture installed hashes, service unit definitions, schema, script versions and exact configuration boundaries privately. Do not copy credentials or state into a public repository.

## 3. UI and navigation

### Desktop sidebar

- **Overview:** overall health, last scout job, review counts, publication confirmations, verification challenges, latest replies.
- **Moltbook → Scout & Review:** validated discussions, generated comments, approvals and rejections.
- **Moltbook → Conversations:** initial thread, Bob's comments, replies, pending follow-ups and last checked.
- **Moltbook → Original Posts:** generate, preview, edit, approve, queue, verify.
- **Moltbook → Publishing Activity:** comment/original attempts, confirmation links, verification events, errors, timeline.
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

**Deployed progress (operator-reported October 28, 2026):** Responsive Settings, immediate password rotation, trusted-console login reset, mobile styling, 15-second read-only service/queue status refresh, and observed worker-stage checkpoints are running in production. Checkpoints are bounded and become unknown when stale; they do not infer progress from service state. Publication-accuracy and original-output-format corrections have also deployed successfully. The original-thought generation outcome still needs a real-world recheck, and historical comment visibility is unknown until independently audited. No automatic reposting or retry of uncertain publications was introduced.

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

**Publication accuracy follow-up (deployed successfully; runtime verification pending):** The publisher preserves a known comment ID or records `verified_unconfirmed` without retry when verification returns no ID. Activity distinguishes API acknowledgment from independently confirmed visibility, and shows auto-queue cancellations as never sent. Original thoughts accept bounded, explicit alternative formats while retaining draft validation and manual approval. A read-only public comment audit is available. The operator reports the updater succeeded; actual Moltbook visibility and a fresh original-thought draft still need validation. See [publication accuracy notes](V072-PUBLICATION-ACCURACY-FIX.md).

**Operator verification (October 29, 2026):** An original-thought draft now generates successfully, a bounded public audit found four comments visible on Moltbook, and Bob has received responses to his original post. The unresolved issue is a queue backlog dominated by queued manual/auto comments. Review identified the two-attempt UTC daily cap, one-hour attempt interval, and an oldest-first scheduler that can let held auto entries block later manual approvals. A read-only live diagnosis command and a manual-first scheduling correction are committed but **not deployed**; maintain rate limits and avoid blind reposting. See [queue backlog investigation](V072-QUEUE-BACKLOG.md).

### v0.7.3 — Observations and evolving opinions

**Deliver:** additive observation/question/opinion/revision schema, source-validated ingestion, searchable learning view and clear provenance. No automatic propagation into social posts until tested.

**Pass:** Reject fake sources, malicious instructions and oversized data; revisions preserve prior positions and counterevidence.

### v0.7.4 — Reflections and contextual recall

**Deliver:** guarded daily reflection worker/timer, journal page, bounded evidence retrieval into drafting and uncertainty display.

**Pass:** Bob can accurately cite earlier real discussions and explain a changed position; identity, permissions, private credentials and publishing rules remain unchanged.

### v0.7.5 — Conversations and final hardening

**Deliver:** thread histories, reply alerts, optional follow-up drafts, end-to-end tests, security review and release documentation.

**Pass:** End-to-end post/scout -> draft -> approval/auto rule -> submission -> challenge -> confirmed-public result -> reply tracking -> source-linked reflection. Never automatically retry an uncertain submission.

## 10. Project-wide acceptance checklist

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

## Next actionable task

**Start v0.7.0:** collect a safe, exact baseline from the *live* OMEN OpenClawLab installation, compare it with our reference source, scrub secrets, add tested source and CI to Git, then demonstrate upgrade/rollback on staging **before** any production code changes.
