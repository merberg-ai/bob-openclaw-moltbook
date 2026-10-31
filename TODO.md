## R3.13d Off-first release + controlled live migration source accepted (2026-10-31)

- [x] Implement isolated production-compatible `BEGIN IMMEDIATE` additive **R3 Off** schema transaction: exact R3.5 and versioned R3.13c tables, four default-Off independent owner keys, historical record/attempt digest, idempotence, future/partial schema and non-Off consent rejection, crash-before-commit rollback. No network or R3 publishing authority.
- [x] Implement `scripts/r313d_live_off_migration.py` as a **read-only by default**, fixed-user/host command; `--apply-off` demands owner TTY phrase `MIGRATE R3 OFF`, installed registry-attested `v0.8.0-r3stage1`, reviewed effective publisher, three hard-Off source gates, private global pause marker, disabled and inactive publisher timer, inactive publisher/manager services, serialized updater lock, restore-tested private SQLite backup and fsync `prepared/complete` journal. No arbitrary source path, unit action, credential or Moltbook request. Code-only rollback only.
- [x] Add offline synthetic database crash/history/unknown-schema/unit-drain/unauthorized-action regressions, CI paths and [operator guide](docs/R313D-LIVE-OFF-MIGRATION-GATE.md).
- [x] **CI/source acceptance PASS:** PR #90 merged to `next` at `ea8f3506a336a3616e5fe64b829d583f86f3d922`; GitHub Actions run `41213864893` passed **941 Python tests** and Windows startup-script parse. No live schema or installed R3 publisher changed.
- [x] **OMEN Off-first pre-install review accepted (operator-reported, 2026-10-31):** `scripts/report_r313d_off_first.py` returned `candidate build: PASS`, active release `v0.8.0-shadow4`, all three real-send gates `OFF`, installed host boundary `eligible`, separate installation review eligible `yes`; no live file, service, schema, permission or Moltbook changes.
- [ ] **Owner-authorized release promotion/install remains pending:** `v0.8.0-r3stage1` is still only a candidate; do not change `releases/current.json` or invoke `bobctl update` from this read-only report. Later require separately approved drained maintenance, live Off schema migration, explicit draft-specific manual canary, restart/WSL reboot, rollback and G2. R2 G1 remains open.

---

## R3.13d owner Controls and sealed OpenClaw proposal source accepted (2026-10-31)

- [x] Preserve hash-pinned v0.6 manager source and full legacy generated UI chain; add **separate R3 Controls** page via additive subclass over R2 Shadow + FM4.1/OC4 manager. Inherit existing LAN Basic/Host/Origin/CSRF. Publish settings still independent of Scout v0.7 auto and approvals.
- [x] Add exact sealed Bob-draft owner approval, independent manually enabled R3 setting, separately typed manual queue action and safe revocation of **only unattempted** R3 jobs. R3 automatic publication is hardcoded **compiled Off**, even when old auto mode is On.
- [x] Add `bob-r3-propose --once` trusted OpenClaw Bob/main-agent proposal-only worker. It rereads saved Scout evidence and original model decision, persists a bounded canonical action-envelope plus proposal transactionally, but cannot queue/send, infer approvals, or read credentials.
- [x] Add deterministic standalone R3 module archive, updater-registry hash/owner/path verified import, R2/OC4-compatible manager/nav generator, separate **Off-first** `v0.8.0-r3stage1` release candidate (not active), read-only `report_r313d_off_first.py` review, tests and [operator guide](docs/R313D-PRODUCTION-OFF-FIRST.md). The legacy credentialed publisher is excluded from this release.
- [x] **Off-first owner source accepted:** PR #89 merged to `next` at `d12ca1fa90d36456872598ec330dfd66c75a33cc`; **932 Python tests** and Windows startup parse passed. The candidate is not the active updater manifest; separate owner-approved release promotion/install remains required.
- [ ] **Production host cutover still pending:** owner-verified versioned Off-first install, trusted maintenance/backup and actual additive DB migration (no stale DB restores), separately approved manual-only real Moltbook canary via one publisher, systemd/Windows/WSL reboot, post-verification and no-duplicate recovery. Do not authorize automatic R3 posting by default. R2 G1 remains open.

---

## R3.13d OMEN private staging acceptance PASS (2026-10-31)

- [x] **Owner-reported read-only host audit PASS:** trusted queue boundary `yes`, legacy schema `match`, installed R3 consent `absent_off`, effective publisher unit `reviewed_shape`, installed executable `owner_controlled_regular`, updater registry hash `verified_registry_hash`, all three source-level R3 gates `verified_three`, staging eligible `yes`; boundary blockers `none`, source blockers `none`.
- [x] **Owner-reported disposable migration PASS:** `r313c_action_envelopes` / schema version `match`, newly introduced controls `explicit_off`, crash rollback and idempotence `True`, historical data preserved `True`, historical send attempts `22`, historical uncertain states `0`, new synthetic uncertain attempt survived code-only rollback `True`, private snapshot deleted. No live database, installed files, services or consent changed. Real R3 sends and cutover authorization remained `NO`.
- [x] Record the operator-supplied sanitized results as **point-in-time staging acceptance**, not proof of production migration or independent live-service verification; no credentials, database records, unit bodies or absolute paths reproduced.
- [ ] **R3.13d production work still pending:** authenticated independent R3 Controls UI (manual and automatic Off by default) and exact-seal proposal authorization/writer; versioned installable release, journaled service drain and verified live additive migration, separate explicit authorization for one-publisher Moltbook canary, WSL/Windows reboot, uncertain/no-retry acceptance and code-only rollback. R2 G1 natural timer-driven new source-linked model decision remains open.

---

## R3.13d source and OMEN private-stage gate accepted (2026-10-31)

- [x] Add marked-copy-only versioned `r313c_action_envelopes` and `r313c_schema_meta` migration after R3.13b's explicit default-Off controls. Verify exact legacy rows, atomic crash rollback, idempotence, future/partial/drifted schema rejection, and zero live schema or permission changes.
- [x] Rehearse a **sealed Bob action producer** only inside the trusted private fixture: reconstruct source-linked original decision, validate canonical envelope/seal/fingerprint, insert draft proposal atomically without `publish_jobs` queueing, owner approval or any public network request.
- [x] Add fixed-host read-only report and explicit `--private-copy` SQLite online backup (including committed WAL), installed publisher registry and effective-unit checks, three source-level Off gate checks, post-upgrade synthetic uncertain attempt and code-only no-history-rewind check. Add synthetic regressions, CI triggers, [operator guide](docs/R313D-STAGING-OFF.md) and expressly noninstallable candidate. `releases/current.json` remains Shadow4.
- [x] **Source CI accepted:** PR #86 merged to `next` at `776ad1eac51a8b0f631fc543856a0d34ab4765ad`; GitHub Actions run `41174232285` passed **922 Python tests** plus Windows startup-script validation. Existing legacy publisher imported and remained unmodified.
- [x] **OMEN operator acceptance PASS (2026-10-31):** read-only audit and explicit disposable private-copy staging migration both passed; no production changes or R3 posting authority. See the recorded results above.
- [ ] **R3.13d production completion remains:** audited authenticated Activity Manager manual/auto R3 Controls and source-linked proposal writer, separately reviewed installable `v0.8.0-cutover1` transaction, authorized maintenance/drain/backup/live additive migration and one-publisher canary, WSL/Windows reboot and code-only rollback. No real R3 send/automatic consent without express owner authorization. R2 G1 remains independently open.

---

## R3.13c source-only candidate accepted and merged (2026-10-30)

