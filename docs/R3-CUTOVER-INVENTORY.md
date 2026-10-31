## R3.10 source-only atomic publisher claim and crash/revocation tests

**New:** `src/bob_v08/r310_atomic_claim_lab.py`, `tests/test_r310_atomic_claim.py`, and offline CI trigger. The code accepts only a preverified `UnifiedLab` with a private marked `r3-unified-fixtures/r3-unified-lab.sqlite3`; it uses its fixed sibling `scout` and `paused` paths, not caller-specified source/permission roots. The inherited R3.9 GET and clock are **test-owned callbacks**, never agent-supplied authority.

The R3.9 read-only, two-pass local/source/owner/friend/queue review must first return `reviewed`. The R3.10 claim then acquires `BEGIN IMMEDIATE` and rechecks exact source and independent Bob text seal, stored R3/legacy auto flags and opt-in age, manual owner approval, manual-first queue ordering, current legacy activity limit policy, protected friends, existing attempted/uncertain targets, and paused marker. The single guarded SQL CAS marks the exact legacy-shaped job `sending_simulated` with `attempted_at`; the matching proposal moves to `intent_simulated` and an audit event is committed **in the same transaction**. SQL audit failure rolls back all of it. A post-commit pause/source change locks the counted attempt as `uncertain` rather than replaying it, without contacting Moltbook. Concurrent threads yield at most one successful claim, and a restart sees the already-attempted job as ineligible.

**Production caveats:** No publisher credentials/API POST or installed v0.7 publisher entrypoint uses this module. No new owner option or R3 auto permission is enabled in the live service. The R3.10 positive result is **not a dispatch token** and always says `dispatch_authorized=False`. Fresh HTTPS and filesystem evidence can change between SQLite commit and a real POST, so the future integrated publisher must revalidate immediately before its existing credentialed send, lock uncertain outcomes, and prevent dual dispatchers. R3.11 remains the versioned, disabled-by-default adapter/inert entrypoint rehearsal; **real owner cutover approval is still absent**.

---

## R3.9 independent Bob-draft publisher review, still not enabled for live sends

`src/bob_v08/r39_publisher_review.py` adds a **read-only** publisher-side contract using the already reviewed R3.4 saved-source validator, R3.6 Bob-origin classifier and real v0.7 activity-limit evaluator. It requires the **new Bob seal/proposal** to match the existing unattempted queued legacy job, current separate stored owner R3 opt-in/dial (or matching Bob-specific manual approval), safe source age, friend protection, no attempted/uncertain target collision, manual-first queue order and non-paused state. A fixed-host public HTTPS GET (no API credentials, no redirects, strict UUID target/author/deleted checks) is bracketed by two full local source/policy checks with bounded elapsed time. All tests mock the GET transport; no real network activity occurs.

A positive review **does not authorize dispatch**, claim an intent or update any SQLite row. It explicitly returns `dispatch_authorized=False`, `acted=False`. The actual v0.7 publisher currently only knows Scout-approved text, and this source module is not wired into its live path. The owner has **not** created R3 auto permission or approved an R3 cutover; the existing `auto_enabled=1` remains a v0.7-only control.

**Next R3.10** must integrate an independent Bob-draft schema/owner consent with the **one existing credentialed publisher**, reconcile two-pass GET checks with the atomic pre-POST `attempted_at` CAS, retain no-blind-retry and manual priority, and rehearse an explicit rollback/versioned owner acceptance before any live change. Do not infer a green light from an isolated unit test or from R3.8's healthy effective service shape.

---

## R3.8 real OMEN effective-unit inspection accepted (2026-10-30)

Operator-supplied read-only report from OpenClawLab: publisher service `reviewed_shape`, timer `reviewed_shape`, **0 service overrides**, **0 timer overrides**, **1 environment declaration**, **0 review blockers**, `R3 cutover authorized: NO`. The R3.8 conservative check recognized the expected one-shot command shape and timer target/cadence. Environment values and unit paths were not printed. **Accepted as a narrow installed-effective-unit-shape snapshot only**; it does not attest the executable hash, dispatch behavior, WSL/Windows restart survival, fresh Moltbook GET/friend signals, new owner permissions, or readiness for live R3 cutover. The existing publisher, Shadow4, database and credentials remain unchanged.

---

## R3.8 inert dispatch/receipt and effective publisher unit review (source only)

**Added:** `src/bob_v08/r38_dispatch_lab.py`, `tests/test_r38_dispatch_recovery.py`, `scripts/report_r38_effective_units.py`, `tests/test_r38_effective_units.py` and CI triggers. [R3.8 detailed operator/engineering guide](R38-DISPATCH-RECOVERY.md).

