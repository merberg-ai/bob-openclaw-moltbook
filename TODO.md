## R4 autonomy1 consolidated development, one eventual installation (2026-11-01)

- [x] **R3 public canary accepted:** exact approved comment was acknowledged by the original publisher, recorded as attempted/published, and independently found in the public listing. No automatic retry or second local attempt. Preserve its ledger, release and original HTTPS service.
- [x] **Unified R4 UI source:** HTTPS-authenticated, 380px responsive Now, Inbox, Bob, Controls, Diagnostics and reserved inert Chat; existing PM2, personality, FM friends and FM4.1 social history linked rather than duplicated.
- [x] **R4 controls / pause source:** independent per-action Off/Propose/Auto contract and typed owner controls, all Off by default. Auto deliberately cannot be selected before corresponding source-verified worker is approved. Separate R4 pause does not flip legacy Scout or old R3 canary permissions.
- [x] **R4 observed evidence source:** bounded SQLite read-only projections, owner-staged notes versus Bob-expressed sealed R3 reasons versus platform follow status, exact existing attempt provenance, no invented external verification.
- [x] **Agent/social contract source:** strict eight-field model output against verified Scout source ID/post/author, genuine skip, minimum two observed posts before a follow proposal, unverified reply/unfollow refused. Fixed official API method/paths but no direct external writer. Full fake-model tests.
- [x] **Single non-current candidate / CI:** `v0.8.0-autonomy1` candidate under `releases/candidates/`, exact HTTPS Manager generated over accepted R3/R2/legacy stack, one read-only source audit. `releases/current.json` stays `v0.8.0-r3canary1`; no OMEN install.
- [x] **Source-sealed R4 social proposal and private owner Inbox:** new additive durable R4 ledger (skips, proposals, exact-seal owner approve/reject, separate append-only audit), two independent source checks, precommit follow-evidence recheck, duplicate and source-age refusal, separate from all R3 and legacy publication tables. One-shot future `bob-r4-propose --once` uses genuine OpenClaw agent only after verified owner modes and unpaused settings; no systemd timer, publisher, API client, or installation. Full synthetic validation including Host/Auth/Origin/CSRF. Source in PR #137.
- [x] **R4 memory/relationship suggestion review:** source-sealed private memory and Follow-based relationship suggestions stage atomically with Bob's validated proposal. Exact typed HTTPS owner approval creates a low-confidence opinion via existing PM2, or a pending candidate in existing FM Friend Discovery, *not* a platform follow or immediate friend. Existing memory/friend managers do final local handling; no automatic OpenClaw memory injection. Negative tests cover tampering, duplicate review, parent rejection and rollback.
- [x] **Offline versioned schema rehearsal:** `bob_r4_schema.py` checks the exact additive social/suggestion tables and schema marker; synthetic migration preserves verified historical R3 attempt/receipt rows, detects partial/future schemas, and is idempotent. The actual OMEN install hook is deliberately hard Off.
- [ ] **Production signed R4 schema integration:** one guarded, backup-verified installation must explicitly enable and run the versioned migration after host/release preflight. R4 GET never migrates the database, and OMEN remains on unchanged `v0.8.0-r3canary1`.
- [ ] **Single-publisher verified actions:** real supported social actions through original credentialed process only, durable atomic intent, per-action budgets, owner revocation, pause, no-replay uncertainty, remote verification and identity/following checks. Must not let existing canary arm authorize R4.
- [ ] **One final integrated signed release + host acceptance:** complete CI including synthetic API faults/races, TLS authenticated routes and rollback, single owner-confirmed `v0.8.0-autonomy1` installation and read-only acceptance. No interim OMEN release. Direct Bob Chat remains later CH1.

---

## R3 public canary VERIFIED and accepted on real OMEN (2026-11-01)

- [x] **Signed R3 canary installed:** `v0.8.0-r3canary1` upgraded from `v0.8.0-r3skip1` with typed `UPDATE`; `report_r3_canary_installed.py --check` reported `acceptance: PASS`, signed exact scope PASS, authenticated HTTPS PASS, R3 owner controls PASS, original service topology PASS. Installing did **not** arm or publish.
- [x] **Exact manual approval, queue and owner arm:** source `20261101T151033Z`, target `bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a`, seal `870a59f6bb3ccc02088bf44e8f1530c7a19a4d511f312420b609d8fa735a4bc2`. Owner explicitly approved on HTTPS `/r3`, separately queued, `bob-r3-canary-arm --check` returned `READY_TO_ARM`, and typed `ARM BOB R3 20261101T151033Z` produced `R3 EXACT CANARY: ARMED`.
- [x] **Exactly one observed R3 attempt and public listing verified:** normal **existing publisher** timer at 2026-11-01 **11:46:08 PST** reported `R3 candidate outcome: api_acknowledged`. Fixed local queue inspection: `state: published`, `attempt_recorded: true`, `local_record_stable: true`, `no_other_attempted_target: true`, saved comment ID `8c37f88f-e678-4007-ba56-586b76ef4cfd`. Separate bounded anonymous public GET returned `independently_visible: true`, `public_observation: visible_in_public_listing`. Subsequent user-shared publisher ticks returned `no queued publications`, not additional R3 posts.
- [x] **Uncertainty / authorization boundaries preserved:** `retry_authorized: false`, `external_duplicate_excluded: false`, `api_ack_is_public_receipt: false`. Independent GET confirms this known comment's visibility, **not** the absence of every possible external duplicate or other actor. Canaries, source/run pin, and marker do not authorize future R4 action categories. Keep R3 broad auto Off and preserve publisher history/receipt.
- [ ] **R4 one consolidated milestone:** `v0.8.0-autonomy1` integrates responsive Now/Inbox/Bob/Controls/Diagnostics; genuine evidence-grounded memory, social reflections and friendships; only verified Moltbook endpoints; explicit independent Off/Propose/Auto controls; fault/recovery gates, signed single publisher and one guarded user acceptance. Do not implicitly promote R3's owner approval or arm to new powers. CH1 real Gateway Chat remains a later independent feature.

---

## R3 first valid real OpenClaw decision ACCEPTED on OMEN (2026-10-31)

- [x] **Installed signed R3 Format1 release acceptance PASS:** Owner ran `scripts/report_r3_format_installed.py --check` and observed account verified, signed diagnostic package PASS, authenticated HTTPS health PASS, authenticated R3 Controls PASS, proposal-only timer ACTIVE, overall `acceptance: PASS`. No database, service schedule, publisher or credential changes; real R3 public publishing remains unauthorized.
- [x] **First valid natural scheduled model decision:** On 2026-10-31 20:01:41 PDT, `bob-r3-propose.service` started on the real OMEN. At 20:01:54 it returned `{"attempted":false,"dispatch_authorized":false,"queued":false,"reason":"bob_chose_not_to_comment","source_run":"20261101T024801Z","status":"skipped"}`; systemd then logged **Finished** (not failed). This proves an actual scheduled OpenClaw main-agent reply was accepted by the unchanged strict five-field contract under R3 Format1. A skip is a valid abstention, **not** a generated draft or an external comment.
- [ ] **Next distinct R3 producer gate:** Observe an independently chosen `status: proposed` on a future natural tick, verify a source-linked, sealed draft appears for authenticated owner review without any public send, or a legitimate `none`/new `skipped` outcome. Do not force a model outcome, manually start the service, replay old sources or weaken the validator to fabricate a proposal.
- [ ] **Public canary remains separate:** current signed release has all R3 real dispatch gates hard Off; first public R3 comment requires another reviewed source-level release, exact target/draft owner approval, single guarded attempt and remote receipt verification. No timer or publisher changes authorized by this acceptance.

---

## R3 strict five-field decision format repair (2026-10-31)

- [x] **Second natural proposal worker attempt confirmed:** 19:26:02 PDT service started and 19:26:09 returned `decision_invalid_model_shape` for verified source run `20261101T014755Z`. No proposal queued or public send attempted; next systemd run scheduled ~20:01 PDT. Exact raw model fields are not logged, so the cause is shape mismatch, not proven missing-vs-extra fields.
- [x] **R3-only schema prompt** now supplies an example of the exact five-field string JSON object, with pinned `source_run` and `target_id`, outside the delimited third-party data. The original strict parser remains unchanged: malformed/wrapped/nonmatching output is rejected, never silently repaired or sent.
- [x] **Sanitized shape classifications** split `decision_invalid_model_shape` into `decision_shape_not_object`, `decision_shape_missing_fields`, `decision_shape_extra_fields`, `decision_shape_missing_and_extra_fields`, or `decision_shape_invalid_field_values`, without exposing any field names, values, credentials or raw model response.
- [x] **Minimal signed update prepared:** `v0.8.0-r3format1` from `v0.8.0-r3diag1`, three managed files (updater, bobctl, R3 ZIP), no manager restart, no new publisher, no timer change or SQLite migration; hard-Off public dispatch retained. Guarded updater preflight and read-only `scripts/report_r3_format_installed.py --check` implemented, with offline CI. See `docs/R3-FORMAT1-STRICT-JSON-REPAIR.md`.
- [ ] **Owner OMEN acceptance pending:** after CI/PR merge run source-updater `--check`, typed `UPDATE`, one read-only installed check and observe the next natural R3 proposal result. Actual model compliance and Moltbook canary remain separate; no forced manual service execution or public R3 comment rights.