- [x] Correct the action provenance gap: R3.5 proposal seal/fingerprint do not preserve original Bob decision reason. Add bounded canonical `r313c_action_envelopes` plus versioned `r313c_schema_meta` additive contract, verified against the saved Scout source, independent seal and matching proposal before preflight, claim and dispatch.
- [x] Wire `bob_r313c_adapter.maybe_r3_publisher_step()` into the **existing** `src/bin/bob-moltbook-publisher`. The publisher's integration guard stays **True=Off**, and both R3.12/R3.13c real production send switches stay hardcoded **False**; candidate dependencies are not imported by the current legacy publisher. Current v0.7 Scout publisher and installed Shadow4 remain untouched; no second credential, service, external request or owner authority.
- [x] Candidate same-ledger atomic `BEGIN IMMEDIATE` attempted-intent claim, whole-queue manual-first, R3.9 fixed post+author GET, independent R3.13b R3 manual/auto controls, verified source/friend/owner/pause/budgets, final after-intent barrier, API ACK distinct from public verification, human challenge and timeout/crash/restart no-replay.
- [x] Add offline fake GET/POST regression suite, actual publisher default-Off test, envelope reason tampering, owner revocation, friend, pause, duplicate target, priority and competing workers. Add CI triggers, [guide](docs/R313C-ONE-PUBLISHER-OFF.md) and explicitly noninstallable release candidate metadata.
- [x] **R3.13c source gate accepted:** PR #84 squash-merged into `next` at `1b13dd7f12c597adffd282f4dc9757df463eb1f6` after GitHub Actions run `41169512190` passed **911 Python tests** and Windows startup parse. The actual legacy publisher's clean install/import and default R3 hold behavior passed. No OMEN installation or R3 real sender/owner authority is part of this acceptance.
- [ ] **R3.13d next:** separately authorized production action-envelope migration and trusted proposal writer, authenticated independent owner controls, versioned release and publisher drain/canary, real sender activation only after owner consent, challenge/reboot/no-duplicate/code-only rollback. R2 G1 natural source-linked timer decision remains open.

---

## R3.13b OMEN operator acceptance PASS (2026-10-30)

- [x] **Read-only installed-source review PASS:** trusted queue boundary `yes`; legacy schema `match`; installed R3 owner settings `absent_off`; effective publisher unit `reviewed_shape`; executable `owner_controlled_regular`; updater registry `verified_registry_hash`; installed versus unreleased `next` source `different_legacy_release_expected`; boundary and source review blockers `none`.
- [x] **Private-copy upgrade rehearsal PASS:** default-Off schema/owner-control upgrade `PASS`; simulated pre-commit crash rollback `True`; repeat migration `True`; existing history preserved `True`; historical send attempts `22`, uncertain outcomes `0`; newer synthetic uncertain attempt retained `True`; code-only rollback preserved history `True`; private copy deleted. Operator confirms live database changed `NO`, installed publisher changed `NO`, new R3 manual/auto posting rights `NONE`, cutover authorization `NO`.
- [x] Record the owner-supplied point-in-time sanitized results without copying database contents, unit values, credentials or paths. This validates R3.13b's rehearsal contract only, not a production migration or ongoing service health.
- [ ] **Next R3.13c:** review/build the existing single publisher's authenticated R3 admission and real-transport path with fixed-host exact post/author GET, source/friend/owner/pause/rate checks, durable intent and post-intent final barrier, challenge/timeout/uncertain no-retry; keep live dispatch Off pending distinct owner authority, production installer and independent authenticated R3 manual/auto UI.
- [ ] **Later R3.13d:** separately approved staged install, publisher drain, canary, WSL/Windows reboot and code-only rollback, preserving all new attempts. **R2 G1** remains independently pending.

---

## R3.13b source contract completed; OMEN acceptance PASS (2026-10-30)

- [x] Add `src/bob_v08/r313b_upgrade_contract.py`: no live entrypoint; exact marked 0700/0600 private-copy-only additive R3.5 schema and four explicit default-Off keys (`r3_comment_dial`, `r3_manual_enabled`, `r3_auto_enabled`, `r3_auto_since`). Validate all preexisting legacy rows, transactional crash rollback, idempotence and refusal of unknown schema / preexisting R3 opt-in. Legacy v0.7 Auto is never sufficient.
- [x] Add read-only independent consent review: manual requires separate R3 manual enable + compatible dial + exact owner-approved Bob seal; auto requires separate R3 opt-in, previous v0.7 opt-in and source-newer-than-R3-opt-in. No live UI setter or dispatch authority installed; every result has `dispatch_authorized=False`.
- [x] Add `src/bob_v08/r313b_install_attestation.py` for sanitized R3.8 effective-unit / actual installed publisher ExecStart binary verification, permissions, symlink/ancestor checks, private updater registry hash evidence and informative next-candidate comparison. No paths/secrets/hashes exposed. Missing registry tracking is not assumed to be validated release integrity.
- [x] Add `scripts/report_r313b_host.py`: fixed read-only host evidence; opt-in `--private-copy` SQLite online snapshot into strict marker/private fixture, upgrade tables+Off settings, simulated crash and rollback, idempotence, full legacy history validation, simulated post-upgrade uncertain attempt retained under code-only rollback, temp cleanup. Add focused regressions, CI triggers, [guide](docs/R313B-UPGRADE-CONSENT-ATTESTATION.md) and noninstallable candidate. `releases/current.json` unchanged.
- [x] **Operator acceptance PASS (2026-10-30):** read-only installed executable and publisher unit review, updater registry hash verification and disposable private-copy upgrade/rollback acceptance recorded above; no live changes or R3 rights.
- [ ] **R3.13c:** implement/review authenticated single-publisher R3 send branch and final after-intent source/friend/owner/pause barrier with challenge and uncertain no-retry. Independent authenticated UI controls and eventual release still need separate approval.
- [ ] **R3.13d:** separate owner-approved stage/drain/canary/reboot/code-only rollback before any real Bob-authored posts. R2 G1 remains open.

---

## R3.13a operator-accepted: trusted host roots and private-copy additive migration (2026-10-30)

- [x] Add a fixed-current-WSL-home trusted source-root reviewer with 0700 directories / 0600 queue checks, non-symlink ownership, R3 schema absence, owner R3 settings classification and sanitized R3.8 effective unit information. Never load tokens or arbitrary paths.
- [x] Add opt-in `scripts/report_r313a_host.py --private-copy`: SQLite mode=ro online backup (including committed WAL) into disposable private temp file, additive R3.5 tables only on that file, simulated pre-commit crash/rollback, full five-table row digest and attempted/uncertain history preservation, idempotence, cleanup.
- [x] Add synthetic `tests/test_r313a_host_private_copy.py`, CI triggers, [operator guide](docs/R313A-HOST-PRIVATE-MIGRATION.md) and explicitly noninstallable `releases/candidates/r313a-host-private-only.json`. Existing R3.12 real send remains hard Off; release manifest unchanged.
- [x] **Owner acceptance PASS (2026-10-30, OMEN/OpenClawLab):** after `next` merge, operator ran `python3 scripts/report_r313a_host.py` and `--private-copy`. Fixed root/private queue verified, pause `not_paused`, legacy schema `match`, additive R3 schema `absent`, separate owner settings `absent_off`, source/unit review blockers `none`; effective publisher service/timer both `reviewed_shape`. Private copy migration `PASS`, history preserved `True`, simulated crash rollback `True`, idempotent `True`, 22 historical send attempts, 0 uncertain states, temporary copy deleted. No installed schema, executable, settings, units, public send, or release changes; R3 cutover remains **NO**. This is operator-provided point-in-time evidence, not fresh on-host inspection by GitHub.
- [ ] **Next R3.13b:** define/test production additive migration and code-only rollback contracts, independently gated owner R3 manual/auto controls (default Off), installed publisher executable/source integrity attestation, and explicit versioned rollout checklist. Still no live schema DDL, installed R3 permission/UI, publisher R3 send branch, or cutover until separately approved.
- [ ] R2 G1 remains pending naturally scheduled source-linked decision.

---

## R3.12 source checkpoint: disabled single-publisher queue adapter and fake-credentialed POST

- [x] Add `src/lib/bob/bob_r312_adapter.py` into the **existing** `src/bin/bob-moltbook-publisher` queue selector. Recognize separately sealed R3 proposals so the old Scout-only validator does not falsely mark Bob-authored drafts as corrupt. Preserve the original legacy queue SQL when no additive R3 schema exists; old Scout jobs continue through existing single credentialed publisher path. Malformed R3 schema fails closed.
- [x] **Hard production Off:** `R312_REAL_DISPATCH=False` is a source-level restriction, regardless of legacy `auto_enabled` or synthetic R3 owner settings. R3 jobs are left queued, unattempted, and cannot reach the live Moltbook POST path. No new active publisher/worker or posting permissions. This source change is **not installed on OMEN**.
- [x] Add `src/bob_v08/r312_fake_credentialed.py` and explicit `--r312-fake-credentialed` option on the same publisher executable. Marker-locked private R3 fixture only: original sealed source/owner/friend/pause/queue/rate rules, one atomic R3.10 attempted_at claim, final R3.8 barrier, in-memory fake credential and exact POST-shaped method/path/payload. ACK/challenge/timeout/rejected/unknown outcomes are simulated; no real HTTP or credentials.
- [x] Add `tests/test_r312_disabled_adapter.py`: actual publisher `publisher_step()` with R3 and approved v0.7 Scout jobs side by side under fake network, actual publisher CLI subprocess fake-credentialed path, default Off, malformed schema, fake credential enforcement, late pause, competition, crash and uncertain no-replay. Include CI trigger and [R3.12 guide](docs/R312-DISABLED-PUBLISHER-ADAPTER.md).
- [x] Create `releases/candidates/r312-adapter-off.json` as explicitly **noninstallable** source metadata. `releases/current.json` remains `v0.8.0-shadow4`; no live migration, Windows/WSL startup, credential or service change.
- [ ] **R3.13 next:** authenticated installed-source and owner-setting contract, additive live-schema migration rehearsed in a private copy, and a reviewed real publisher R3 send branch with final after-intent barrier. Plan a separately authorized staged install, canary, WSL reboot/rollback and no-duplicate recovery before any live R3 posting.
- [ ] **R2 G1 remains pending:** naturally timer-driven source-linked model decision from a fresh Scout selection.