The existing R3.3 marked private fixture is still the **only** transactional ledger. R3.7 trust gates an unattempted Bob-authored draft; the atomic synthetic intent marks one `publish_jobs.attempted_at` before any fake external event. R3.8 provides only a tightly typed `InertSink` that records a SHA of the target/text in memory, with no network imports or credentials. A bounded follow-up barrier rereads current owner dial/auto consent, source/proposal content, friend table and flags, global pause and reduced budgets. All R3.8 **returned outcomes** are explicitly simulated; for compatibility the marked fixture may store legacy-shaped `state='uncertain'` when a previously counted send has become ambiguous, while new fake receipt states use `_simulated` labels. Acknowledgment requires a valid fake UUID; fake challenge requires human intervention; ambiguous results and crashes require manual review. A new worker or process restart cannot retry an already attempted target. `recover_after_restart` handles only synthetic in-flight intents, leaving all original v0.7 `sending`, `uncertain` and verification history unchanged.

A separate read-only `systemctl --user cat` audit evaluates the **effective** legacy publisher service and timer, including ordered drop-in override/resets, unexpected extra processes/restarts and timer association. Only allowlisted safe labels are returned. No unit, database, credential or queue change is possible through this report. **Real OMEN effective-unit acceptance is still pending**; the earlier R3.6 host snapshot established service/timer activity and database schema, not exact ExecStart or drop-in safety.

This **does not** implement any real publisher HTTP transport, trusted live GET/friend attestation, true atomic external pause plus DB transition, versioned installer, new automatic owner permission or service cutover. The cutover flag remains false. R3.9 should reconcile the owner-provided effective unit evidence and then develop an isolated publisher-side extension to the one credentialed writer, with exact source admission and a final pre-POST comparison.

---

## R3.7 offline publisher trust gate, not a credentialed send adapter

**Implemented:** `src/bob_v08/r37_trusted_gate_lab.py`, `tests/test_r37_trusted_gate.py`, and offline CI path. A strict dry-run gate now ties R3.6 exact Bob-origin classification to the existing R3.3 *marked, private synthetic queue*; independently re-verifies saved Scout file integrity, a Bob-authored seal linked to the same post, current queue mode/state, persisted owner dial, separate R3 auto opt-in, legacy `auto_enabled`, post-opt-in source, manual-first queue priority, attempted/uncertain target conflicts, real v0.7 rate-limit reader, and global pause marker. Manual Bob-authored drafts require a distinct owner decision covering their precise new seal.

**Friend check:** the selected author is extracted from the SHA-verified Scout feed, compared against the existing private `bob_friends` table, and source/friend markers are checked conservatively. Missing/corrupt friend data or a friend-targeted batch refuses R3 auto. This is a lab adaptation of the reviewed v0.7 `allow_auto_candidate()`; the live function currently resolves its own source directory and is not a drop-in for new Bob-origin work. No new ability to auto-comment on friends is implied.

**Preflight check:** a test harness provides a callable GET/clock (not model JSON); the gate requires a positive exact post ID, matching author, not-deleted state and a bounded elapsed interval. A second complete source/owner/friend/queue/budget/pause check follows before the synthetic ledger records `sending_simulated` and `attempted_at`. No SQLite write lock is retained while the GET-like callback executes. GET exceptions and unknown fields fail closed, and the result is explicitly `dispatch_authorized=False`. **No real authenticated GET or POST is implemented**, and this cannot establish live Moltbook availability or actual friend identity.

**Production boundaries still missing:** integrate a trusted fixed-host HTTPS client owned by the single credentialed v0.7 publisher, identify safe author field contract against real API responses, bind final pre-POST pause/consent/source snapshot with the publisher's durable CAS, maintain no-blind-retry uncertain recovery, and finish effective installed unit/drain/reboot validation on OMEN. A clean R3.6 host baseline and passing R3.7 tests do **not** approve new Bob posting permissions or live migration.

---

## R3.6 real-host checkpoint accepted; R3.7 trust gate outstanding (2026-10-30)

Operator-supplied read-only report from updated `~/bob-next`: publisher timer **active**, publisher oneshot service **inactive**, Shadow4 timer **active**, startup reconciliation timer **active**, candidate publisher timer **inactive**, legacy system Scout timer **inactive**; v0.7 SQLite schema **match** and policy **valid**, pause **not_paused**, existing v0.7 automatic comments **enabled**, **22 attempted_at-bearing history records**, **0 states flagged for delivery review**, `baseline consistency: observed`, `review blockers: none`, `cutover authorized: NO`. This verifies a compatible point-in-time host baseline. It does **not** verify actual published comment totals, unit/drop-in topology or reboot resilience, actual live GET/friend result freshness, owner approval of R3 activity, or installed publisher support for new sealed Bob drafts.

R3.7 must gate each proposed new Bob-authored comment through a single credentialed publisher with independently authenticated owner settings, saved-source verification, exact draft seal/consent, reliable local friend protection, authenticated post-existence GET, a final pause and budget check, durable pre-POST intent, and no blind retry for uncertain outcomes. Any auto mode requires separate explicit R3 opt-in in addition to the existing `auto_enabled=1`; do not silently treat the v0.7 setting as consent for new Bob-authored actions. Keep all R3 code uninstalled until a reviewed cutover.