---

## R3 first natural proposal: actionable diagnostic release (2026-10-31)

- [x] **First natural timer run observed:** at 18:50:34 PDT, `bob-r3-propose.service` started on OMEN; at 18:50:39 it failed closed with `openclaw_decision_invalid_or_unavailable`. No queue, attempted send or dispatch authorization. Next timer tick was scheduled automatically, confirming the first-run timer repair.
- [x] **OpenClaw failure taxonomy fixed in source:** R3 producer now distinguishes `openclaw_*` CLI/envelope issues from `decision_*` strict JSON/target/reason validation errors using the existing R2 allowlisted safe error categorizer. Raw model output, third-party text, credentials and stderr never appear in journal output. Synthetic input tests cover real observed failure categories, private text suppression, valid skip and fail closed.
- [x] **Minimal signed diagnostic release prepared:** `v0.8.0-r3diag1` from installed `v0.8.0-cutover1`, three code files only (updater, bobctl, R3 ZIP); HTTPS preserved, no Activity Manager binary/restart, publisher/Scout/timers/DB schema unchanged, four real R3 public send gates still hard Off. Guarded installed-cutover and idle/timer preflight plus read-only `scripts/report_r3_diagnostic_installed.py --check` prepared. See `docs/R3-DIAG1-SAFE-ERROR-REASONS.md`.
- [ ] **Owner install/acceptance pending:** after PR/CI approval, owner runs source updater `--check`, separately typed code-only `UPDATE`, then one installed acceptance `report_r3_diagnostic_installed.py --check`. On next natural timer tick inspect sanitized `reason`, then target the exact observed contract failure with focused source change if necessary. Never force a model run or replay public POST to collect diagnostics.
- [ ] **Public R3 canary remains separate and unauthorised:** diagnostic release does NOT enable manual/auto dispatch, change publisher/Scout or grant external posting rights.

---

## R3 first natural proposal tick: discovered missing timer anchor (2026-10-31)

- [x] **Observed real OMEN symptom:** `bob-r3-propose.timer` was active after owner-approved handoff, but `systemctl --user list-timers --all bob-r3-propose.timer` showed `NEXT -`, `LAST -` on two checks, and `journalctl --user -u bob-r3-propose.service --since '1 hour ago'` returned no entries. A timer-active state was not a scheduled decision.
- [x] **Root cause identified in source:** the installed user timer contains `OnUnitInactiveSec=35min` only. Since the R3 oneshot has never run, no last-deactivation timestamp exists. Systemd requires an initial monotonic anchor such as `OnActiveSec=2min` for first firing (see systemd.timer documentation).
- [x] **Source-only repair prepared:** `scripts/repair_r3_first_timer.py` installs a narrowly pinned `[Timer] OnActiveSec=2min` user timer drop-in, without touching the original SHA-verified handoff unit files or journal. The script requires the previously accepted installed cutover1 hard-Off release, original journal complete, publisher/Scout unchanged, idle services, no competitor, and interactive owner phrase `REPAIR R3 FIRST TIMER`; it reloads/restarts only the *proposal timer* and checks a monotonic next deadline. `--check` is read-only, `--undo` removes only the exact drop-in. No publisher, credentials, SQLite or external POST actions.
- [ ] **Real owner verification pending:** after PR CI and merge, run one read-only repair check, one separately confirmed timer repair, then verify a real `NEXT` deadline. Only later does journal evidence of a naturally fired R3 proposal service establish model execution. Do not start the service manually or enable any public R3 dispatch.
- [ ] **Recovery note:** the original `r3_service_handoff.py --recover` predates this drop-in. Use the exact `repair_r3_first_timer.py --undo` first if later reverting to R2 Shadow. Do not leave unreviewed drop-ins behind.

---

## R3 proposal-only scheduler handoff: owner-accepted activation (2026-10-31)

- [x] **Read-only service handoff preflight PASS:** the real OMEN reported `installed signed cutover1 hard Off: True`, `preflight blockers: none`, original publisher/Scout untouched, R3 proposal timer not yet enabled and real R3 publishing unauthorized.
- [x] **Owner-authorized proposal timer activation succeeded:** `python3 scripts/r3_service_handoff.py --apply` accepted exact typed confirmation `ACTIVATE R3 PROPOSALS` and returned `R3 HANDOFF: proposal_only_timer_active`. The first confirmation was rejected because of a leading extra space; the exact second entry succeeded. Subsequent `systemctl --user is-active` showed `bob-r3-propose.timer: active`, `bob-v08-shadow.timer: inactive`, `bob-moltbook-publisher.timer: active`, `bob-moltbook-scout.timer: active`. The handoff reported publisher, Moltbook, and SQLite history untouched.
- [ ] **R3 next acceptance:** observe a **natural timer-fired** `bob-r3-propose.service` run and its sanitized outcome. An active timer is NOT proof of successful scheduled agent proposal or that fresh source material exists; Bob may choose `skip` or find no eligible source. Prefer read-only `systemctl --user list-timers --all bob-r3-propose.timer` and `journalctl --user -u bob-r3-propose.service --since '1 hour ago' --no-pager -n 50` without starting services manually.
- [ ] **First real R3 public canary still NOT authorized:** all four R3 send gates remain hard Off. A separately reviewed future source release, exact owner-approved target and comment draft, one limited attempt and remote receipt verification are required; no automatic publication or replay.

---

## R3 Cutover1 Off-first installed acceptance PASSED on OMEN (2026-10-31)

- [x] **Owner-installed `v0.8.0-cutover1` passed the single read-only on-host acceptance:** `python3 scripts/report_r3_cutover_installed.py --postcheck` returned `acceptance: PASS`. Normal `openclaw` user verified; installed signed release `cutover1_hard_off_verified`; authenticated CA-verified HTTPS health and R3 Controls both PASS; owner settings `default_off`; single existing publisher PASS; new R3 proposal timer OFF. Original historical attempted comments 23, uncertain delivery rows 0. Report explicitly observed no database, credentials, Moltbook or systemd changes; R3 real public publishing still NOT authorized.
- [x] **Release promotion and first physical testing complete:** PR #125 merged into `next` at `6bcd9ae25d88a40cd0f769064fe035d054b70cfe`, reviewed 12-file `v0.8.0-cutover1` source bundle offered and owner installed; accepted host gate above. All 1,074 offline tests had passed again on the merged release.
- [ ] **Next separate R3 gate: proposal-only R2 shadow-timer handoff.** Owner must explicitly authorize a distinct unit-only transition. The read-only preflight is `python3 scripts/r3_service_handoff.py --check`. It must show expected exact unit states, safe idle shadow worker, existing Scout/publisher active and no competing writer. Handoff `--apply` requires a separate typed `ACTIVATE R3 PROPOSALS` and is NOT yet approved, performed, or implied by cutover1 acceptance.
- [ ] **Real Moltbook R3 publishing remains a separate gate:** all source dispatch/auto flags remain hard Off. One first exact source/post/draft/attempt canary needs its own source review and explicit owner consent. Never equate proposal timer approval with publication authority, and never auto-replay attempted/uncertain work.
- [ ] **R4 after R3 activation/verification:** social follow/upvote/exploration and unified owner UI under separate opt-in and verification.

---

## R3 consolidated pre-host engineering acceptance snapshot (2026-10-31)

- [x] **Full pre-host source integration staged and CI verified:** original one credentialed publisher, R3 sealed producer/owner pipeline, exact 12-file HTTPS integration candidate, safe source updater, registry-before-restart and code-only rollback; the synthetic proposal-to-owner-to-publisher and timer handoff/recovery suite passed within **1,074** full offline tests on the last tested source revision. CI source validation after the short operator guide edit remains required. No host or Moltbook changes made.
- [x] **One future owner guide** at `docs/R3-CUTOVER1-OWNER-HANDOFF.md`: checkout-source updater (not old installed `bobctl update`), one authenticated/verified Off-first postcheck, and a **separate optional** proposal-only timer handoff with journal/rollback. A first real Moltbook R3 canary requires a later source-reviewed release and exact owner consent. No timed or concurrent credentialed publisher is introduced.
- [ ] **STOP BEFORE PHYSICAL/OWNER TESTING:** release candidate `releases/candidates/r3-cutover1-integration-off.json` remains **UNPROMOTED** and `releases/current.json` continues advertising `v0.8.0-chhttps3`. The operator must deliberately authorize promotion and a guarded installation after reviewing final offline gates. No host action needed now; no `--apply` or live canary.
- [ ] **R4 afterward:** new Moltbook social autonomy/follows/votes only with API verification and separate owner permissions.

---

## R3 one-consolidated host acceptance prepared (offline only)