---

## R3.11 single-publisher executable inert rehearsal (source-only)

- [x] Add `r311_inert_entry.py`: strictly marker/private-path-bound R3.3 fixture plus exact sealed Bob draft/action descriptor. Reuse R3.10 two-pass checked `BEGIN IMMEDIATE` durable claim; then recheck source/owner/friend/pause limits and use only R3.8 **in-memory fake sink**, with no Moltbook POST or API token access.
- [x] Add *two explicit inert subcommands* to the **existing** `src/bin/bob-moltbook-publisher` executable, `--r311-inert-rehearsal` and `--r311-inert-recover`. Normal `publisher_step()` remains byte-for-byte unchanged compared with `next` before this phase; no second credentialed publisher or new service unit is created. Missing/Off R3 owner settings always deny, even with v0.7 auto posting enabled.
- [x] Add `tests/test_r311_inert_entrypoint.py` to run the **real publisher CLI subprocess** with isolated HOME and private synthetic DB/source files. Verify fake ACK, challenge, timeout, competing processes, exact original text/seal, source rejection, default Off, owner revocation, post-claim crash and restart uncertainty without resend, and metadata-only stdout. CI trigger added.
- [x] Record `releases/candidates/r311-inert-only.json` as **noninstallable**, not referenced by `releases/current.json`. [R3.11 guide](docs/R311-INERT-PUBLISHER-ENTRYPOINT.md) states `dispatch_authorized:false`, `acted:false`, no live host changes or permissions.
- [ ] **R3.12 next:** a separate reviewed production adapter and locked-down, disabled-by-default publisher integration, end-to-end fake-credentialed POST within an isolated test host, migration/rollback and true owner consent. Do not wire R3 comments into the deployed posting path or turn on R3 auto merely because source tests pass.
- [ ] **R2 G1 separately pending:** naturally timer-driven OpenClaw decision from a new verified Scout post.

---

## R3.10 implemented: one-queue atomic claim, source-only and default Off

- [x] Add `src/bob_v08/r310_atomic_claim_lab.py`, a **marked synthetic fixture only** single-publisher claim rehearsal. Source root (`scout`) and pause marker (`paused`) are derived from the verified private fixture directory, never passed by a model. R3.9 two-pass source/permission/GET review runs read-only; it explicitly does **not** authorize a send.
- [x] After the R3.9 preflight, acquire `BEGIN IMMEDIATE` on the **same legacy-shaped `publish_jobs` ledger**. Revalidate exact source pin, independent Bob draft seal/fingerprint, owner `r3_comment_dial`, separate `r3_auto_enabled` and `r3_auto_since`, v0.7 `auto_enabled` (for auto only), explicit sealed Bob owner approval (manual), friend protection, current pause, manual-first queue, source freshness, prior attempted/uncertain targets and v0.7 budgets. Atomically update `publish_jobs` to `sending_simulated` with `attempted_at`, `r3_proposals` to `intent_simulated`, and one audit event, all with guarded CAS. An SQL failure rolls back the **entire** write.
- [x] Test `tests/test_r310_atomic_claim.py`: default Off even with legacy auto enabled, manual exact-seal approval and revocation, auto opt-in revocation, competing legacy manual priority, same-target prior attempts, resealed source changes, new friend/pause, failure during audit transaction, two concurrent workers, stale GET clock, post-intent pause irreversibly locking the attempt, and process restart no-retry. All calls use mocked GET and in-memory clocks, with no live HTTP or credentialed dispatch.
- [x] **Explicitly NO real send authorization:** `claimed_simulated` includes `dispatch_authorized=False`, `acted=False`. The code does not call or modify `src/bin/bob-moltbook-publisher`, any real SQLite DB, installed unit, API token, release manifest or actual Moltbook POST. The `r3_auto_enabled` flag is **on only in disposable test fixtures**, not installed production.
- [ ] **R3.11 next:** design the additive publisher integration patch and versioned disabled-by-default release candidate, while retaining the old Scout validation path and one credentialed sender. Require independent owner opt-in/approval and a final source/pause check after durable intent; rehearse actual publisher entrypoint via an inert transport in an isolated checkout before any deployment. External source bytes/pause markers cannot be atomically locked together with SQLite across a real network POST.
- [ ] **R2 G1 independently pending:** naturally scheduled, source-linked OpenClaw decision on fresh verified Scout evidence.

---

## R3.9 engineering checkpoint: read-only publisher admission review and pinned HTTPS GET

- [x] Add `src/bob_v08/r39_publisher_review.py`, a future publisher-side **read-only** admission contract. It consumes an existing SQLite connection, verifies the original saved Scout feed/report with R3.4, checks the R3.6 independent Bob-authored proposal seal, requires the exact queued unattempted `publish_jobs` row, rejects any old Scout decision collision or previously attempted target, and uses **the existing v0.7 budget/spacing evaluator**. No queue insertion, state change, credential lookup, POST, or second dispatcher.
- [x] Read owner-controlled `publish_settings.r3_comment_dial`, independent `r3_auto_enabled` and `r3_auto_since`, and existing `auto_enabled` **directly** from the shared queue. Missing/Off/corrupt R3 consent blocks new Bob automatic comments even though v0.7 automatic commenting is enabled. Manual mode independently requires exact `r3_owner_approvals` for Bob's own draft seal. The original Scout approval never authorizes Bob's different words.
- [x] Add a tightly bounded, **GET-only** public preflight client using fixed `www.moltbook.com` HTTPS host, exact UUID path, six-second timeout, no cookies/bearer headers, no redirects, 64 KiB response cap, and exact matching post ID/author with deleted-post refusal. Test responses are locally mocked; **no actual Moltbook requests are performed in CI**.
- [x] Bracket the GET with two saved-source/owner/queue/friend/pause/rate checks. A changed owner dial, friend status, feed, limit, pause marker or queue position fails closed. Even a positive result only returns `status=reviewed`, `dispatch_authorized=False`, `acted=False`. Add `tests/test_r39_publisher_review.py` and CI trigger for spoofed targets, redirects, bad payload, permissions, stale clocks, friend/queue/source mutation and no writes.
- [ ] **Still NOT integrated:** this module is not imported or called by the installed v0.7 credentialed publisher. It has no transactional pre-POST claim, does not itself authenticate the caller-supplied SQLite/source/pause roots, and does not assert WSL reboot safety. It does not install R3 consent UI or change deployed units, credentials, release manifests or post permissions.
- [ ] **R3.10 next:** design an explicitly disabled-by-default, publisher-owned R3 admission/claim extension with a trusted fixed source-root and owner configuration, transactionally sealed Bob draft, manual priority, exact live GET and revalidation immediately before the **existing single** credentialed POST. Rehearse migration/rollback and verify default Off under a fully offline fake publisher. Only an separately approved release/owner cutover may permit actual R3 publication.
- [ ] **R2 G1 remains separate:** verify one naturally timer-triggered source-linked Shadow4 OpenClaw decision; no forced Scout replay.

---

## R3.8 source increment: inert publication lifecycle and effective systemd review

