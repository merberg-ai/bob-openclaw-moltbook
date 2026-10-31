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