---

## R3.6 host-check implementation, production approval still withheld

**Code added:** `scripts/report_r36_host_readiness.py` expands the older R3.0 inventory to include the publisher service, Scout service, original/reconcile services and two inert candidate unit names; verifies essential exact v0.7 schema columns and reports **counts only** for attempted and uncertain delivery states, along with validated legacy activity limits and pause/auto settings. Its default CLI prints a compact operator report, optional `--json` remains metadata-only, all under fixed `systemctl show` and SQLite `mode=ro` calls. It never reads API keys, outputs prompt/comment text, alters installed files, starts workers or posts. **No actual OMEN inventory has been run by this PR.**

`src/bob_v08/r36_admission_contract.py` is a second independent non-dispatch classification check. It uses real locally saved Scout result/feed hashes through `verified_source`, validates the *exact* old draft hash for legacy jobs, or the new Bob draft seal and attached `r3_proposals` fingerprint for R3 jobs. Any attempted or uncertain job, altered payload or missing source record is rejected. `dispatch_authorized` stays false even for well-formed test examples. The existing credentialed publisher remains unchanged and would still reject the new Bob seal.

**Owner acceptance:** [one safe read-only host command and interpretation](docs/R36-HOST-READINESS.md). A baseline-consistent report is not cutover approval. Real installed unit/drop-in shape, WSL reboot, trusted owner/friend/GET authority and final pre-send behavior remain future gates. The installed Shadow4 and v0.7 publisher remain the sole running decision/publishing systems respectively.

---

## R3.5 additive migration and restart safety rehearsal (source-only, October 30, 2026)

**Added:** `src/bob_v08/r35_migration_lab.py`, `scripts/rehearse_r35_deployment.py` and `tests/test_r35_migration_recovery.py`. This is an isolated rehearsal, not a deployable upgrade. It has no new release manifest entry, no publisher API integration, no start/stop of systemd, no access to the OMEN legacy queue, and no credential handling.

The migration class only accepts a **pre-existing private synthetic SQLite file** with the exact name `r35-inert-fixtures/r35-legacy-queue-lab.sqlite3` and a matching `r35_fixture_meta` marker; wrong paths, symlinks, unsafe permissions, missing or altered legacy tables and unknown versions fail closed. It validates the same essential `publish_jobs`, `decisions` and `publish_settings` column contract used by `src/lib/bob/bob_publish_common.py`. The intended additive schema has `r3_proposals`, `r3_owner_approvals`, `r3_lab_audit` and `r35_schema_meta`, matching the R3.3 synthetic draft/approval model. All DDL and its version marker are committed in a single `BEGIN IMMEDIATE` transaction. Injected crash before commit removes **every newly created table**, leaving all queued jobs, previous attempts, uncertain states, owner decisions and settings unchanged. Subsequent retry is idempotent; schema collision and unknown versions are refused, not overwritten.

The **code rollback** exercise explicitly does **not** restore a stale full database snapshot or remove new additive tables. Even when a newer simulated uncertain attempt appears after migration, its `attempted_at` and state remain intact. Only the hypothetical code pointer and service ownership return to baseline. Preserving old history is a safety invariant, not a reason to replay an uncertain write.

The new reboot evaluator `reboot_reconcile()` consumes *synthetic* observed old/new timer and worker states. A single verified legacy publisher after boot can be classified as safe baseline; duplicate timers, split worker/timer ownership, unknown startup reconciliation, candidate auto-resume, and quiesced no-writer state all require a hold or manual review. The evaluator **does not disable timers or assert any actual host state**. The one-command offline report uses existing `stage_service_graph.write_timer/write_service` inert publisher/scout/original/reconcile templates, checks timer-to-service targets and one-shot shape, runs a simulated rollback, and prints only harmless verdict flags.

**What R3.5 does not prove:** exact installed unit/drop-in contents, WSL/Windows reboot behavior, actual dispatcher drain, pre-POST ownership takeover, real GET/friend proofs, owner authorization, production migration compatibility or restart from an active network attempt. A production updater would need exact installed-source and schema verification and a carefully reviewed, operator-approved transition with one writer. A genuine R3.5 host cutover has **not** been attempted. `main` remains the stable production reference, `next` is development, and `v0.8.0-shadow4` continues unchanged on the OMEN.

**Next R3.6:** compare sanitized real host unit/queue inventory against this model, design a fail-closed credentialed publisher adapter for Bob-authored drafts, and run a separate inert rehearsal with exact versioned unit templates. Do not grant a new automatic action or install a publishing candidate until explicit owner approval and full R2/R3 gates.

---

## R3.4 guarded source boundary + service ownership rehearsal (source-only candidate, 2026-10-30)