- [x] Add `src/bob_v08/r38_dispatch_lab.py`: only the existing marked private synthetic R3.3 SQLite fixture and a typed `InertSink` can be used. The R3.7 trusted gate atomically records `sending_simulated` and legacy-shaped `attempted_at`, followed by a fresh owner/friend/source/pause/budget barrier and one in-memory fake transport receipt. ACK, challenge, malformed response, failure and timeout outcomes are all explicitly **simulated**; no Moltbook API, credentials or real POST. The record always retains the consumed attempted send.
- [x] Add restart recovery `recover_after_restart()`: convert a valid interrupted synthetic intent to irreversible uncertainty; never auto-replay, restore old queue bytes, or modify older legacy publication/verification records. Block corrupt in-flight synthetic records for manual inspection.
- [x] Test concurrency, crash before/after fake send, failed receipt transaction, non-acknowledged challenge, retry after restart, owner/friend/pause/budget/source revocation, unexpected fake transport and unknown legacy history in `tests/test_r38_dispatch_recovery.py`.
- [x] Add `scripts/report_r38_effective_units.py` plus focused tests: inspect only fixed `bob-moltbook-publisher.service/.timer` via read-only systemd `cat`, check effective ExecStart resets, oneshot shape, timer target/cadence, unexpected additional commands/restart behavior and drop-in counts. Output never includes raw environment, paths or arguments; **cutover_authorized: false**.
- [x] **R3.8 owner effective-unit checkpoint accepted (2026-10-30):** owner ran the read-only effective-unit audit from OpenClawLab and reported `effective service: reviewed_shape`, `effective timer: reviewed_shape`, `service dropins: 0`, `timer dropins: 0`, `environment declarations: 1`, `review blockers: none`, `R3 cutover authorized: NO`. This is a **point-in-time sanitized effective-unit shape check**, not proof of binary integrity, Windows/WSL reboot continuity, real publishing safety, or authorization of R3 actions. No live unit changes were made.
- [ ] **R3.9 next:** review actual host effective unit findings and design a *publisher-side* opt-in and Bob-origin admission path without cloning the credentialed publisher. Prove real fixed-host GET and final pause consistency under isolated no-network tests, then separately review a versioned and explicitly authorized installation/rollback. No live R3 publisher migration or auto consent has been granted.
- [ ] **R2 G1 still open:** naturally scheduled model decision on a fresh verified Scout source, not merely successful oneshot execution.

---

## R3.7 implementation checkpoint: publisher-owned trust boundary (offline simulation)

- [x] Build `src/bob_v08/r37_trusted_gate_lab.py`: a **marked synthetic fixture only** two-pass host-source/permission/queue verification gate that ties the R3.6 source classifier to the existing `r3_unified` transaction. Read authenticated-by-file Scout bytes, exact Bob-authored seal, queued unattempted job, owner `r3_comment_dial`, **both** `auto_enabled` and `r3_auto_enabled`, opt-in date, separate manual approval, legacy limits, manual priority and duplicate/uncertain history. No action policy from the model grants authority.
- [x] Add a conservative saved-friend guard using the exact verified Scout feed and existing `bob_friends` table. Missing/damaged table, tagged friend batch, saved friend target and changed batch refuse auto mode; no implicit friendship bypass when extra Bob autonomy is enabled.
- [x] Recheck the owner flags, feed integrity, queue, friend table, budget and pause marker **after** a strictly target-and-author-matching GET *fixture*, without holding a SQLite write lock across the simulated GET. A matching GET alone is not authorization. Only the existing offline `UnifiedLab.simulated_pre_send` may record `sending_simulated`; every returned result has `acted=False`, `dispatch_authorized=False`.
- [x] Add `tests/test_r37_trusted_gate.py` to verify revoked owner consent, changed friend state, pause activation, changed rate limits, wrong/missing/deleted GET identity, stale clock, concurrent legacy priority, attempted/uncertain target history and private manual seal. CI path updated.
- [ ] **R3.7 live adapter NOT built:** the GET function and clock are host-test callbacks, not a verified installed HTTPS client; `UnifiedLab` is marker-locked synthetic SQLite, not the production queue. There is no installed v0.7 publisher change, new consent setting UI, credential or HTTP POST. A real host-side adapter needs exact service/root ownership, secure GET parsing, final pause recheck, source/file consistency and one publisher-owned pre-POST CAS.
- [ ] **R3.8 next:** build independent isolated effective-unit template/override review and a production-like publisher dispatch rehearsal using inert transport and crash/reboot hooks. No release/update or production permissions without explicit owner approval.
- [ ] **R2 G1 still pending:** a naturally timed source-linked model decision, distinct from the verified no-event timer run.

---

## R3.6 implementation: read-only real-host readiness audit and draft-origin contract

- [x] Add `scripts/report_r36_host_readiness.py`: a single compact owner-run report that reads only fixed allowlisted systemd **unit states** and existing SQLite queue schema/metadata in `mode=ro`. Includes publisher service/timer, startup reconcile, shadow and inert candidate, system legacy Scout, exact legacy table shape, validated policy, pause, attempted and uncertain counts. Every report explicitly says **cutover_authorized: false**. Expanded `--json` remains sanitized.
- [x] Add `src/bob_v08/r36_admission_contract.py`: verify saved Scout bytes using the reviewed R3.4 source pin, distinguish unmodified v0.7 Scout draft from an independently sealed Bob-authored comment linked to R3 proposal rows. Any unknown/different/attempted job refuses, and **both classifications forbid dispatch**. Existing publisher and deployed release remain unchanged.
- [x] Add isolated tests `tests/test_r36_host_readiness.py` and CI triggers for malformed/missing queue schema, symlinks, uncertain history counts, fake active candidate, secret-text sanitization, tampered feed, unknown seal, and no new writes.
- [x] **R3.6 owner host-readiness snapshot accepted (2026-10-30):** owner ran `cd ~/bob-next && git pull --ff-only && python3 scripts/report_r36_host_readiness.py`. Observed: legacy publisher timer **active**, publisher service **inactive** (normal between oneshot runs), shadow timer **active**, startup reconciliation timer **active**, candidate timer **inactive**, legacy system Scout timer **inactive**, legacy queue schema **match**, queue policy **valid**, global pause **not_paused**, existing v0.7 auto comments **enabled**, **22 historical attempts**, **0 delivery states requiring review**, `baseline consistency: observed`, `review blockers: none`, **`cutover authorized: NO`**. This is a point-in-time, sanitized read-only readiness snapshot, **not** a live publication count, sustained service/reboot assurance, or new v0.8 publisher authorization.
- [ ] **Next R3.7:** integrate authenticated owner settings, source roots and fresh friend/GET/pause evidence in one publisher-owned pre-send gate; inspect effective installed unit/drop-ins and restart behavior, rehearse exact publisher compatibility and maintain code-only rollback. No live installs, Moltbook sends, or new automatic permissions without explicit review.
- [ ] **R2 G1 still open:** naturally timer-driven source-linked OpenClaw decision against a new verified Scout selection.

---

## R3.5 engineering checkpoint: additive migration and reboot rehearsal

- [x] Implement `r35_migration_lab.py` for **private marked synthetic SQLite** only: verify essential legacy queue schema, create R3 proposal/owner/audit metadata tables atomically, preserve all decisions/attempts/uncertain jobs, reject schema drift and unknown versions, prove idempotent retry and rollback on simulated power loss.
- [x] Add a pure reboot ownership evaluator: reject overlapping legacy/candidate timers and workers, unknown startup reconciliation, candidate auto-resume after boot, and silent re-enable from a quiesced state. Keep history intact on code-only rollback, including new simulated uncertain attempts.
- [x] Add `scripts/rehearse_r35_deployment.py` for one-command disposable template-shape and migration report, plus `tests/test_r35_migration_recovery.py` and CI triggers. No systemctl, credentialed Moltbook client, actual publication, release manifest change or OMEN install.
- [ ] **R3.6 next:** compare a sanitized, read-only installed unit/queue topology with the rehearsal model, design and test trusted publisher-side Bob-draft admission and permissions against one credentialed writer, and rehearse genuine versioned service ownership without touching live state. Any real schema migration and cutover require explicit approval, backup integrity and safe unknown-send recovery.
- [ ] **R2 remains independently open:** natural timer-driven source-linked model decision; prior scheduled no-event execution and manual OpenClaw decision both remain valid evidence.

---

## R3.4 completed source increment: pinned Scout evidence and dry-run service ownership

- [x] Add `r3_cutover_rehearsal.py`: source-bound `read_observation()` verification before propose, queue and simulated intent; pin snapshot, post and legacy Scout approval hashes; terminally hold changed saved evidence without consuming a synthetic attempt.
- [x] Make R3.3 `r3_unified.py` reread the persisted lab-only `r3_comment_dial` within queue/intent transactions. An Off/missing dial blocks, Propose cannot be upgraded to Auto, and revocation after queue stops simulated sending. Preserve distinct human approval of Bob-authored comment text.
- [x] Model pure one-publisher stages, explicit owner authorization, old/new worker drain, shadow timer preservation, safe rollback with immutable attempted/uncertain history; provide `scripts/rehearse_r3_cutover.py` denial-and-rollback report. Focused offline `tests/test_r3_cutover_rehearsal.py` and CI triggers cover source tamper, disabled/revoked settings, simulated GET staleness, overlap and nonboolean gates. **No host actions or release install.**
- [ ] **R3.5 next:** replace synthetic truth placeholders with reviewed host-side trust *contracts*, rehearse exact installed unit ownership and crash/reboot behavior using inert fixture templates, and prove additive single-publisher migration/rollback with no stale SQLite state restore. Do not treat the R3.3 caller-supplied `Proof`, `Policy` or pause boolean as live authorization; real friend/GET checks and actual owner settings remain unimplemented.
- [ ] **R2 still pending separately:** naturally timer-driven OpenClaw decision against a new verified saved Scout selection; no force replay and no premature R2 G1 closure.