- [x] **One post-install read-only report implemented:** `scripts/report_r3_cutover_installed.py --postcheck` is staged for the later OMEN handoff. It verifies exact installed `v0.8.0-cutover1` hashes, four compiled real-send gates Off, pinned CA-verified authenticated HTTPS manager routes including `/r3`, additive R3 schema and default-Off owner controls, one active legacy publisher timer plus active Scout timer, old R2 shadow still active, R3 proposal timer still disabled/uninstalled and no competing publisher. Outputs only safe status/aggregate attempted/uncertain counts, never private draft text, token, unit content or remote IDs. Does not call Moltbook or modify any local state.
- [x] **Single pre-update host drift refusal:** checkout-source `scripts/bob_release_updater.py` invokes previously accepted G2 HTTPS/queue/unit baseline and verifies the existing publisher oneshot is *inactive* before asking the owner to type UPDATE for `v0.8.0-cutover1`. A busy publisher or changed host refuses the code install rather than starting a new public send or stopping the old timer. This is a point-in-time gate, not an atomic systemd transaction.
- [x] **Tests and source CI coverage:** synthetic happy/denied installed acceptance, inherited permissions, host drift, busy publisher, unknown release, no owner mutation, and no accidental publisher timer changes. E2E owner/publisher and unit handoff tests are offline-only.
- [ ] **Actual OMEN acceptance and any R3 unit activation NOT AUTHORIZED YET:** after all source-only CI/release review and owner approval, one guarded install and one composite read-only health report, followed by separately typed optional proposal-timer handoff. No published canary without distinct exact post/comment/attempt approval. Do not alter `releases/current.json` until source CI and review gates are ready.

---

## R3 pre-host full-chain and proposal-timer handoff engineering (source only)

- [x] **Proposal-only service ownership designed and implemented offline:** `scripts/r3_service_handoff.py` defines exactly `bob-r3-propose.service` and `bob-r3-propose.timer`, initially uninstalled and disabled. The timer runs only the verified `bob-r3-propose --once` launcher; it is **not** a second Moltbook publisher. The old `bob-moltbook-publisher.timer` and `bob-moltbook-scout.timer` must remain active throughout. Handoff checks that the R2 shadow decision worker is idle, original shadow timer is active and enabled, and every competing R3 publisher service/timer is inert; only the original R2 shadow decision timer can be retired in favor of the proposal-only R3 timer.
- [x] **Guarded future owner action, not executed:** `--check` is nonmutating. `--apply` requires real installed `v0.8.0-cutover1` with all four **hard-Off** source dispatch constants, exact installed-file hashes, valid HTTPS transport, expected systemd states, private owner identity and a terminal phrase `ACTIVATE R3 PROPOSALS`. It journals exact unit hashes and transitions; `--recover` with `RECOVER R3 SHADOW` restores prior R2 timer and removes only unchanged candidate unit files, never publisher/Scout, credentials, remote API or SQLite. No service modifications have been authorized or performed.
- [x] **Offline fake-systemd contract and recovery tests:** success, disabled-by-default state, early failure, interruption after retiring shadow, deliberate unit drift, active competing publisher, busy shadow, inactive Scout, unauthorized release and missing/unknown units are tested; all changes occur in disposable temporary directories.
- [x] **One coherent synthetic Bob proposal-to-publisher chain:** `tests/test_r3_end_to_end_offline.py` runs real production-shaped sealed `propose_verified`, typed owner `manual-on`, independent exact approve and queue, and the real existing publisher adapter with mocked signed package, fixed-host public author review and fake POST. Tests assert only one request/key lookup, no replay on uncertain timeout, cancellation before attempt and absolute manual priority of old human-approved work. Actual production dispatch constants remain compiled Off.
- [ ] **Await offline CI and full integration acceptance; no host action yet:** finish end-to-end suite/review, ensure source candidate fixed HTTPS/install chain and rollback proofs, and prepare one consolidated OMEN acceptance report. Do not promote `releases/current.json` or run `--apply` before the full release and separate owner approval.

---

## R3 signed-archive activation/recovery engineering source gate (2026-10-31)

- [x] **Fix candidate private-registry activation order:** original updater publishes installed SHA registry after manager restart, but new R3 signed ZIP loader requires exact hash at import during startup. Reviewed source update checks all candidate hashes, atomically publishes provisional new registry with an incomplete transaction journal, **then** restarts manager and performs HTTPS health; failure/code-only rollback restores old code and prior registry. The production installed updater remains unchanged until a later owner-approved release.
- [x] **Disposable real-updater rehearsal added:** tests call actual updater `update`/`rollback` with isolated synthetic manager/archive/registry/journal, mocked systemd/HTTP/backup. Demonstrates candidate SHA already trustworthy on restart; rollback after failed health, interruption and restart error; **post-update synthetic SQLite attempts survive rollback** (never stale database restore). These are CI fixtures, not real host acceptance.
- [ ] **Final R3 release still withheld:** integrate safe original publisher module reload, exact controlled service ownership and post-restart checks with code-only unit rollback, owner-consent and pre-POST validation, shadow G1 scheduling, and separately reviewed canary permission. Candidate not promoted; existing services/timers and R3 Off unchanged.

---

## R3 consolidated source bundle staged (2026-10-31; no live install or posting)

- [x] **One 12-file integration candidate, source-only:** `releases/candidates/r3-cutover1-integration-off.json` chains exactly from the installed-source `v0.8.0-chhttps3` to the reserved `v0.8.0-cutover1` identity. It collects one existing credentialed publisher (with hardened duplicate checks), existing R3 owner/proposal modules, verified R3 ZIP/launcher, HTTPS-only generated Activity Manager/navigation, and source updater+`bobctl` transport compatibility. **`releases/current.json` is not modified.**
- [x] **HTTPS protocol continuity fixed in candidate source:** updater and `bobctl` have a *fixed* `v0.8.0-cutover1 -> https` mapping, preserving the exact private CA and SAN-verifying behavior. The currently installed old updater does not know future release IDs and would fail its post-install health check; a later operator-approved single-install path must use the separately reviewed checkout-source updater, not the old installed updater, unless a compatibility update is approved first. No plaintext fallback.
- [x] **Strict no-install source audit:** `python3 scripts/report_r3_consolidated_candidate.py --check` validates the fixed manifest chain/files, compiles/builds all 12 reviewed release artifacts, checks FOUR literal R3 public-send/auto Off gates and exact HTTPS pin, and reports `ready_to_install_or_cutover=False`. Automated regression covers exact artifacts, unknown release rejection, source drift, extra target and wrong chain. This is for CI; owner should **not** need to run it.
- [ ] **NOT YET CUTOVER-READY:** all real R3 send gates remain Off, the candidate is explicitly unpromoted, and no managed timer/service transition, automatic permission expansion, true publisher/ZIP activation, exact authorized canary, integrated rollback or production acceptance has been approved. Continue combined source/CI engineering without host installations.
- [ ] **After complete source review and isolated rehearsal:** one explicit owner upgrade and consolidated health report, only then separately authorized exact-comment canary. Never silently run a second credentialed publisher or disable existing Scout/publisher.

---

## G2 accepted on OMEN; consolidated R3 single-writer source hardening in progress (2026-10-31)

- [x] **Owner's G2 bounded public receipt report PASS:** 23 historical legacy comment attempts, all 23 inspected, 23 valid saved receipt IDs, all 23 exact IDs observed in public comment listings, no truncation, no repeated attempted target groups, no reused receipt IDs, and local database unchanged across the public GET checks. The report returned `known_receipts_visible`; this is strong **all known receipts reconciled** evidence, not absolute proof that an unrecorded remote duplicate could not exist. Original posts were not included.
- [x] **R3 pre-cutover duplicate-target publisher hardening (source only):** improve the *existing* credentialed legacy publisher's duplicate check to include every row with `attempted_at IS NOT NULL`, regardless of a later state of `failed`, and recheck that same target rule atomically in the final original `publish_jobs` claim after public GET. Synthetic regression covers a prior post-attempt failure, an attempted duplicate inserted during GET, and a safe historical unattempted failure. Existing three R3 compiled-Off source gates untouched.
- [ ] **Full consolidated R3 release engineering still required:** single versioned `v0.8.0-cutover1` candidate from installed `v0.8.0-chhttps3`, reviewed publisher package import, unified timer ownership, protected dashboard owner controls, source/approval/pause/limits hard barriers, API acknowledgement vs independently verified public receipt, interrupted send recovery and code-only rollback. No `releases/current.json` promotion or OMEN changes just because the source tests pass.
- [ ] **One owner acceptance at end, not now:** offline CI and isolated rehearsal first; then a separately authorized guarded update with one integrated health review. First genuine public canary requires separate exact target/draft/attempt consent; R3 Off remains in effect.
- [ ] **Residual G1:** allow one naturally scheduled source-linked shadow decision when new verified Scout sources arrive. Do not force replay.

---

## Active execution plan: ONE G2 reconciliation, ONE consolidated R3 cutover (2026-10-31)