**Implemented:** `src/bob_v08/r3_cutover_rehearsal.py`, `scripts/rehearse_r3_cutover.py`, and `tests/test_r3_cutover_rehearsal.py`. This phase remains an **inert, offline rehearsal**, not a production publisher adapter or executable cutover. The OMEN's installed `v0.8.0-shadow4`, `bob-moltbook-publisher`, legacy `activity-queue.sqlite3`, API credentials, user timers and Windows startup are untouched. Nothing is added to `releases/current.json`.

### Genuine saved-source trust boundary, still not live platform proof

- `verified_source(source_dir, action)` invokes the existing reviewed `read_observation()` to re-read the *actual* schema-2 Scout result and feed bytes from a fixed caller-owned source directory, enforcing feed SHA-256, draft/approval hashes, exact selected post, source run, no symlinked source files, size bounds and strictly parsed Bob model action. Its `SourcePin` locks `source_run`, `target_id`, `snapshot_sha256` and the **legacy Scout's** `approval_sha256` against drift. **This pins saved evidence, not proof a post remains live/public or has received comments.**
- `simulated_source_handoff()` re-verifies the same saved source **before proposing, before queue admission and before simulated intent**, using R3.3's *synthetic* unified ledger. A changed/missing source is refused; if the Bob draft is already queued, the harness records a **terminal synthetic hold** without consuming a send attempt. New Bob text retains its **own distinct seal** and does not inherit approval of the legacy Scout draft.
- `r3_unified._permission()` now rereads a separate persisted synthetic `publish_settings.r3_comment_dial` inside its queue/intent SQLite transaction. Missing/Off/corrupt stored dial denies. Owner's Propose dial cannot become Auto through a caller-supplied `Policy`; a changed dial after queuing terminally holds the draft. The old `auto_enabled`, independent `r3_auto_enabled`, manual approval, auto opt-in timestamp, and v0.7 budget/spacing gates remain required. **No new production owner toggle or deployed permission is created here.**
- The pause marker reader fails closed on symlinks, missing/untrusted parent directory and unreadable state in a private fixture. `Proof` is still *synthetic caller-supplied data* that cannot establish real Moltbook GET/friend status; final live proof and pause consistency are **not built**. The host adapter must obtain both from trusted sources immediately before a future credentialed POST, not accept values from Bob's prompts or the web UI.

### Inert one-writer ownership rehearsal

- `CutoverState` / `rehearse_cutover()` models the exact safety sequence **baseline (legacy publisher timer owns writes) → staged (candidate inert) → quiesced (legacy drained and timer disabled, candidate still disabled) → candidate (only after separate explicit owner approval and proofs) → rollback (candidate drained and disabled before legacy re-enabled)**. The shadow timer remains unchanged. The old system-scope Scout timer is modeled as inactive; an active duplicate, overlapping senders, missing backup/drain/rollback proof or non-boolean owner-approval flag refuses.
- This is **pure data**. No systemctl commands are generated or executed and no actual unit names are installed or switched. A candidate publisher can never be activated through this repository change. The command `python3 scripts/rehearse_r3_cutover.py` reports a deliberately **denied** unauthorized activation followed by a simulated code-only rollback. Historic attempted and uncertain publication identifiers are preserved exactly.
- Tests cover fresh verified saved Scout input, feed tampering after queue and fully resealed changed feeds, symlinked sources, changed local owner dial, pause appearing after queue, synthetic GET expiry/target mismatch, explicit manual approval of the new seal, default Shadow/Off, simultaneous-ownership refusal, worker drain requirements, authorization type strictness, and history-preserving rollback.

### Outstanding before any deployment/release (R3.5 and later)

1. **Real host-bound trust adaptor:** obtain verified Saved Scout input from the installed storage with symlink-resistant path handling and an independently authorized source root; derive owner policy and pause **only** from trusted local owner settings, not caller flags. Implement a trusted bounded GET/friend preflight that cannot be fabricated by the model. Current `Proof` in R3.3 is an *offline stub*, not such an adapter.
2. **Actual unit/release topology:** read-only inventory and sanitize the installed user/system unit graph, including startup reconciliation and exact timer/worker states. Then simulate the actual unit templates, disabled candidate listener, pause/drain, idempotent start/stop and recovery under fresh-host and crash/reboot fixtures. The current ownership state machine is **abstract**, not proof actual systemd transitions are safe.
3. **Database migration and rollback:** design additive source-type validation and new Bob-draft sealed schema changes acceptable to the **single existing credentialed publisher**. Preserve all pre-existing queue/approval/event rows and attempted/uncertain states; test in private copy of synthetic fixtures only. Never restore a stale full SQLite backup over newer post-attempt history during code rollback.
4. **Operator gate:** no automatic v0.8 posting, no new category authority, no production software update until explicit owner review/authorization and final end-to-end one-writer/rollback acceptance. R2's naturally timer-driven **model decision** is independently still open; successful timed no-op service execution is not that decision.