---

## R3.3 implementation checkpoint: one simulated publisher ledger

- [x] Add `src/bob_v08/r3_unified.py`, joining the R3.1 unique reservation and R3.2 legacy queue protections into **one** marked synthetic database. A new Bob-generated comment gets a unique source-bound seal and proposal record, never inherits the hash or manual approval for an older v0.7 Scout draft.
- [x] Enforce separate manual approval vs auto flags, v0.8 Off/Propose/Auto policy, dated auto opt-in, manual-first/FIFO queue, current legacy rate policy, trusted-placeholder preflight and friend protection, and atomic synthetic `sending/attempted_at` CAS. Ambiguous outcomes remain locked; no credentialed publisher integrated.
- [x] Test concurrent workers, altered text, revocation after queue, legacy queue collisions, UTC budgets/spacing, stale preflight, SQL crash rollback, uncertain/restart state and refusal of live DB paths in `tests/test_r3_unified.py`. Trigger CI on these tests.
- [ ] **R3.4 next:** build an isolated host-trust adapter and publish-control migration/restart/rollback rehearsal with exact current unit ownership, signed/verified Scout provenance and real **one-publisher** source validation; never substitute a synthetic preflight/owner-consent argument for actual host authority. Preserve historical attempts and make rollback code-only after new database events.
- [ ] **R2 G1 still pending:** naturally timer-driven OpenClaw decision on a new verified Scout selection; a successful no-event scheduled service alone is insufficient.

---

## R3.2 legacy compatibility checkpoint (source-only)

- [x] Build isolated `r3_legacy_compat.py` preview against a private marked fixture of actual legacy queue tables. It reuses the real `bob_activity_limits.allowed()` implementation and checks manual-first/FIFO, exact draft+hash, manual approval, auto enabled/owner override, friend clearance, age, duplicate target, same-transaction `attempted_at`, final synthetic audit and irreversible uncertain status.
- [x] Add `tests/test_r3_legacy_compat.py` and CI triggers for manual/auto boundaries, budget exhaustion, pause, altered model payload, malformed history, competing claims and SQLite failure rollback. **All outputs simulated, no live DB, publisher or Moltbook contact.**
- [ ] **R3.3 next:** merge R3.1 reservation concepts with R3.2 v0.7 compatibility into a single publisher-owned cutover contract. Simulate an actual new Bob-authored draft as distinct from the old queued Scout text, real publisher intent-before-POST, expired/uncertain states, rechecking permission after simulated preflight, timer ownership and isolated forward-compatible migration/rollback. No v0.8 real publisher integration, service activation, credential changes or new permission by default.
- [ ] **R2 still open:** a naturally timer-driven source-linked decision is not proven by the 17:30 no-event scheduled service. Keep Shadow4 running on verified Scout sources; do not force replay.

---

## R3.1 engineering checkpoint: transactional reservation and simulated pre-send

- [x] Implement source-only `src/bob_v08/r3_reservations.py`: private lab database with atomic source/target reservation, duplicate lock, conservative budget accounting, independent final recheck, simulated intent recording and irreversible unknown state. No real send/approval/worker integration, no v0.8 outbound permission.
- [x] Add synthetic tests in `tests/test_r3_reservations.py` and CI triggers for two simultaneous claimants, content/source hash drift, policy revocation, UTC rollover, spacing, corrupt clock/settings, crash rollback and no network APIs. This is an engineering fixture, **not a new installed release**.
- [ ] **R3.2 next:** map authoritative existing v0.7 `publish_jobs`, `decisions`, `publish_settings` and publisher's pre-POST `sending/attempted_at` transition into an exact transactional compatibility gate. Avoid duplicate independent ledgers granting competing dispatch authority. Prove manual-first and stale approval handling; preserve uncertain/verification states and no blind retries. Follow with isolated service cutover and rollback rehearsal, then explicitly approved owner acceptance. No running unit or live credential changes during this preparation.
- [ ] **R2 remaining:** allow natural Scout observations to reach the active Shadow4 timer and record one timer-driven source-bound decision before declaring the full G1 representative scheduled-decision gate complete. The successful scheduled no-event service run is not equivalent to a fresh model decision.

---

# Bob 💀 — Project TODO

## Active handoff: v0.8 Shadow4 accepted manually; R2 completion and R3 preparation (2026-10-30)

**Installed host reality (owner-observed):** `v0.8.0-shadow4` is active with a versioned verified archive and separate `bob-v08-shadow.timer` user timer. A real OpenClaw main-agent `bobctl shadow-once` returned `state: shadow_decision`, `action: comment`, `policy: deny`, `policy_reason: action_off`, `acted: false` for verified Scout source `20261030T200610Z`, post `a9ccf436-c5d5-4849-af92-843670ab8271`. The authenticated Shadow Now page recorded observe, decision and policy events; historical earlier model-validation errors remain visible and are not new failures. The existing v0.7 Scout/publisher, permissions and queues were not modified by this acceptance.

**Updated timer evidence (owner-verified 2026-10-30):** `systemctl --user list-timers --all bob-v08-shadow.timer` reported `LAST Fri 2026-10-30 17:30:05 PDT` and `NEXT Fri 2026-10-30 17:51:12 PDT`. `systemctl --user show bob-v08-shadow.service -p Result -p ExecMainStartTimestamp -p ExecMainExitTimestamp` reported `Result=success`, with start and exit at **17:30:05 PDT**. This proves **the timer triggered the service and the service completed successfully**. It does **not** establish whether the tick evaluated a fresh Scout source: the shadow CLI exits 0 for `no_new_verified_sources`, for a valid decision, and for recorded model-invalid results. Check the bounded journal outcome before claiming a timer-driven model decision. Dashboard still shows `Next reported run: not reported` because it queries only the realtime property of a monotonic timer.

### TODO: accurate Shadow Now scheduled-time display

- [ ] **R2-UI-SCHEDULE** Fix `/v08/now` to display the real next run for Bob's **monotonic** `OnActiveSec` / `OnUnitInactiveSec` user timer. Current `src/bob_v08/inspect.py:timer_observation()` requests only `NextElapseUSecRealtime`; this may be absent for monotonic timers despite a valid `systemctl --user list-timers` NEXT value. Prefer a documented, version-compatible structured systemd property including monotonic schedule and boot-time conversion, or tightly scoped read-only `list-timers` parsing. Never invent or infer NEXT from budget/rate-limit eligibility.
- [ ] Add offline synthetic tests for monotonic and calendar timers, inactive/missing/failed services, timezone changes, no next run, and systemd field-format variations; bound subprocess timeouts, output size, and parsed display. UI is **read-only** and must not start timers or add new routes. Batch with a later reviewed UI release; **no emergency Shadow4 hotfix** solely for display.
- [x] **G1 scheduled service execution confirmed:** 17:30:05 PDT service invocation completed with `Result=success`; the timer also reported its previous and next run. This establishes the user-systemd scheduling and execution path.
- [x] **G1 scheduled 17:30 no-event interval inspected:** owner ran a read-only SQLite query across UTC `2026-10-31T00:29:00`–`00:31:00` and found **0 shadow events**. This confirms no new source-linked observe/decision/error event in that period; likely the source backlog was exhausted. The service did run successfully, but exact no-op reason is **not proven** without the process result output. Keep naturally collecting evidence on later Scout selections; no further synthetic replay needed.
- [ ] **G1 future scheduled decision:** when new verified Scout sources naturally arrive, classify at least one successful source-linked timer-driven decision. R2 is functionally useful, but full G1 decision-cadence acceptance remains open until then. No forced tests or database resets.
- [x] **G1 MD1 one-shot live smoke accepted with interpretation caveats:** on 2026-10-30 PDT, owner ran `bobctl shadow-experience`, confirmed `ASK-BOB`, and Bob's actual OpenClaw `main` agent returned an evidence-bounded private summary of six verified saved Scout selections. He reported `no_recorded_attempt`, `publisher_queued`, and `publisher_failed` labels, consistently caveated visibility as `unknown` or `not_rechecked`, and claimed no confirmed public replies **within the supplied digest**. This demonstrates functioning isolated read-only context, **not permanent memory, public publication proof, or full historical recall**. One output over-interpreted `publisher_failed` as a real network attempt without an `attempted_at` check; several observed third-party posts were described ambiguously as Bob's posts, and source-run IDs were omitted in favor of post IDs. Output had character-encoding artifacts (`Heres`, ``). These are accuracy/presentation follow-ups, not grounds to discard the working one-shot.
- [ ] **MD1 attribution/attempt semantics:** in future bundled R2/R3 UI and digest polish, include an explicit `observed_third_party_post` label, distinguish `publisher_failed_pre_send` from `attempted_send_failed_or_uncertain` using safely verified `attempted_at`, keep queue state separate from any actual POST, and require the agent to include both `source_run` and `post_id` when referencing examples. Review raw output UTF-8/locale handling without logging private text or widening tool permissions. Do not retroactively claim no published activity *outside* the six-selection history scope.
- [ ] **MD1 extension later:** fresh normal Gateway/CH1 chat can only be called experience-aware after an opt-in safe context bridge is independently proven; the current `shadow-experience` session is isolated and does not write `MEMORY.md` or PM2.
- [ ] After representative natural ticks, at least one scheduled tick, and bounded experience validation, record R2/G1 acceptance. Only then advance to the **R3 guarded cutover engineering gate**: exact v0.7 permission/queue parity, one credentialed publisher, atomic reservation and pre-send recheck, failure/rollback rehearsals, and explicit owner authorization before any new writes. `main` remains the stable reviewed baseline; source development continues on `next` via clean `~/bob-next`.

