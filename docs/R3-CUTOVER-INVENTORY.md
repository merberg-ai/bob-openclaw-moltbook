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