---

## R3.3 unified publisher handoff laboratory (synthetic only, 2026-10-30)

**New source:** `src/bob_v08/r3_unified.py` and `tests/test_r3_unified.py`. R3.1 and R3.2 remain isolated historical labs; this is the first **single-ledger simulation** combining Bob-authored sealed proposals, explicitly separate owner approval/auto opt-in, legacy-shaped `publish_jobs`, the real `bob_activity_limits.allowed()`, queue priority, and the final simulated `attempted_at` CAS with an audit row. The code refuses any database except an owner-private fixture named `r3-unified-fixtures/r3-unified-lab.sqlite3` with a verified `r3_lab_meta` marker, file mode 0600, and parent 0700. **No production installation, permissions, credentialed HTTP calls or systemd modifications.**

### Lifecycle rehearsed

1. **Propose (zero authority):** strict exact `Action` / `Observation` target match and SHA-shaped source metadata, valid Bob comment text, an independent `seal_sha256 = SHA256(post_id + newline + Bob_comment + newline + snapshot_SHA)`, and action fingerprint. Only the isolated `r3_proposals` table is populated; this is neither an owner approval nor a legacy Scout `decisions` row. Unique source-run and post IDs prevent competing proposed actions from silently displacing one another. For a future real build, an independently verified `read_observation()` must supply the `Observation`; syntactically shaped test objects are **not production source verification**.
2. **Queue (single transactional source of truth):** a matching sealed proposal plus a *separately authored* owner-approved seal for manual, **or** both current v0.7 `auto_enabled` and separate `r3_auto_enabled` plus an opt-in-after timestamp for auto. The v0.8 dial must be consciously configured to Propose/Auto for manual or Auto for auto, with `shadow=False` in **synthetic fixtures only**. The default installed Shadow4 policy denies. No borrowing old Scout drafts or existing `decisions`. Target/run conflicts with the legacy queue fail closed. The candidate enters a *synthetic legacy-shaped* `publish_jobs` queue with its own seal and text, not a second parallel action budget. No dispatcher is added.
3. **Final pre-send simulation:** in one `BEGIN IMMEDIATE` transaction, re-read exact queued draft and seal, separate owner decision, both auto settings, valid opt-in date, source age, manual-first FIFO head, current legacy attempts/settings, v0.8 budget/spacing, current pause input and a bounded target-matching **synthetic** external GET/friend proof. Revocations or changed source content terminally hold; stale GET or an earlier manual job waits/refuses without consuming attempts. The only success is `sending_simulated` with one `publish_jobs.attempted_at` and one audit entry **inside the same transaction**; no POST exists. SQL crash injection leaves no partially counted attempt.
4. **Unknown outcome:** a simulated crash/ambiguous response transitions a counted attempt to `uncertain` and locks it against automatic resend. Reopening the fixture must preserve history; rollback must never restore an older queue database over newer attempts.

**Tests:** default shadow/off, approval missing/rejected/revoked, fresh manual consent, separate fresh auto opt-in and its revocation, fake/expired preflight proof, friend protection, manual queue priority, changed Bob wording, duplicate legacy target, source expiry, exact shared budgets/cooldowns, simultaneous claims, SQL trigger rollback, and irreversible uncertainty. All outputs include `simulated:true, acted:false` and live queue paths are rejected.

### Production cutover blockers (R3.4)

- The lab currently receives a caller-provided `Observation`, `Policy`, `paused` and `Proof`. These **are not trusted credentials or live attestations**; a real publisher must obtain verified Scout bytes, owner settings, durable consent and live preflight from trusted host-side sources, never from Bob's model JSON.
- The existing v0.7 publisher's `load_record()` reads legacy Scout drafts and would **not** accept a newly sealed Bob comment. Real implementation requires a reviewed, branch-specific source validator and queue admission path with no bypass of manual priority or rate limit. Simply inserting a live `publish_jobs` row would be unsafe and is **not implemented**.
- The actual paused filesystem marker and GET/friend lookups live outside SQLite. True final consistency needs a publisher-owned recheck immediately before the real HTTP POST, with a clear conservative hold on any changed/unknown boundary.
- A backward-compatible migration, worker ownership change, isolated release rollback and recovery from process crashes must be rehearsed with real unit templates. Old `main` production remains authoritative; `next` contains source work only.
- No automatic publication permission is enabled by this lab, and **R2 natural timer-driven model-decision evidence** remains a separate pending gate.

---

## R3.2 legacy queue compatibility lab: source candidate (2026-10-30)