**R3.0 engineering inventory:** [read-only cutover map and safety gates](docs/R3-CUTOVER-INVENTORY.md). The source-only `scripts/report_r3_cutover_inventory.py` reports allowlisted unit states, bounded non-secret queue counts and actual validated policy settings without changing production. Synthetic tests in `tests/test_r3_cutover_inventory.py` cover isolation, unsafe names, secrets and invalid settings. **Not installed; do not consider this permission to cut over**. Source engineering can proceed without stopping the existing publisher or enabling v0.8 writes.

**Do not do:** reset/erase shadow events, automatically replay failed Scout sources, silently enable v0.8 publishing, or treat the planned NEXT time as a completed run.

---


> **Historical planning note (superseded by the active handoff above):** [Bob v0.8 roadmap](docs/ROADMAP-v0.8.md) is now the proposed primary engineering plan. It packages the work into **four operator-facing upgrades**: R1 safe updater, R2 full shadow build and experience digest, R3 guarded cutover, R4 autonomous social features and consolidated UI. This is planning only; no release manifest, production files, services, permissions, or databases have changed.
>
> **Historical v0.7 baseline:** the previously accepted release was **`v0.7.7-fm41-social1`**; the host has since installed **`v0.8.0-shadow4`**. Standalone FM4.2 / FM4.3 / FM5 and MD1 engineering are **paused and folded into v0.8**, retaining their evidence/approval/security requirements. CH1 real-agent LAN Chat remains planned after the refactor and HTTPS. The former v0.7 handoff follows unchanged below for traceability; its “next FM4.2” language is superseded by the v0.8 plan.

---

## Historical v0.7 handoff (retained, not active implementation order)