- [x] **G2 source-only aggregate public receipt audit implemented:** §scripts/report_g2_public_receipts.py§ reads exact legacy comment attempts via read-only SQLite and optionally checks locally saved receipt IDs through the existing bounded anonymous Moltbook public HTTPS GET reader. Scope at most 40 jobs, two pages each, detects missing/unverified receipts, attempted target/ID reuse, unresolved/unknown states and database changes during GET. Always says external no-duplicate posting unproven; does not POST or print private content. CI synthetic regressions included.
- [ ] **ONE owner G2 receipt check after green reviewed merge:** §cd ~/bob-next && git pull --ff-only && python3 scripts/report_g2_public_receipts.py --public-get§. The prior 23 attempted/0 uncertain local historical results are not full external proof. A truthful §review_required§ result is a category-based audit outcome; do not blind-retry anything. Original posts and potentially unrecorded remote duplicates are out of scope.
- [x] **R3 consolidated release contract written:** §docs/R3-CONSOLIDATED-CUTOVER.md§ plans integrated §v0.8.0-cutover1§ based on installed §v0.8.0-chhttps3§, one legacy credentialed publisher, source-sealed Bob approval, shared ledger, atomic intent/unknown locks, exact managed timer handoff and code-only rollback. R3 still HARD OFF; this documentation does not install or authorize real Moltbook writes.
- [ ] **NEXT engineering batch (not another owner test marathon):** implement the R3 source integration and offline fault/rollback CI, package one single candidate with one acceptance report. Only after owner approval: one update and one installed health check. Exact optional public canary separately approved. Do not change §releases/current.json§, running timers, private database or permissions while the candidate is incomplete.
- [ ] **R2 G1 opportunistic scheduled model-decision evidence:** timer execution is confirmed; a naturally source-linked decision remains unconfirmed. Allow normal Scout/Shadow operation to produce it without forced replay.
- [ ] **G2 privacy scope:** post-reboot both LAN clients reachable, owner's outside-network inaccessibility observation and default-block/source-limited Hyper-V firewall accepted. A fresh warning-free new-password browser challenge and exhaustive WAN/IPv6/router proof remain separately unverified; they are not reasons to repeat G2 reboot tests.

---

## G2.5 owner reports no external reachability; network scope accepted by observation (2026-10-31)

- [x] **Owner-reported internet-side observation:** “nothing is reachable from the outside.” Record this as the owner's statement that their network is not externally reachable, not a verified independent WAN/IPv6/UPnP port scan or exhaustive audit of all exposure paths. Do not infer the testing method, router model or precise external address.
- [x] **Existing independent local controls:** in WSL2 `mirrored` mode, Bob TLS binds `0.0.0.0:18790` and serves two Windows LAN clients; WSL Hyper-V firewall `Enabled=True`, `DefaultInboundAction=Block`, `AllowHostPolicyMerge=True`; the enabled TCP 18790 allow exception is source-limited to `192.168.1.0/24`. Windows `netsh portproxy` empty. No active `OpenClawLab` TCP 8787 listener although a separate code-server allow rule permits `Any`. These facts plus owner-reported outside inaccessibility strongly support the intended **LAN-only operational behavior** without service changes.
- [ ] **No global WAN-proof claim:** detailed host merged firewall, router forwarding/UPnP, public IPv6 and VPN audits weren't furnished; if LAN/WAN topology changes or public IPv6 is enabled later, recheck exposure. Preserve default block and scoped allow. No new firewall rules or publishing rights.
- [ ] **Last G2 external receipt/replay reconciliation:** local legacy publisher attempted count **23** and uncertain **0** both before/after reboot. Verify any actual Moltbook remote comments/receipts and recent activity against ledger without manually restarting publisher, replaying jobs, using POST, or enabling R3. Count parity by itself is not proof of no external duplicates.
- [ ] **Post-reboot TLS UI detail:** both LAN clients reached dashboard; absence of certificate warnings and fresh rotated-password sign-in were not explicitly reconfirmed in the latest report.

---

## G2.5 effective WSL Hyper-V inbound policy PASS; code-server 8787 not listening (2026-10-31)

- [x] **Owner-provided effective Hyper-V policy** for WSL VMCreatorId `{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}`: `Enabled=True`, `DefaultInboundAction=Block`, `AllowHostPolicyMerge=True`. The previously confirmed active `Bob Activity Manager - WSL LAN` rule allows `TCP 18790` only from `192.168.1.0/24`. **WSL-specific inbound firewall gate PASS** for expected default-block + scoped exception. This does not prove the total effective path is LAN-only because host policy can merge, other rules can exist, and router/WAN/IPv6/VPN paths need separate inspection.
- [x] **Owner-provided 8787 socket probe:** `ss -lnt '( sport = :8787 )'` produced header only. No currently listening TCP 8787 socket was found *inside OpenClawLab* during the check. Separate installed Hyper-V `code-server WSL 8787` inbound rule remains `Allow/Any`, but this is not proof that a service is running or externally accessible; consider narrower rule/removal after independently assessing whether code-server is required.
- [ ] **Complete network perimeter gate:** read-only Windows host firewall merged rules, router IPv4 forwarding/UPnP, IPv6 and VPN scope check. Do not add/delete firewall/portproxy rules to satisfy audits; LAN reachability and the WSL default-block gate are already functional.
- [ ] **External legacy publisher no-duplicate gate:** independent reconciliation of attempted targets/receipts against actual Moltbook posts across reboot; local unchanged 23 attempted / 0 uncertain is insufficient proof. R3 remains compiled Off.

---

## G2.5 WSL Hyper-V inbound rule review: Bob LAN scope confirmed, default action still needed (2026-10-31)