Added **`src/bob_v08/r3_legacy_compat.py`** and **`tests/test_r3_legacy_compat.py`**. The module runs only against a deliberately named synthetic database `r3-compat-fixtures/r3-legacy-compat-lab.sqlite3` with a private-directory/0600-file check **and an in-database synthetic-only marker**; it **refuses live `activity-queue.sqlite3`**, unmarked fixtures, symlinks, or untrusted source/model payloads. No credential loading, network operations, service controls, new publish routes or v0.7 process changes.

**Actual v0.7 contract exercised:** the existing `publish_jobs`/`decisions`/`publish_settings` schema, oldest manual-first/FIFO queue head, exact `approval_sha256` plus `draft_comment` equality, human-approved manual jobs, owner decision overrides on auto jobs, `auto_enabled`, and 3-hour auto/7-day manual age limits. Auto friend protection requires an *explicit simulated* verified-clear signal, never inferred from the local Friends directory. Existing `bob_activity_limits.allowed()` is imported and called against **the same transaction** to enforce stored total and automatic UTC budgets, spacing, malformed previous timestamps and invalid user settings. Existing attempted or uncertain same-target jobs block further claims.

**Independent v0.8 condition:** the simulation rejects the current default `shadow=true` and Off/Propose dials. A positive test must supply a deliberately synthetic `shadow=false, comment=auto` policy, pass the current pure action check, and also pass the legacy queue and owner settings. This does **not** change installed Shadow4 permissions.

**Atomicity:** `BEGIN IMMEDIATE` locks a fixture for queue-head selection, approval/settings evaluation, one compare-and-swap transition to `sending_simulated`, simulated `attempted_at`, and a sanitized audit row in one transaction. Failures roll back all fields; concurrency tests allow only one claimant; a deliberately simulated unknown outcome transitions to `uncertain` and never retries. No HTTP request exists in this module.

**Critical semantic limit:** A new Bob shadow comment is **not** automatically the v0.7 Scout draft. A differing `action.text` is refused, even if the target and selection match. This compatibility harness demonstrates how to retain already-queued manually approved/auto-vetted jobs; a future R3 route for Bob-authored *new* comments needs independently reviewed source sealing, queue insertion, authorization, and publisher ownership. Do not replace a human-approved draft, create an auto-approved job, or silently reinterpret post IDs as outgoing comment IDs.

**Not yet a deployable R3 cutover:** caller-supplied source validity, friend clearance and preflight confirmation are laboratory inputs. Real production will require authentic `read_observation` validation, live friend guard and GET preflight, actual pause state, a fresh v0.8 policy snapshot, atomic integration with current publisher's pre-POST handling, and timer ownership transition rehearsals. An external pause marker is not transactional with SQLite, so a final check is required immediately before the credentialed POST. No live cutover is authorized by these tests or docs.

---

## R3.1 transaction and pre-send recheck laboratory (source-only, acceptance pending)

Implementation candidate: `src/bob_v08/r3_reservations.py` and `tests/test_r3_reservations.py`. This is an **offline isolated simulation engine**, not a publisher, authority service or deployed file. `releases/current.json`, running Shadow4, v0.7 jobs, legacy database, user timers and credentials stay unchanged. The module deliberately has **no network/publisher/worker imports or functions**.

- Only parsed, source/target-matched **comment** actions with a bounded reason and text, and syntactically validated source hashes, can enter the simulation. In a later actual integration, the caller must supply `read_observation`-verified provenance and freshly loaded, authoritative legacy budget, owner consent and duplicate history. A model-provided `Observation` or `PolicyState` is never trusted.
- The simulation refuses `Policy.shadow=true` (the currently installed shadow mode), off/propose dials, disabled legacy automatic commenting, pause, invalid clocks/budgets/spacing and mismatched source/target. The *only* test-positive path explicitly configures synthetic `comment=auto` and `shadow=false`, which does **not** enable real host permissions.
- Private lab-only SQLite filename `r3-reservation-lab.sqlite3` under a 0700 directory, 0600 DB, `BEGIN IMMEDIATE`, unique `(kind,target_id)` and `(kind,source_run,target_id)` indexes, never raw comment text or credentials stored. Reserved-but-unsent actions conservatively consume the synthetic daily budget and spacing slot; duplicate/held/unknown targets stay locked. All status/audit transitions are in the same transaction; errors roll back completely.
- A separate `simulate_pre_send` must match the source/content fingerprint and re-evaluate **fresh** policy, baseline counts and authorizations under a new write transaction. A revoked permission, newly exhausted budget, changed payload or backdated clock produces `held`; approved conditions produce only `intent_simulated`, **not an HTTP request**. `simulate_uncertain` models irreversibly locked unknown results.
- Synthetic tests prove the failure matrix: concurrent duplicate claims, concurrent budget serialization, UTC midnight crossing, minimum spacing, external baseline counts, revocation/pause after reservation, stale clock, payload drift, transaction rollback on induced SQL failure, symlink/corrupt path refusal and irreversible uncertain outcomes. No Moltbook or OpenClaw call is made.