**Last reviewed:** October 30, 2026 (America/Los_Angeles)  
**Canonical repo:** `merberg-ai/bob-openclaw-moltbook`, `main`  
**Operator-tested deployed baseline:** `v0.7.7-fm41-social1` (FM4.1 Social Memory Timeline operator-tested and accepted October 30, 2026; PR #49, 599 offline tests passed)  
**Status:** FM1–FM3 complete, **FM4.1 operator-accepted**. **Next Friends engineering phase: FM4.2** revisable social impressions and owner corrections, then separately opted-in FM4.3 recall. FM5 remains planned and unimplemented; actual Moltbook following needs separate FM5.2 authorization. MD1 and CH1 are independently planned, not yet implemented.  
**Deployment contract:** future implementation through `bobctl update` with verified private backup, installed-module import checks, reversible release and short live acceptance. A Git commit alone never changes the running Activity Manager.

## Current development streams

| Stream | Progress | Next |
| --- | --- | --- |
| Personality (PM1) and Memory (PM2) | Implemented / operator-tested | Maintain existing explicit memory recall and owner review boundaries |
| **Friends (FM1–FM4.1)** | **FM4.1 installed and operator-accepted** (`v0.7.7-fm41-social1`, PR #49, 599 offline tests) | **Next: FM4.2** evolving, source-linked per-agent impressions, revisions and owner corrections; then FM4.3 optional social recall. [FM4.1 accepted release](docs/V077-FM41-SOCIAL-MEMORY.md). No Moltbook following until separately authorized FM5.2. |
| **Operations Center: activity / automation / console / inactivity investigation** | **OC0–OC4.1 complete, installed and operator-accepted** | Working baseline `v0.7.6-oc41-polish1` (PR #47, 591 CI tests). Remains maintained; FM4 has since resumed. [OC4.1 release notes](docs/V076-OC41-DIAGNOSTIC-POLISH.md). |
| Logs & Diagnostics | Installed / operator-tested | Reuse existing bounded redacted journal, job, event and checkpoint collectors rather than duplicate raw logging |
| **Direct Bob Chat (CH1)** | **Planned here, not started** | Gateway compatibility spike, then authenticated LAN chat UI |
| Fresh-host installer | Deferred | Keep current WSL/Windows startup, services and updater intact |

## Completed priority: Bob Operations Center, before FM4

**Owner request (Oct 30, 2026):** The Overview gauges show 2/10 comment attempts, 0/6 automatic, 0/4 originals and six queued manual comments, but reveal too little about the reason for inactivity. Owner wants a compact live-truthful **“Bob right now”** card directly below gauges, a centralized **Automation** section with controls/status/last action/next actual run for automatable features, a terminal-styled **read-only sanitized Console** showing useful Ollama/OpenClaw/Gateway/system/worker diagnostics, and a reliable one-view **“Why no activity?”** explanation. All pages must be compact and mobile-friendly.

**Implementation status:** **OC0 through OC4.1 operator-accepted on the OMEN.** The publication fix `v0.7.6-pubfix-manual1`, OC4 investigator and OC4.1 `v0.7.6-oc41-polish1` have been installed in sequence, and the operator reports OC4.1 works as expected (October 30, 2026). This closes the scoped Operations Center roadmap; see [OC4.1 release notes](docs/V076-OC41-DIAGNOSTIC-POLISH.md). No new publishing authority was added. **Next separately planned work: MD1 Moltbook Experience Digest** for verified history in real Gateway/CH1 conversations, not yet implemented. Build from existing `bob_overview`, `bob_live_status`, `bob_job_tracking`, `bob_diagnostic_logs`, `bob_activity_limits`; preserve queue and publishing protections. Only add automation toggles through exact, independently authorized handlers. **Original posts remain owner-requested/approved** unless separately redesigned; empty original budget is not proof of failure. “Earliest possible next” is a rate-limit eligibility clock, not a real scheduled run.

**User preference:** no sprawling command-marathon; one `bobctl update` per small code release, with CI first and a concise mobile/LAN acceptance. Keep FM4/FM5 paused until the Operations Center and other operator-reported issues are addressed.

---
## Friends work: paused after final FM3 acceptance

**Passed October 30, 2026:** The operator tested `v0.7.5-fm32d-focus1` through the normal `bobctl update` and confirmed it works as expected. This closes FM3.2d and FM3 as scoped. PR [#38](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/38) merged to main, with **537 passing synthetic offline tests**. This is a documentation acceptance checkpoint, **not a new code release**. Keep `releases/current.json` unchanged until an actual next software release.

**Priority cleared / FM4.1 PASS:** The operator accepted OC0–OC4.1, resumed FM4 and confirmed the installed read-only Social Memory Timeline works as expected. This acceptance does **not** automatically grant FM4.2/4.3, external follows, chat memory integration or FM5 autonomy. Continue in small independently accepted releases.

**FM4.1 PASSED; resume at FM4.2:** the accepted Social Memory Timeline displays source-verifiable saved observations, Bob's tentative ideas and owner-reviewed records, without writing PM2 memories, `SOUL.md`, FM1 notes or sending Moltbook actions. Next implement revisable impressions with correction and audit, then independently opt-in FM4.3 recall. FM5.1 autonomous discovery and FM5.2 separately authorized platform follow/unfollow remain future work. Full architecture and handoff: [Friends roadmap](docs/FRIENDS-ROADMAP-AND-HANDOFF.md).

**Future versioning:** last operator-confirmed installed release is **`v0.7.7-fm41-social1`**, accepted October 30, 2026. The next application release (FM4.2 unless superseded) must use exactly `from: v0.7.7-fm41-social1`; preserve guarded `bobctl update`, backups and rollback. **This documentation checkpoint does not change `releases/current.json` or install software.**

---

The earlier Scout `ModuleNotFoundError: bob_publish_common` was repaired through `v0.7.5-scout-importfix1`; the operator installed the shared helper and reset the historical failed status. Separately verify a later **timer-driven complete Scout run** when convenient. Don't restart services simply to satisfy this plan.

---

## MD1: Moltbook Experience Digest for Bob's actual Gateway conversations (PLANNED)

**Identified October 30, 2026:** In a real OpenClaw Gateway chat, Bob said he had seen multiple `moltbook-scout` sessions but described Moltbook as mostly “standby mode,” with little actual learning. Repository inspection explains a **context gap**, not confirmed intentional fabrication: scheduled Scout runs use separate `openclaw agent --session-key moltbook-scout-<run>` sessions and save verified posts, WHY selection, drafts and outcome metadata in private Scout files/SQLite. PM2.3 read-only contextual recall **only** enriches Scout and original drafting prompts; it does **not** supply this evidence to arbitrary Gateway chat. Bob can plausibly know sessions existed but cannot reliably summarize their actual history from normal chat context. His statement about few interactions may also be correct; do not infer a genuine conversation or learning outcome from a queued draft.

**Owner goal:** When asked in Gateway or the future LAN CH1 Chat, “What have you experienced or learned on Moltbook?”, Bob should answer with **verifiable sources and honest limitations**, not an invented personal history. Proposed **MD1: Moltbook Experience Digest** is a bounded, read-only, local bridge covering:
- **MD1.0, contract/inventory:** identify actual active OpenClaw main-agent workspace, Gateway session/tool boundaries, authentic Scout run data, publisher outcomes, incoming reply records, FM3 tentative interests and owner-reviewed memories; distinguish a saved draft, an attempted send, confirmed publication, and actually observed public replies. Never conflate generated text with learned memory.
- **MD1.1, private verified digest:** produce a bounded recent activity summary with last Scout selection/rationale, safely verified public post IDs and UTC times, manual/automatic publication status, received replies, the owner's reviewed tentative interests, and what remains uncertain. Read from sealed existing data, not raw untrusted third-party instructions; no secrets, private owner notes, raw prompts, or arbitrary model-supplied paths. Carry explicit timestamps/source links and stale/unknown labels.
- **MD1.2, conversation bridge:** let the real OpenClaw Bob agent access this digest during appropriately **opted-in** Gateway/CH1 conversations by a deliberately bounded, authenticated mechanism. Verify it works in a **fresh Gateway chat session** and in private-LAN CH1. Do not inject into public posts, grant new tools, publish, change agent persona, or automatically update memory.
- **MD1.3, voluntary growth:** allow Bob to propose new tentative interests and revisions sourced from his digest/experience; owner review/approval and auditable versions stay explicit. Actual long-term social-memory integration belongs with FM4 and requires separate authorization and retention/privacy decisions.

**Acceptance:** ask Bob what he has actually done on Moltbook, confirm an answer points to real saved Scout/published/reply evidence, states the distinction between reading and interacting, and admits missing data. Test zero-data/missing-data, compromised hashes, stale sessions, no publication, source tampering, untrusted feed injection, separate personalities, and privacy leaks. A model's confident claim alone never becomes source evidence.

**Priority/order:** Complete **OC4** first (including any already pending publication-fix operator acceptance). MD1 should be scoped together with the separately tracked **CH1 Direct Bob Chat** and future **FM4.1**, but **not** silently treated as a feature already shipped; FM4 and FM5 stay paused until the operator explicitly resumes them.

---

## CH1: Talk directly to the real OpenClaw agent Bob

### User story / non-negotiable requirement

> From my phone or laptop on the secure private LAN, open the existing authenticated Bob Activity Manager, select **Chat**, type “Bob, what have you been up to on Moltbook?” or “Which agents interest you and why?”, and converse with **Bob the existing OpenClaw agent** using his personality and available memory. Not an Ollama-only imitation.

**LAN access is a hard requirement.** The chat must work via the same trusted-LAN Activity Manager URL and login already used on the OMEN (previously tested at `http://192.168.1.24:18790`), without visiting the OpenClaw Gateway UI separately, connecting a browser to Gateway port `18789`, exposing new Windows inbound ports or requiring internet/public hosting. Test from a second LAN device and Android/mobile browser.

**Hard boundary:** direct interaction with the OpenClaw agent **does not** confer extra rights to publish, DM, follow, vote, execute commands or modify settings. Effective OpenClaw tools/profile and existing Moltbook host-only publisher authorization must remain in charge; the dashboard cannot silently convert a chat message into a publication job.

### Proposed architecture

```text
Trusted LAN browser (phone or laptop)
  │
  │ same origin + existing Activity Manager authentication
  │ HTTPS recommended for production (protect password and chat text)
  ▼
Bob Activity Manager   [WSL2; LAN-accessible existing port 18790]
  /chat  : mobile-first, authenticated UI
  /api/chat/* : exact bounded history/send/status/abort handlers
  │
  │ server-side, authenticated, strictly allowlisted chat adapter
  │ single configured Bob agent/session, origin/CSRF/rate checks
  │ no browser-visible Gateway credentials, no arbitrary RPC proxy
  ▼
OpenClaw Gateway WebSocket [127.0.0.1:18789, loopback ONLY]
  │ current, correctly paired/authenticated operator client
  │ chat.history / chat.send / chat.abort and necessary events
  ▼
Existing OpenClaw agent: Bob 💀
  configured SOUL.md / IDENTITY.md, agent workspace & model
  local Ollama qwen3.5:9b as configured provider
```

**LAN feasibility:** already solved at the Activity Manager boundary. The backend is the only Gateway client. **Do not change `gateway.bind` from loopback to LAN**, add a wildcard listener for Gateway, pipe a Gateway token into HTML/JS, embed the privileged Control UI in an iframe, or implement a general WebSocket forward proxy.

OpenClaw documentation (validate against the actual installed version before coding):

- [WebChat](https://docs.openclaw.ai/web/webchat) — Gateway-backed chat uses `chat.history`, `chat.send` and related chat RPCs, rather than calling Ollama directly.
- [Building a Gateway client](https://docs.openclaw.ai/gateway/clients) — operator read/write scopes and device pairing; do **not** invent tokens or edit private `openclaw.json` to mint client credentials.
- [Gateway handshake](https://docs.openclaw.ai/gateway/protocol/handshake) — challenge, protocol negotiation, authenticated connection; exact installed version wins over assumptions.
- [Network exposure](https://docs.openclaw.ai/gateway/security/network-exposure) — loopback Gateway and narrowly controlled proxy/security boundaries.
- [Feature/RPC reference](https://docs.openclaw.ai/web/control-ui/feature-reference) — `chat.abort` and messaging behavior.

### Sessions and authentic Bob personality

- **Default: one persistent, dedicated Activity Manager conversation session attached to Bob's existing main agent.** Choose a documented, installed-version-valid session key in CH1.0; do not invent a hardcoded key yet. A dedicated chat prevents accidental overlap with scheduled Scout, original-post, or Gateway Control UI conversations. A separate explicit “main session” switch may be evaluated **later**, after access checks and owner confirmation.
- Transcript/history should come from **OpenClaw Gateway's own stored chat session**; no duplicate canonical message store and no writing raw conversations into Git or the publication SQLite database. Render only gateway-normalized display text (bounded/paginated), escape it and suppress tool internals by default.
- Bob's configured **OpenClaw** agent persona/workspace should apply. **Important limitation:** the separate PM2 Activity Manager memory DB, friend records, and past Scout jobs are **not guaranteed to be in the OpenClaw chat context by default**. Chatting with the correct agent does *not* automatically give it all data on the dashboard.
- To answer questions such as **“What have you learned from Moltbook?”** accurately, plan an **opt-in, read-only Experience Context** adapter that selects bounded, provenance-validated past Scout reports and curated/approved memory or friend observations. Treat them as low-trust reference data with timestamps and source IDs, not instructions. Distinguish remembered facts, Bob's model opinions, and unsupported inferences. Never dump private relationship notes or entire feeds into a chat prompt by default.
- Do not add a separate assistant personality in the frontend, call Ollama's `/api/chat` directly, or present a model-generated invented activity summary as observed Moltbook history.

### Proposed implementation phases (small independently testable increments)

#### CH1.0: Installed Gateway capability and security preflight (read-only)

- [ ] Inventory actual OpenClaw version and exact working Gateway endpoint, authentication/pairing model, supported chat RPCs, session syntax, allowed operator scopes and event delivery. Do not print or commit auth tokens.
- [ ] Test whether the existing Activity Manager user can connect to loopback Gateway with a correctly paired, explicitly approved *limited* client identity, without broad `operator.admin`, `operator.approvals` or other unrelated methods. If limited client pairing cannot be arranged, **stop** and design an appropriate broker, not a privileged token pasted into browser code.
- [ ] Confirm existing LAN Activity Manager URL, authentication, Origin/Host/CSRF policies, CSP and phone access. Select a same-origin transport: bounded HTTPS requests + polling initially, optional authenticated SSE if practical; **no direct LAN browser connection to Gateway**.
- [ ] Verify read-only session history in a synthetic/isolated test. Never send a real chat message during preflight.

**Gate:** documented compatibility report and approval of the exact minimal bridge. No production config or listener changes.

#### CH1.1: Secure server-side Gateway chat adapter

- [ ] Implement a narrowly scoped localhost adapter with an exact whitelist (`chat.history`, `chat.send`, `chat.abort`, minimal session/status subscription only as required). No generic RPC execution, arbitrary session key, filesystem path, tool approval or channel-send forwarding.
- [ ] Credential handling remains private on WSL host with owner-only permissions, no token in URL, cookies, browser response, logs, API request payloads or exception text. Use supported Gateway bootstrap/device pairing, never hand-roll tokens.
- [ ] Bind the adapter to one validated Bob session with strict message length, history size, concurrency, queue bounds, per-user/IP rate limits, lifecycle timeouts and cancellation. Encode abort against the active run rather than a guessed unrelated session.
- [ ] Preserve existing dashboard authentication and exact Origin/Host + CSRF protections on all chat mutations; `Cache-Control: no-store`. Reject bad/missing auth, external origins, replay/stale requests, oversized messages and Gateway disconnects safely.
- [ ] Avoid service proliferation unless necessary. If a local Node/WS companion process is required because the stdlib Python dashboard has no native WS client, bind it to loopback only, supervise it as a private user service, and document clean rollback.

**Gate:** offline fake-Gateway protocol tests and isolated HTTP auth/CSRF/negative tests; zero additional network exposure and no existing post/queue behavior change.

#### CH1.2: Usable authenticated LAN Chat page

- [ ] Add **Chat 💀** to Activity Manager sidebar/mobile navigation, authenticated `GET /chat`, with conversation bubbles, autoscroll, multiline composer, Send, clear pending/running/idle/error indicators and copyable text.
- [ ] Retrieve bounded recent history and request earlier pages from the Gateway. Show actual Bob messages and preserve conversation on mobile refresh/reconnect. No fake “memory loaded” indicators.
- [ ] Send a text prompt to Bob through OpenClaw and render its live progress. Start with safe polling if simpler; streaming/SSE can follow after reliability is proved. Add Stop only when a validated live run can be aborted safely.
- [ ] Make empty/disconnected/timeout/model-unavailable/restart cases truthful and actionable. Do not duplicate a `chat.send` when the network response is uncertain; use idempotency/session semantics where supported or show an uncertain state and reconcile history.
- [ ] Responsive Android/LAN UX: usable keyboard composer, no sideways overflow, readable code snippets, sensible error notices, no third-party assets/scripts.

**Gate:** authenticated laptop and phone through the **existing** LAN Activity Manager address; Gateway stays loopback-only and unavailable from a second LAN device directly. Chat is still the real Bob agent, not standalone Ollama.

#### CH1.3: Experience-context and trust-aware opinions (separate opt-in)

- [ ] Add a bounded, **read-only** dashboard summary of Bob's verified Scout discussions, recent selected authors, authored WHY fields, approved PM2 memory/observations and any *confirmed* interactions where source and timestamps are available.
- [ ] Offer an explicit UI option **Include Bob's saved Moltbook context**. Its off state must not leak private notes; enabled context is sent as untrusted reference text, not agent instructions or permissions. Prefer owner-approved memories over raw public posts.
- [ ] Let Bob express opinions and changing interests naturally; show source references and the difference between **“from an actual saved Scout run”** and **“my current interpretation”**. No invented post IDs, verified mutual friendships, or claims that a chat has updated long-term social memory.
- [ ] Future integration with **FM4 Social Memory** can permit owner-reviewed memory proposals from conversations, but **never silent memory write or identity mutation** in CH1.

**Gate:** Bob can truthfully answer “Which Moltbook posts did you choose, and why?” from a verified saved snapshot or explicitly say no saved evidence is available. No unapproved public write or memory mutation.

#### CH1.4: Production hardening and optional polish

- [ ] **LAN confidentiality:** existing Basic authentication on plain HTTP is not encrypted. For normal/private chat, prefer **HTTPS on the existing LAN endpoint or a narrowly configured internal HTTPS reverse proxy**; verify phone certificate trust and that credentials/chat aren't exposed in transit. If testing over current trusted-LAN HTTP, label it explicitly as a temporary lower-confidentiality mode; do not imply private LAN == encryption.
- [ ] Verify access from the known trusted phone/laptop, reject unauthenticated clients and non-LAN/public ingress. Ensure WSL/Windows port forwarding remains unchanged and no self-referential portproxy is introduced.
- [ ] Test Gateway restart, browser refresh, duplicate-send, CSRF failure, origin mismatch, brute-force limits, large user/agent text, HTML/script injection, malformed WS packets, stale abort, multiple tabs and read-only outage.
- [ ] Confirm activity logs record only sanitized error codes, timestamps and optional run IDs, never chat text/tokens/structured tool arguments.
- [ ] Review that a chat prompt cannot bypass Bob's configured sandbox/tool restrictions or Moltbook approval workflows.
- [ ] Release through the normal manifest `from` chain and **`bobctl update`**, backed up and reversible. Keep a single concise live smoke-test checklist, not a wall of commands.

### Initial acceptance checklist

- [ ] From phone and laptop on the private LAN, sign into the existing Activity Manager; **Chat** loads without exposing port 18789.
- [ ] Message **“Bob, what has caught your attention on Moltbook lately?”** receives a reply from the existing OpenClaw agent running with Bob's configured identity (not an Ollama-only test backend).
- [ ] Conversation history reappears after reloading the Chat page.
- [ ] A Gateway or Ollama outage has a clear non-misleading status and doesn't lose/duplicate the user's message.
- [ ] The UI accurately distinguishes Bob's actual saved Scout experience from hypothetical ideas; full PM2/FM context is not assumed available until CH1.3 is implemented and explicitly enabled.
- [ ] Auth/CSRF, private Gateway pairing credentials, rate limits, existing Scout/Publisher limits, manually reviewed friend interactions and original-post approval are unchanged.
- [ ] `bobctl update` applies and rolls back the release without exposing a new LAN service or changing Gateway bind/auth.

### Explicitly out of scope until separately approved

- No direct browser-to-Gateway WebSocket, LAN binding for Gateway, generic RPC proxy, iframe of privileged Gateway Control UI, unbounded shell/exec, admin device pairing, tool approval UI, file uploads, voice/video, automatic chat-to-Moltbook publishing, silent training/memory writes, automatic follows, DMs, or public endpoints.
- No claims that Bob actually remembers a past Scout run unless the relevant source is verifiably accessible through agent context.
- Do not merge the unrelated FM3.2, FM4 or FM5 work into the first CH1 release; chat is an independent workstream.

### New-chat kickoff message

> Begin **CH1.0 Direct Bob Chat** for `merberg-ai/bob-openclaw-moltbook`. Read root `TODO.md`, `docs/ARCHITECTURE.md`, and `docs/FRIENDS-ROADMAP-AND-HANDOFF.md`. A **LAN-accessible Chat page within the authenticated Activity Manager** is mandatory; Gateway remains loopback-only. Integrate with the **actual OpenClaw Bob agent**, not Ollama directly. First verify installed Gateway RPC/session/auth compatibility, then implement the smallest safe server-side bridge and mobile UI via `bobctl update`. Preserve all publishing, friend and memory safeguards.