- [x] **Owner supplied effective inbound rules:** `Bob Activity Manager - WSL LAN` was `Enabled=True`, `Action=Allow`, `Protocol=TCP`, `LocalPorts=18790`, `RemoteAddresses=192.168.1.0/255.255.255.0` (the user's `192.168.1.0/24` LAN). This is an appropriately scoped exception, even though the WSL process binds `0.0.0.0:18790` in mirrored mode. It does NOT by itself prove that traffic outside the LAN is blocked.
- [ ] **Need effective WSL Hyper-V firewall defaults:** the user-supplied output contained only individual rules, not `Get-NetFirewallHyperVVMSetting -PolicyStore ActiveStore -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'` values `Enabled`, `DefaultInboundAction`, `AllowHostPolicyMerge`. Require `Enabled=True` and a blocking default before calling scoped rules effective in isolation; review Windows firewall host merge and router separately.
- [ ] **Separate 8787 code-server potential exposure:** an unrelated enabled `code-server WSL 8787` inbound Hyper-V `Allow TCP 8787 RemoteAddresses=Any` rule exists. **Not proof of WAN exposure**, but more permissive than Bob's rule. Read-only check whether WSL actually listens on TCP 8787 before any rule change; inspect authentication and router/WAN path separately if used. The ICMPv4/v6 and mDNS defaults shown by the user are unrelated protocols/ports and should not be mistaken for generic port 18790 allows.
- [ ] **Remaining G2 security boundary:** Windows host/firewall, IPv6, VPN and router forwarding/WAN exposure review; no live changes now. Keep external Moltbook no-duplicate receipt/queue comparison separate from these host-firewall checks. R3 remains hard Off.

---

## G2.5 OMEN mirrored WSL listener confirmed (2026-10-31)

- [x] **Owner-confirmed Linux listener and WSL mode:** from Windows PowerShell, `wsl.exe -d OpenClawLab -u openclaw -- ss -lnt '( sport = :18790 )'` returned `LISTEN 0.0.0.0:18790`. `Select-String ... .wslconfig ...` returned `networkingMode=mirrored` on line 2. A Linux-owned wildcard IPv4 socket in WSL mirrored mode explains access from both LAN Windows clients even though Windows `Get-NetTCPConnection` showed no listener and Windows `netsh portproxy` had no entries. `0.0.0.0` is **not LAN-only** binding proof.
- [ ] **Read-only WSL Hyper-V firewall policy gate:** use the Microsoft WSL creator ID `{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}` and `Get-NetFirewallHyperVVMSetting -PolicyStore ActiveStore -Name $wslId` to inspect enabled/default inbound; inspect inbound matching rules with `Get-NetFirewallHyperVRule -VMCreatorId $wslId`, including enabled/action/protocol/local ports/remote addresses. Do not change Hyper-V or Windows firewall yet.
- [ ] **WAN boundary separate:** inspect Windows active-profile policy, router/NAT forwarding, IPv6 exposure, and any VPN interfaces before asserting private LAN only. A firewall rule for all remote addresses on a wildcard WSL listener is not intrinsically WAN-safe; absent router port forwarding alone may not cover IPv6. No new service/release changes or R3 posting rights.
- [ ] **Independent Moltbook external receipts/duplicate comparison:** 23 local attempts/0 uncertain pre/post reboot does not establish that no external duplicate posts occurred.

---

## G2.5 WSL listener inspection corrected after Windows-only probe (2026-10-31)

- [x] **Owner Windows PowerShell observation:** `Get-NetTCPConnection -State Listen -LocalPort 18790` returned `No matching MSFT_NetTCPConnection objects`, and `netsh interface portproxy show all` returned an empty list. These are valid negative observations of *Windows host* TCP listeners and explicit `netsh` portproxy rules. They are NOT a failed Bob service health check, and they cannot prove port 18790 is unexposed while the Activity Manager remains reachable from both Windows LAN machines.
- [ ] **Read-only WSL-aware diagnostic, PowerShell on OMEN:** `wsl.exe -d OpenClawLab -u openclaw -- ss -lnt '( sport = :18790 )'` reports Linux socket bind(s) without showing private command-line arguments; `Select-String -Path "$env:USERPROFILE\.wslconfig" -Pattern '^\s*networkingMode\s*=' -ErrorAction SilentlyContinue` reports any explicitly configured WSL networking mode, not necessarily effective runtime configuration. Do not publish full `.wslconfig` content.
- [ ] **Separate Hyper-V firewall + router acceptance:** WSL mirrored networking can receive direct LAN traffic via Windows/WSL bridging without a Windows process bound in `Get-NetTCPConnection` or `netsh portproxy`. Inspect WSL Hyper-V firewall effective settings and scoped rules, ordinary Windows firewall, host/router perimeter and any inbound WAN forwarding before claiming LAN-only access. No new portproxy, wildcard listener, manual firewall change, R3 send authority or publication.
- [ ] **Independent real Moltbook external receipt/no-duplicate review still open:** 23 historical attempts / 0 uncertain across reboot is a local evidence point, not external proof.

---

## G2.4 post-reboot dashboard reachable from BOTH Windows LAN clients (2026-10-31)

- [x] **Owner-reported two-client post-reboot access:** both the OMEN and the second LAN Windows machine can access the Bob Activity Manager dashboard following the successful Windows reboot/logon and G2.3 WSL postcheck. This establishes remote LAN reachability to the dashboard in addition to prior fixed-host verified HTTPS and R3 Off checks.
- [ ] **Browser warning/credential detail not independently reported in this confirmation:** verify neither Windows browser presents a certificate warning or bypass and that fresh authentication uses the rotated password. Do not infer those specific observations solely from “both systems are able to access.”
- [ ] **G2 external publishing receipt/ledger review:** pre/post Linux report shows 23 historically attempted and 0 uncertain jobs without a new *recorded* attempt; independently reconcile real Moltbook replies/receipts/target IDs before saying no duplicates. No replays, manual publisher unit starts, or R3 send authority.
- [ ] **G2 LAN/WAN perimeter review:** read-only inventory of listener interfaces, Windows firewall and portproxy rules, and external router forwarding; working LAN access alone is not proof that WAN cannot reach the port. Keep services/settings unchanged.

---

## G2.3 OMEN Windows reboot/logon and core service recovery accepted (2026-10-31)

- [x] **Owner witnessed Windows reboot + WSL running after sign-in:** before the reboot, `python3 scripts/report_g2_recovery.py --baseline` returned `host gate: PASS` with trusted HTTPS/R3 Off, expected original units/inert competitors, reviewed legacy publisher, migration/history verified, attempted 23, uncertain 0, linger=yes. After Windows reboot and user sign-in, a Windows PowerShell `wsl.exe --list --verbose` listed **OpenClawLab Running** without an operator-reported manual distro launch; Ubuntu/Ubuntu-24.04 Stopped; docker-desktop Running. This supports successful Windows-user-logon WSL startup, not unattended pre-login boot.
- [x] **Owner post-reboot host recovery PASS:** inside OpenClawLab as `openclaw`, `python3 scripts/report_g2_recovery.py --postcheck` returned `host gate: PASS`, HTTPS/R3 Off PASS, required unit and inert competitor states PASS, legacy publisher reviewed, queue schema/journal verified, attempted 23, uncertain 0, linger=yes. `systemctl --user is-active openclaw-gateway.service` returned `active`. G2 report correctly states `Windows reboot observed by report: NO`: witness comes from owner, not code.
- [ ] **Remaining LAN client acceptance:** explicitly confirm a fresh login to `https://192.168.1.24:18790/r3` with new rotated password and no browser certificate warnings from the second Windows LAN machine after the reboot; repeat on the OMEN. Internal CA-verified loopback PASS alone is not proof of remote accessibility.
- [ ] **Remaining external publisher/no-duplicate acceptance:** attempted 23/uncertain 0 before and after reboot shows no recorded new *legacy* attempts in that observation interval, not proof that an external duplicate Moltbook post did not occur. Independently reconcile actual posts/receipts and queued targets against persisted ledger, avoid replay of attempted/uncertain jobs, and inspect legacy timer activity. Never force a publisher oneshot, restore an old database, turn on R3, or declare G2 complete from counts alone.
- [ ] **Remaining network perimeter acceptance:** verify activity manager remains restricted to private LAN and has no WAN forwarding/exposure. No change to installed release, services, Windows startup configuration or credentials for this documentation update.

---

## G2.2 Windows user-logon startup inventory PASS; G2.3 supervised reboot recovery next (2026-10-31)

- [x] **Owner-supplied G2.2 Windows PowerShell inventory PASS (read-only):** 0 relevant scheduled tasks, 0 Run registry entries, 2 user Startup-folder shortcuts, 0 query warnings. `Bob OpenClaw Startup` is a user-scope PowerShell shortcut; its reviewed local wrapper was `inspected` and mentions **WSL**, **OpenClawLab**, and **systemd**. `OpenClaw Companion` is a separate user-scope OpenClaw-named executable shortcut. Existing startup configuration and WSL unchanged. Private sanitized JSON remains in user-local `BobBaseline`, not in the public repo.
- [x] G2.1 read-only OMEN host baseline previously PASS: original user timers/manager active, system Scout duplicate timer disabled/inactive, old publisher reviewed, HTTPS/R3 Off, `Linger=yes`, attempted 23, uncertain 0.
- [ ] **G2.3 owner-scheduled Windows reboot/logon test (no automated reboot command):** before reboot, record `report_g2_recovery.py --baseline` and verify current new-password HTTPS on both Windows machines. Reboot Windows by the owner's normal UI action and sign back into the **same Windows account**. Before opening WSL/terminal or running any WSL launch commands, check second LAN machine's `https://192.168.1.24:18790/r3` and Windows PowerShell `wsl.exe --list --verbose` (observe OpenClawLab Running vs Stopped). An explicit WSL launch would invalidate this auto-start observation.
- [ ] **G2.3 after WSL observed Running naturally:** run `python3 scripts/report_g2_recovery.py --postcheck` as WSL `openclaw`, check `systemctl --user is-active openclaw-gateway.service` and both Windows trusted HTTPS new-password logins. Expect local host gate PASS, same inert competing services and R3 Off, and healthy Gateway; recorded `historical_attempts` / `uncertain` are evidence to compare, not an automatic no-duplicate verdict. The script always prints `Windows reboot observed: NO` because it cannot witness the Windows event; the owner separately supplies that observation.
- [ ] **Separate G2 external send/no-duplicate evidence:** review original legacy queue history/receipts and any actual Moltbook post attempts across reboot, allowing normal timer passage. Neither no new attempts nor equal counts alone proves no duplicated external posts. Windows firewall/WAN isolation still not independently confirmed. Do not run publisher oneshots, restore SQLite, disable legacy timers or authorize R3 posts to "test" reboot.

---

## G2.1 OMEN host baseline PASS; G2.2 Windows logon startup audit is next (2026-10-31)

- [x] **Operator-reported read-only G2 host baseline PASS:** `account: verified`, `installed https r3 off: PASS`, `expected user units and inert competitors: PASS`, `effective legacy publisher: reviewed_shape`, `legacy history schema journal: verified`, `historical attempts: 23`, `historical uncertain: 0`, `user linger: yes`, `host gate: PASS`. Report explicitly made no service/database/credential changes and no Moltbook requests, and did not grant R3 rights.
- [x] Previous inactive/static system-level Scout false blocker addressed in G2.1; the accepted baseline now proves the specific installed competing timer and candidate units are inert at inspection time. A static service may still be manually started or triggered by an unreviewed dependency, so avoid claiming whole-machine exclusive execution beyond the observed units.
- [ ] **G2.2 Windows startup collector (Windows PowerShell, NOT WSL terminal):** run already reviewed `scripts/inventory_windows_startup.ps1` from the updated `~/bob-next` checkout copied into a Windows temp script, no elevated privileges. Review trigger categories, existing startup items, PowerShell wrapper presence, and query warnings. The collector writes one PRIVATE user-local report but modifies no scheduled tasks, shortcuts, systemd units, registry configuration or WSL state. Console output only is shareable. Do not push the report to GitHub.
- [ ] **G2.2 scope decision:** older Windows evidence showed 0 matching scheduled tasks, 0 Run registry matches and two user Startup-folder shortcuts (`Bob OpenClaw Startup` via PowerShell wrapper mentioning WSL/OpenClawLab/systemd; `OpenClaw Companion` OpenClaw-named executable). This indicates probable **interactive user logon** recovery, not unattended pre-logon machine boot, and not yet actual reboot acceptance.
- [ ] After Windows startup audit, stage separately approved reboot test and post-reboot `python3 scripts/report_g2_recovery.py --postcheck` with BOTH LAN trusted HTTPS browser logins, pre/post queue attempt and uncertainty comparison and independent remote receipt review. No new R3 publishing/canary rights, no manual publisher execution, no duplicate-service installs.

---

## G2 baseline false blocker: inactive/static system Scout service (2026-10-31)

- [x] **Owner-supplied G2 read-only JSON diagnosed:** all three required user units `active/enabled`; system-level `bob-moltbook-scout.timer` `loaded/inactive/disabled`; paired system Scout `service` `loaded/inactive/static`; R3 candidate publisher service/timer both `not-found/inactive/unknown`; current trusted HTTPS and R3 Off PASS, reviewed legacy publisher, migrated SQLite history verified, historical attempted 23 / uncertain 0, user linger yes. Only the excessively strict `_inert` gate rejected the static service.
- [x] **G2.1 source fix:** recognize only the exact `system bob-moltbook-scout.service` as inert when `loaded/inactive/static` AND the paired **installed system timer** is `loaded/inactive/(disabled|masked|masked-runtime)`. No relaxation for R3 candidates, static timers, active services, enabled competing timers, unknown states or HTTPS/legacy journal requirements. Synthetic regression covers the owner's precise JSON and all unsafe timer variations.
- [ ] **Owner after reviewed CI/merge:** `cd ~/bob-next && git pull --ff-only && python3 scripts/report_g2_recovery.py --baseline`. Expect `host gate: PASS`, with 23 attempted / 0 uncertain if background publisher remains quiet, no R3 real posting. This proves only current host read-only shape, not an observed reboot or no external duplicate posts.
- [ ] **Next independent gates:** Windows login startup wrapper review, owner-scheduled WSL/Windows recovery, both separate trusted HTTPS Windows browser sessions, LAN-only exposure review, and cross-reboot ledger / external receipt comparison. No live service edits or public R3 sending rights.

---

## CH-HTTPS4 manager-only restart PASS; G2 reboot readiness next (2026-10-31)

- [x] **Owner-provided manager restart acceptance:** `systemctl --user restart bob-activity-manager.service` returned successfully; `systemctl --user is-active bob-activity-manager.service` output `active`. Before **and after** the restart, CH-HTTPS4 `--verify` returned `installed HTTPS, current login and R3 Off: PASS`, and CH-HTTPS3 `--installed` returned `acceptance: PASS`, verified installed release, correct CA SHA, authenticated TLS manager/R3, plaintext HTTP refused, and original Scout/publisher timers active. No additional R3 publishing rights. Prior rotation `--apply` separately proved old 401/new 200.
- [ ] **Two-browser post-rotation AND post-restart trust:** owner has not explicitly reported fresh new-password login and no cert warnings on both OMEN and remote Windows since the accepted rotation/restart. Do not infer these from loopback checks.
- [x] **G2 source-only read-only report staged:** `scripts/report_g2_recovery.py --baseline` and `--postcheck` classify exact manager/publisher/Scout unit states and duplicate-scope Scout/candidate writer risk, installed HTTPS and Off, effective reviewed publisher service/timer, and private SQLite historical attempts/uncertain counts. No writes, secret output, or Moltbook requests. The report NEVER claims to observe a Windows reboot, external posts/no-duplicates, LAN-only perimeter, or the Windows Startup folder chain.
- [ ] **Owner G2 preflight (after CI/review/merge):** `cd ~/bob-next && git pull --ff-only && python3 scripts/report_g2_recovery.py --baseline`. Require `host gate: PASS` or review blockers before modifying startup settings or rebooting. Separately run the existing Windows startup inventory and confirm user-logon vs boot semantics; do not run `wsl --shutdown` or a Windows reboot until the baseline is understood.
- [ ] **Full G2 acceptance remains separate:** after an owner-scheduled reboot/logon, `--postcheck`, Windows startup inventory, both trusted LAN browser connections, and source-linked ledger/receipt comparison. A changed attempted-job count alone is not duplicate proof; zero duplicate evidence in local SQLite alone is not proof that no duplicate Moltbook post occurred.

---

## CH-HTTPS4 credential rotation accepted on OMEN; restart recovery pending (2026-10-31)

- [x] **Live owner CH-HTTPS4 password rotation PASS:** after the deliberate first attempt to reuse the original password (safely refused), the owner ran `python3 scripts/ch_https4_rotate_dashboard.py --apply` with a distinct replacement and received `credential change: APPLIED`, `old password rejected + new password accepted over verified HTTPS: PASS`, and `installed TLS/R3 safeguard recheck: PASS`. The command stated no systemd, SQLite, publisher, or Moltbook action was performed. This proves local/private credential and verified HTTPS new/old checks at rotation time.
- [x] Previous CH-HTTPS4.1 audit `UNCHANGED_OLD_ACCEPTED_NEW_REJECTED` matched the owner's explanation that the initial attempted replacement equaled the old password. No actual password values were shared.
- [ ] **Windows browser acceptance after the successful change:** freshly reauthenticate on both OMEN and second LAN Windows client with the *distinct new* password and without certificate warnings; verify cached old login is rejected. Previously reported successful logins occurred before the accepted change and do not satisfy this gate.
- [ ] **CH-HTTPS4 manager-only restart and recovery:** once both clients pass, run read-only preflight `python3 scripts/ch_https4_rotate_dashboard.py --verify && python3 scripts/report_ch_https3_cutover.py --installed`; require PASS. Separately restart only `bob-activity-manager.service` with `systemctl --user restart bob-activity-manager.service`, then repeat both read-only checks, confirm active systemd unit and HTTPS/new login from both clients. No publisher/Scout/Gateway restart or R3 permission changes.
- [ ] **Distinct G2 Windows/WSL reboot gate:** inspect systemd startup/recovery, LAN-only exposure, independent timers, and no duplicate historical sends. Do not equate manager-only restart with full reboot or authorized R3 posting.

---

## CH-HTTPS4.1: owner hit an ambiguous credential rotation refusal (2026-10-31)

- [x] Owner ran original CH-HTTPS4 `--preflight` with `installed HTTPS, current login and R3 Off: PASS`. A subsequent terminal `--apply` completed hidden prompts but printed `CH-HTTPS4 REFUSED OR INDETERMINATE: CredentialError` rather than an accepted rotation proof. Owner additionally reports both LAN Windows browser logins successful using what they identify as the new password. The sanitized script did not identify where the credential check failed; do **not** assume it wrote, failed to write, or proved rejection of historical login solely from that output.
- [x] CH-HTTPS4.1 adds terminal-only, **read-only** `--audit`: hidden historical/new password prompts; compare stored credentials with real CA/IP-SAN verified HTTPS old/new/anonymous requests; classify `ROTATED_OLD_REJECTED_NEW_ACCEPTED`, `UNCHANGED_OLD_ACCEPTED_NEW_REJECTED`, or `NOT_VERIFIED`. No writes or restart. Adds safe refusal categories for future `--apply` without printing credentials or paths.
- [ ] Owner, **after review + CI + merge**: `cd ~/bob-next && git pull --ff-only && python3 scripts/ch_https4_rotate_dashboard.py --audit` and separately `--verify`; then run CH3 `--installed`. Do not retry `--apply` blindly.
- [ ] After positive credential proof, repeat fresh independent Windows browser tests without certificate warnings, and schedule manager restart and separate G2 Windows/WSL reboot. Keep R3 real publishing compiled Off.

---

## CH-HTTPS3 server acceptance PASS; CH-HTTPS4 owner credential gate staged (2026-10-31)

- [x] **OMEN CH-HTTPS3 acceptance PASS (operator-supplied report):** `python3 scripts/report_ch_https3_cutover.py --installed` returned `acceptance: PASS`, exact installed release verified, CA SHA256 matched, R3 schema/journal/source Off verified, authenticated HTTPS manager/R3 both pass, plaintext HTTP 18790 refused, manager and existing publisher/Scout timers active. Read-only report changed no services, DB or publishing rights.
- [x] Both OMEN and a second Windows LAN computer reported successfully opening the Activity Manager over HTTPS after installing the public CA. Explicit browser *absence of certificate warnings* remains an operator visual confirmation, not remotely proven by the WSL report.
- [x] **CH-HTTPS4 source-only implementation staged for review:** `scripts/ch_https4_rotate_dashboard.py` requires installed CH3 `PASS`, trusted interactive `openclaw` terminal, exact typed consent, old/new/confirm hidden password prompts, atomic existing credential rotation, and negative old-password/anonymous plus positive new-password probes over CA/IP-SAN verified HTTPS. `--preflight` and `--verify` remain read-only. No installed release manifest change.
- [ ] After reviewed CI/merge, run `python3 scripts/ch_https4_rotate_dashboard.py --preflight`; then separately approve `--apply` and verify `PASS`. Do **not** paste secrets into chat, GitHub or shell arguments.
- [ ] Reconnect BOTH Windows browsers with the new password and valid certificate; check the old password no longer works. Check `--verify` after a separately approved manager restart. Confirm LAN-only routing/firewall. Full Windows/WSL reboot and G2 no-duplicate/publisher evidence remain independent gates; no R3 real send authorization.

---

## CH-HTTPS3 HTTPS browser check reported on both LAN systems (2026-10-31)

- [x] **Owner-reported HTTPS client access:** Activity Manager is now reachable by HTTPS from both the OMEN host and the second LAN Windows system after public CA imports. This is a live browser observation, not independent evidence that the host's full CH-HTTPS3 acceptance report passed or that both clients were warning-free.
- [ ] **Final machine-verified CH-HTTPS3 acceptance:** run `python3 scripts/report_ch_https3_cutover.py --installed` as `openclaw` inside `~/bob-next`; require `acceptance: PASS` with exact installed release hashes, R3 Off, CA fingerprint, authenticated HTTPS, and plaintext HTTP rejection. Check there is no browser certificate warning on both computers. Do not turn on R3 manual/automatic publication.
- [ ] **CH-HTTPS4 next:** plan separate, safe rotation of the old LAN Basic-auth password, including updater/manager consistency and two Windows browser reconnections; then reboot/recovery, LAN-only exposure and no-duplicate/publisher checks. Do not rotate password during unresolved CH-HTTPS3 verification.

---

## CH-HTTPS3 OMEN Windows CA trust reported; TLS-only cutover release ready for acceptance (2026-10-31)

- [x] Owner confirmed **public CA imported successfully into the Windows trust store on BOTH the OMEN and the primary remote LAN Windows computer**. Verified source certificate SHA256: `af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196`. This is owner-reported store import, not yet a successful post-switch browser HTTPS handshake.
- [x] Reviewed CH-HTTPS3 TLS-only manager/source extension tested in isolated real localhost TLS fixture (979 Python tests, Windows parse). Preserves existing R3 controls and legacy routes; TLS>=1.2, trusted exact CA/SAN, strict HTTPS Origin/CSRF/Host and no HTTP fallback.
- [x] Promote exact versioned `v0.8.0-chhttps3` from installed `v0.8.0-chhttps1`: only `bob_manager_tls.py` plus generated `bob-activity-manager`, `restart_manager: true`. No publisher, Gateway, Scout, timer, SQLite or R3 consent change.
- [x] Add fixed-host read-only `scripts/report_ch_https3_cutover.py --preflight` before updating and `--installed` afterward; requires owner-pinned public CA fingerprint, valid private cert chain, installed registry hashes, existing manager/timers active, R3 complete+compiled-Off, authenticated TLS 1.2+ manager routes, unauthenticated R3 rejected, plaintext HTTP on old port refused.
- [ ] **Owner CH-HTTPS3:** after CI and merge, `cd ~/bob-next && git pull --ff-only && python3 scripts/report_ch_https3_cutover.py --preflight` must PASS. Next `bobctl update --check` must show exact two-file CH3 release and manager restart yes. Then `bobctl update`, owner typed `UPDATE`; afterwards run `python3 scripts/report_ch_https3_cutover.py --installed` read-only and verify local/remote browsers at `https://192.168.1.24:18790/r3` without warnings. Do not proceed if earlier gates fail. On failure consult updater code-only journal, **never restore old SQLite**.
- [ ] **CH-HTTPS4** browser trust and remote-LAN acceptance, HTTP denial, rotate historical Basic auth password, test post-restart / Windows WSL reboot and legacy publisher no-duplicate evidence. R3 Bob-authored real sending remains separately unauthorised.

---

## CH-HTTPS2 OMEN cert PASS; CH-HTTPS3 source-only candidate (2026-10-31)

- [x] **Owner CH-HTTPS2 local cert acceptance PASS:** independent fixed-host read-only preflight verified CH-HTTPS1 install, no material and eligible; owner typed `PREPARE BOB HTTPS`, private CA/server cert created, three SANs verified (192.168.1.24 / 127.0.0.1 / localhost), disposable TLS handshake and wrong-hostname refusal PASS. Repeat `--verify` read-only PASS. Public CA SHA256 **`af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196`**. No TLS service activated or R3 send rights.
- [ ] **Windows CA trust pending:** on owner's Windows session, compare public `ca.crt` SHA256 from WSL share with above. Import public CA only to Current User Root after deliberate confirmation. Never export private `ca.key` or `server.key`; certificate trust of browser connection only proven after actual TLS-only service.
- [x] **CH-HTTPS3 source-only candidate built:** new `src/lib/bob/bob_manager_tls.py`, additive `scripts/build_ch_https3_manager_candidate.py` over pinned R3 generated UI, and **UNPROMOTED** `releases/candidates/ch-https3-tls-manager.json` with two files `bob_manager_tls.py` + `bob-activity-manager` and `restart_manager:true`. Require fixed private CA/SAN chain and TLS 1.2+ before binding old port; strict HTTPS Origin/Referer/Host, retain Basic auth/CSRF/R3 hard-Off; no plaintext fallback. Real synthetic TLS HTTP tests cover /r3 and legacy routes plus refusal of HTTP, wrong CA, cross-origin and bad CSRF.
- [ ] **Do not promote/install CH-HTTPS3 yet:** independent owner report confirming verified Windows CA import and browser trust store state first; then explicit reviewed release promotion with health/rollback acceptance before switching the live manager. Publish/Scout/Gateway and SQLite remain untouched.
- [ ] **Post-cutover CH-HTTPS4:** confirm `https://192.168.1.24:18790/r3` verified browser lock, no warning, HTTP plaintext refused, all owner actions guarded, second LAN device CA trust, password rotation, reboot/reconnect and no publisher regressions. No real R3 canary consent.

---

## CH-HTTPS2: OMEN certificate provisioning awaiting owner acceptance (2026-10-31)

- [x] **CH-HTTPS1 owner acceptance PASS:** installed release `v0.8.0-chhttps1` verified, R3 schema `ready`, journal `complete`, authenticated existing HTTP manager and R3 owner page pass, no new R3 send rights. HTTP LAN remains unencrypted pending reviewed TLS-only switch.
- [x] Add exact fixed-host `scripts/prepare_ch_https2.py` with read-only default and `--verify`, separately TTY-confirmed `--apply`. ECDSA P-256 root/server private keys created only under owner-private `~/.config/bob-system/manager-tls/`, never overwritten, no existing unit, cert trust or database change.
- [x] Verification requires three SANs `192.168.1.24`, `127.0.0.1`, `localhost`, CA/server roles, key match, 30-day validity margin, real disposable TLS loopback and negative hostname check. CI uses disposable private fixtures and checks symlink/weak permissions/overwrite/refusal.
- [ ] **OMEN owner CH-HTTPS2:** after reviewed PR merge, `cd ~/bob-next && git pull --ff-only && python3 scripts/prepare_ch_https2.py` must show eligible; then the owner separately types `PREPARE BOB HTTPS` under `python3 scripts/prepare_ch_https2.py --apply`, then `--verify` read-only PASS. This is NOT a code release install and does NOT start TLS on port 18790.
- [ ] **Windows trust explicit owner action:** compare the full public `ca.crt` SHA256 printed by WSL against the file seen via Windows WSL share; explicitly import *public CA only* into the Windows Current User trusted root store. Never export `ca.key` or `server.key`. Confirm browser trust only after CH-HTTPS3.
- [ ] **CH-HTTPS3** independently code-review TLS-only manager, secure HTTPS Origin/CSRF, updater postflight+rollback health; **CH-HTTPS4** browser and plaintext refusal tests, legacy LAN password rotation, later restart/Windows reboot G2. No R3 real posting rights.

---

## CH-HTTPS1 OMEN transport-aware updater candidate (2026-10-31)

- [x] **CH-HTTPS0 host acceptance PASS (owner-reported):** `v0.8.0-r3stage1` installed, R3 schema ready and completed journal, manager/publisher timer/Scout timer active, authenticated HTTP /r3, listener LAN/wildcard, no preexisting TLS material. Read-only source preflight PASS; no R3 real-send rights.
- [x] Stage transport-aware two-file candidate `v0.8.0-chhttps1` from installed `v0.8.0-r3stage1`: only `bob-release-updater` and `bobctl`, `restart_manager=false`. No Activity Manager, Gateway, Scout, publisher, SQLite, certificate or service change.
- [x] Pin explicit release-to-transport mapping: installed R3 stage1 and CH-HTTPS1 use authenticated localhost HTTP only; future separately reviewed CH-HTTPS3 uses hostname/IP-SAN-verified HTTPS with fixed private CA; no unrecognized release or TLS handshake downgrade. Updater preflight/candidate/rollback checks use their respective exact reviewed release IDs.
- [x] Add read-only `scripts/report_ch_https1_installed.py` and offline transport/CA validation/rollback/bobctl tests, plus CI gating; HTTPS cert provisioning is **not** part of this release.
- [ ] **Owner CH-HTTPS1 install acceptance:** first `bobctl update --check` to verify exact two files, `v0.8.0-chhttps1`, no manager restart and `v0.8.0-r3stage1` as predecessor; then typed `bobctl update`, then `python3 scripts/report_ch_https1_installed.py` for preserved HTTP /r3, completed Off-schema journal and verified future HTTPS probe. **No TLS switch or owner-mode enablement yet.**
- [ ] **Next CH-HTTPS2:** private CA/server certificate setup and independent browser trust, then CH-HTTPS3 versioned TLS-only manager cutover. Legacy password rotation and Windows reboot tests require later owner gates.

---

## CH-HTTPS0: Secure Bob Activity Manager owner LAN (source audit in progress, 2026-10-31)

- [x] Review current manager, `bobctl`, guarded updater and generated R3 dashboard: HTTP Basic credentials currently cross LAN unencrypted; existing updater/CLI HTTP health checks and strict `http://` Origin verification prohibit a safe one-step HTTPS switch.
- [x] Choose **direct TLS-only on the existing OMEN LAN port `192.168.1.24:18790`**; no internet exposure, second public socket or remote reverse-proxy hop. Preserve original authenticated UI and R3 triple compiled-Off send gates.
- [x] Add `scripts/report_ch_https0.py` with no-write owner/installed schema and journal, three service/timer statuses, authenticated localhost GET, listener/cert metadata; no passwords, private keys or Moltbook API calls. Add offline refusal tests and [HTTPS rollout SOP](docs/CH-HTTPS-ROLLOUT.md).
- [ ] **OMEN CH-HTTPS0 read-only audit:** after CI and source merge, run `cd ~/bob-next && git pull --ff-only && python3 scripts/report_ch_https0.py`; save sanitized report. No user service, browser trust or certificate changes in this checkpoint.
- [ ] **CH-HTTPS1:** reviewed first versioned code-only release to make updater, `bobctl` and acceptance checks explicitly transport aware, with phase-accurate HTTP/HTTPS health and rollback and no TLS switch.
- [ ] **CH-HTTPS2:** owner-local CA/server certificate provisioning, SAN `192.168.1.24`/`127.0.0.1`/`localhost`, private key files and browser trust on OMEN plus laptop; prefer DNS-01 trusted name only if selected separately. Never export CA private key or trust unverified certificates.
- [ ] **CH-HTTPS3/4:** separately approved manager TLS-only cutover on **same port**, HTTPS Origin/CSRF/authenticated health + code-only rollback, proof plaintext HTTP refuses connections, browser trust and LAN-only accessibility. Rotate historical LAN Basic password after verified cutover; no R3 canary or auto publishing enabled.

---

## R3.13d OMEN OFF-first migration and service restoration COMPLETE (owner-reported, 2026-10-31)

- [x] Live schema migrated, independently checked `ready` with journal `complete`; migrated schema preserves **23** historical send attempts, **0** uncertain outcomes and four R3 independent settings `off/0/0/empty`.
- [x] Activity Manager restarted under private maintenance pause; authenticated `/r3` returned expected compiled-Off controls, and `scripts/report_r313d_stage1_installed.py` passed with exact installed `v0.8.0-r3stage1` registry and all three source real-send guards Off.
- [x] **Service restoration accepted:** original publisher and Scout user timers (both `enabled/active` before maintenance) re-enabled and active; manager remained active/healthy; owner checked exact private pause content and removed it **last**. Operator output: `R3.13d: SERVICES RESTORED; MAINTENANCE PAUSE REMOVED`. Legacy Scout/publisher scheduling is restored; independent Bob-authored R3 publishing remains compiled Off. This is an owner report, not direct host introspection.
- [ ] **Later independent checks:** post-resume natural timer run, service-restart/Windows-WSL reboot, no-duplicate/uncertain outcome evidence (G2). No assertion that post-resume scheduled publisher has completed a fresh cycle yet.
- [ ] **Remaining R3 canary prerequisites:** HTTPS or equivalently protected LAN owner actions; independently authorized exact Bob draft+target and one-publisher send cutover, rollback/no-duplicate acceptance. R2 G1 remains independent. Do not rerun live DDL or restore a stale SQLite backup.

---

## R3.13d OMEN post-migration acceptance PASS (operator-reported, 2026-10-31)

- [x] Owner fast-forwarded `next` to `3b0cd9b` (PR #97) and reran read-only post-migration reports. The fixed-host schema report now verifies `installed_off_first_release_verified: true`, `r3_schema: ready`, `journal: complete`, **23** historical attempts, **0** uncertain attempts, private global pause `true`, and real R3 dispatch `false`.
- [x] Independent installed-stage report: `installed release: verified`, `R3 real-send source gates: verified_off`, `authenticated R3 Controls: authenticated_read_only_page`, `installation acceptance: PASS`, no live changes from check, and no Moltbook canary authorization. Manager running makes `publisher_and_manager_drained: false` expected; completed migration makes `eligible_for_off_migration: false` expected.
- [x] **Service restoration completed:** original user publisher/Scout timers returned to `enabled/active` and manager health reverified; private pause removed last. See acceptance checkpoint above.
- [x] **Post-restoration immediate acceptance:** timers active+enabled, maintenance pause removed, manager and installed R3 controls verified healthy and source gates Off. Longer-term natural timer/no-duplicate and G2 reboot recovery remain separate open acceptance gates.

---

## R3.13d live OFF-schema migration applied on OMEN (owner-reported, 2026-10-31)

- [x] Owner drained publisher and manager, disabled publisher/Scout user timers and established private pause; final fixed-host read-only report showed installed stage1 verified, eligible schema, paused+drained yes, journal absent and explicit migration eligible.
- [x] Owner independently typed `MIGRATE R3 OFF` for `scripts/r313d_live_off_migration.py --apply-off`. Tool returned `R3.13d LIVE OFF SCHEMA: APPLIED (owner-confirmed)`, historical attempted sends preserved **23**, historical uncertain **0**, database rollback by stale restore **NEVER**, new R3 publication permissions **NONE**, publisher/manager **STILL STOPPED**.
- [ ] **Post-migration independent read-only acceptance still pending:** check `python3 scripts/r313d_live_off_migration.py --json` for `r3_schema=ready`, journal `complete`, attempts `23`, uncertain `0`, pause true, publisher/manager drained true, installed release verified. `eligible_for_off_migration=false` is correct after successful migration. Do not invoke `--apply-off` again.
- [ ] **Next staged service restoration:** start Activity Manager while private pause remains, run `python3 scripts/report_r313d_stage1_installed.py` and verify authenticated R3 page; only after this passes restore original `enabled+active` publisher/Scout timer states and remove the exact owner-created pause marker LAST. Do not start legacy publisher oneshot by hand. Do not touch Gateway/Shadow. No real R3 canary or automatic permissions.
- [ ] **Ledger follow-up:** prior private snapshot had 22 attempts, live Off migration retained 23. One additional attempted job appeared in the interval while the legacy timer was running; that alone does NOT prove a successful public post. Preserve all records and check source-linked provenance later, without replay.
- [ ] **Remaining R3.13d gates:** secure HTTPS/protected owner LAN route before enabling manual R3 owner mutations, explicit canary/one-publisher G2, reboot/no-duplicate/code-only rollback. R2 G1 remains independent.

---
## R3.13d stage1 OMEN install accepted (operator-reported, 2026-10-31)

- [x] **Guarded updater acceptance PASS:** owner ran `bobctl update --check`, verified exact `v0.8.0-r3stage1` seven-file manifest and Activity Manager restart, then ran `bobctl update` with typed `UPDATE`; result `BOB UPDATE: updated`.
- [x] **Independent installed-host acceptance PASS:** `scripts/report_r313d_stage1_installed.py` returned `installed release: verified`, `R3 real-send source gates: verified_off`, `authenticated R3 Controls: authenticated_read_only_page`, `installation acceptance: PASS`; no changes from this report to database/services and **no new R3 posting rights or canary authorization**.
- [x] **LAN visual acceptance:** owner screenshot shows authenticated `/r3` rendering on `192.168.1.24:18790`; manual owner control OFF, automatic publishing OFF/compiled locked, and no eligible R3 proposals. The read-only notice reflects the **not-yet-migrated live R3 schema**, not a failed stage1 code install.
- [ ] **Small UI copy correction:** after stage1, replace “read-only until separately reviewed OFF-first install” with “read-only until separately authorized live R3 schema migration.” No need to roll a release for wording alone.
- [ ] **R3 sensitive LAN controls security gate:** browser shows plain HTTP (`Not secure`) on LAN; Basic-auth credentials and future owner actions require an authenticated HTTPS endpoint (or equivalently protected private tunnel) before enabling R3 manual mutations. Keep LAN-only and do not open public access.
- [ ] **NEXT independent owner-approved migration gate:** normal-account read-only `python3 scripts/r313d_live_off_migration.py` to identify pause/drain/readiness, then separately scheduled maintenance with exact typed authorization for an Off-only additive schema upgrade. Do **not** run `--apply-off` from this acceptance alone. Real publishing canary and WSL/Windows reboot G2 remain separately pending. R2 G1 natural scheduled source-linked decision remains open.

---

## R3.13d Off-first stage1 release promotion (install acceptance pending)

- [x] Promote the previously accepted `v0.8.0-r3stage1` **code-only** manifest to `releases/current.json` on `next`, chained exactly from installed `v0.8.0-shadow4`. Only seven R3 proposal/dashboard/navigation files are in the manifest; **the credentialed legacy Moltbook publisher and its timer are excluded**. This is not an automatic installation, live schema migration, or real R3 publication authorization.
- [x] Fix trusted R3 ZIP namespace loading: the existing Shadow4 dashboard imports `bob_v08.inspect` first and caches the package path. The new loader now verifies BOTH installed archives against the private updater registry before exposing reviewed R3 submodules to the cached package. Add real LAN Basic/Host/Origin/CSRF localhost HTTP smoke and installed-runtime tests while retaining the production account boundary.
- [x] Add `scripts/report_r313d_stage1_installed.py` as a **read-only** post-install check for exact updater registry SHA, installed binary hashes, three R3 source Off gates, reviewed publisher effective unit, independent R3 consent Off and authenticated `/r3` response. It never changes database, permissions, services or Moltbook state.
- [x] **Stage1 release promotion CI accepted:** PR #93 squash-merged into `next` at `b9445464e67baae6b3469c1ae913b0bcb393bf67`; GitHub Actions run `41215807186` passed **946 Python tests** and Windows startup parsing. `releases/current.json` is now `v0.8.0-r3stage1` from Shadow4 with exactly seven R3 dashboard/proposal files, and no credentialed publisher update.
- [x] **OMEN stage1 code install accepted (2026-10-31):** guarded updater reported `updated`; installed report verified exact release, triple-Off source, authenticated read-only `/r3` and no R3 posting rights. See operator evidence above.
- [ ] **Still separate R3.13d gates:** owner-approved paused/drained maintenance and live Off-only SQLite migration; safe service restart, WSL/Windows reboot; separate exact-post and exact-draft manual canary and G2 no-duplicate recovery. Auto R3 stays compiled Off. R2 G1 natural fresh timer decision remains open.

---

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