**Important engineering limitations before R3.2:** This is a transaction algorithm rehearsal, not the final dispatch ledger: policy/baseline snapshots are passed from an isolated caller; they are *not* yet loaded or locked against the real existing `publish_jobs` and settings transaction. No production user authorization, publisher integration, service cutover, lock handoff or unknown-delivery recovery exists. In R3.2 establish one **legacy-compatible source-of-truth transaction** for existing attempted sends and owner settings, preserve manual-first queue priority and real publisher's intent-before-POST, and rehearse crash/restart/migration without wiping private historical DB rows. No cutover until explicit owner approval.

---

## R3.0 source-only inventory implementation (CI candidate, no host install)

Added `scripts/report_r3_cutover_inventory.py`: a **read-only, metadata-only** report of nine fixed Bob/OpenClaw user/system service units (including legacy scout and v0.8 shadow); safely classified systemd load/active/enabled/result values; count-only manual/auto comment queue state and attempted-at presence; persisted auto_enabled state; paused marker state; and the **actual** legacy `bob_activity_limits.read_limits()` policy applied to a SQLite `mode=ro` connection. Missing/corrupt/invalid data returns unavailable/invalid and cannot authorize cutover. No record IDs, raw model content, credential paths, unit environment or arbitrary systemctl parameters appear in output. No publishing, service control, DB migration or update code exists here.

Offline synthetic tests `tests/test_r3_cutover_inventory.py` verify bounded allowlists, invalid values, symlinks and missing SQLite, unchanged source bytes, invalid persisted limits, no secret strings, and perpetual `cutover_authorized:false`. CI includes both new paths. **No host deployment requested**; this is one reviewable engineering increment toward the later exact ownership/rollback gate, not a live source-of-truth report yet.

**Latest natural shadow evidence:** owner verified service `Result=success` at 17:30:05 PDT and then queried the shadow event DB for UTC 00:29–00:31, finding **zero events**. This means no new observation/decision/error was recorded for that tick, consistent with exhausted saved Scout selections. It does not prove why the service returned (its standard output was not available), nor does it prove a timer-driven model decision. Continue natural shadowing without forcing replay.

---

## Scheduled shadow evidence update (2026-10-30, 17:30 PDT)

The active Shadow4 timer executed its service automatically: systemd's `LAST` reported 17:30:05 PDT and the service's `Result=success`, with actual start/exit timestamps. The 17:30 run's **domain outcome** remains unclassified because the CLI uses exit code zero for no new verified sources and handled model rejections as well as valid shadow decisions. Keep that distinction in R3 event/health design: `service_executed` must not be conflated with `source_processed`, `model_decision_accepted`, or `externally_published`.

---

## R2 evidence handoff to R3.0 (private one-shot MD1 verified 2026-10-30)

A live owner-approved `bobctl shadow-experience` yielded a source-grounded response from Bob's real OpenClaw main agent covering six latest verified Scout selections. Publication statuses and uncertain visibility were represented, but model interpretation overstated `publisher_failed` as an actual attempt without checking `attempted_at`. R3 must **explicitly preserve the distinction** among `queued`, `failed_before_sending`, `sending/uncertain`, `acknowledged` and `publicly_verified`. An observed third-party post ID is never Bob's published comment ID. Do not use an unverified natural-language account of activity as evidence to dispatch actions, adjust budget or create historical records.

The one-shot does not provide durable Gateway memory or authorize sending. The naturally scheduled Shadow4 run remains to be verified on host before full R2/G1 closure.

---

# R3.0 guarded cutover: read-only source inventory and safety contract

**Status:** design/inventory only. Prepared October 30, 2026 on `next`; no release manifest, service, credentials, queue or production state changed. **R2/G1 remains pending** naturally scheduled shadow execution and an accepted opt-in experience review. Do not activate external v0.8 actions from this document.

## Verified source-level starting point

| Component | Existing source/evidence | R3 implication |
| --- | --- | --- |
| Real decision-maker | `src/bob_v08/shadow.py`, `src/bob_v08/core.py` | Uses current OpenClaw `main` agent in isolated sessions, pinned verified saved Scout targets; source-bound `comment` or honest `skip`; current `Policy()` default Off. A `shadow_decision` is not permission to POST. |
| Safe shadow evidence | `src/bob_v08/evidence.py`, separate `~/.local/state/bob-v08-shadow/events.sqlite3` | Append-only metadata; old failed rows remain. Must not treat candidate action as a publish job or overwrite historical evidence. |
| Existing Scout | `src/bin/bob-moltbook-scout`; user `bob-moltbook-scout.timer` documented in `docs/RELEASE-REHEARSAL.md` | Fetches/reviews bounded data and creates source-verifiable candidate drafts. Do not start two concurrent Scout generators; distinguish reader from actual publisher ownership. |
| Existing comment publisher | `src/bin/bob-moltbook-publisher`; user `bob-moltbook-publisher.timer` in prior inventory | Host-side credentials; manual-first queue ordering; exact approval, integrity, freshness, duplicate, global pause, budget/spacing and preflight checks; intent persisted before POST; uncertain results not automatically retried. **This remains authoritative through R2.** |
| Limits and settings | `src/lib/bob/bob_activity_limits.py` plus `docs/V072-ACTIVITY-LIMITS.md` | Current saved UTC daily/auto budgets and spacing values must be read as actual state, not assumed from defaults or a recommended preset; changing settings does not authorize a new action. |
| Original-post worker | `bob-original-worker.timer` in prior unit inventory; `docs/ARCHITECTURE.md` | Distinct human approval domain. No R3 automatic-original shortcut or shared comment budget. |
| WSL/Gateway/Manager | `src/bin/bobctl`, `docs/RELEASE-REHEARSAL.md` | Gateway + Activity Manager + startup-reconcile units remain distinct. R3 must not change Gateway bind or authenticated LAN access during cutover. |
| Release/update contract | `scripts/bob_release_updater.py`; `docs/OPERATIONS.md` | Source from clean `~/bob-next`; exact installed `from` release and hashed file list; private backup, journal, health and code rollback. A data snapshot restore can erase subsequent real publications. |

**Current owner-observed host checkpoint:** `v0.8.0-shadow4` installed; one validated `comment` decision on run `20261030T200610Z` received `deny/action_off` and `acted:false`; verified versioned shadow timer active. `list-timers` showed an upcoming activation at `2026-10-30 16:08:11 PDT` and `LAST -`, not a confirmed completed scheduled run. Existing v0.7 publisher was not changed.

## R3.0 engineering deliverables, before any implementation capable of sending

1. **One writer, one record of truth.** Diagram exact service and DB ownership from the *current installed user units* as a read-only snapshot. Identify which legacy timer creates decisions and which credentialed process actually dispatches. R3 must not introduce competing publishers, bypass manual queue priority, or simultaneously run legacy and new decision generators when cutover is active.
2. **Canonical action and approval mapping.** Define lossless mappings of legacy manual/auto comment jobs, queued/sending/uncertain/published/verification states, approval hashes, paused/auto-enabled settings, daily attempts and spacing into the R3 event/dispatch contract. Missing or ambiguous state must become denied/held, never interpreted as automatic approval.
3. **Reserve then recheck.** Design transactional unique (source_run, target, action) reservation, global UTC budget and cooldown check, commit to durable intent before POST, then final permission/source/approval/duplicate/budget check immediately before the existing credentialed publisher's send. A parsed model JSON object or prior pure policy `allow` must never dispatch alone.
4. **Unknown means locked.** Preserve in-flight, timeout, crash, moderation challenge and mismatched-ack outcomes as non-retryable until an explicit recovery review. Source-visible verification requires a separate read-only check and is not inferred from an API acknowledgment.
5. **Preview-and-rollback cutover.** Rehearse in isolated synthetic copies: concurrent ticks, timer overlap, crash after reservation, crash before/after POST intent, changed owner permission mid-run, shadow pause, expired Scout material, duplicate target, UTC rollover, install failure, rollback without restoring an obsolete DB. Stage a service-ownership transition plan with exact old/new unit names, verification and recovery. Do **not** modify the live units yet.
6. **Owner control and acceptance.** Default all v0.8 outbound action categories Off. Require explicit opt-in for each proposed category and the exact cutover itself. Existing manual approvals and post limits continue to apply. R3's first permitted live action, if authorized later, must be single, easily auditable, and never automatically retried after ambiguity.

## Actual host unknowns requiring a later bounded read-only inventory

- Current complete user systemd unit and drop-in contents, enabled state and last execution (old `docs/RELEASE-REHEARSAL.md` snapshot is historical).
- Actual current saved activity limits, pause/auto flags and queue counts, not simply defaults.
- Current publisher state-machine schema and possible concurrent controller/worker races; exact restart and rollback prerequisites in the installed release.
- Whether naturally scheduled Shadow4 decisions and private MD1 experience review both pass on host after manual smoke success.

**Operator ergonomics:** Build one non-mutating sanitized R3 inventory report rather than asking for dozens of terminal commands. Tests must use synthetic data; no Moltbook write calls, API keys, private model text or production SQLite copies in Git.

## Next sequencing

- **R2/G1 host:** confirm one genuinely timer-driven shadow tick and run the explicitly consented `bobctl shadow-experience` one-session MD1 probe. Leave external v0.8 permissions Off.
- **R3.0 source work:** complete service/DB ownership inventory and pre-cutover safety specification, then isolated offline fixtures. Documentation and synthetic CI may proceed while R2 acceptance is being collected.
- **R3 release candidate:** only after R2/G1 gate closes and R3.0 race/rollback proofs are reviewed. A documentation merge neither installs software nor authorizes a cutover.
