# R4 production-shaped rehearsal and release review

**Status:** R4 canary-aware source checks **PASS**: **1,269 Python tests** plus Windows startup checks on code commit `0eb9342` (GitHub Actions run `41370228129`). **Not an OMEN installation**. In source-only release promotion PR #138,
`next` will advertise `v0.8.0-autonomy1` using the exact separately reviewed
candidate manifest in `releases/candidates/r4-autonomy1-consolidated.json`.
The actually installed OMEN release remains `v0.8.0-r3canary1` until a separate
owner-confirmed updater transaction. No public R4 action is authorized.

## What the isolated rehearsal actually executes

`tests/test_r4_production_shape_rehearsal.py` builds all **23 real candidate
payloads** (including the generated HTTPS Manager) from the candidate manifest,
then exercises the existing updater's real `update()`, filesystem archive,
SHA-256 registry validation, real online SQLite backup and independent restore,
`r4_install_guard`, hash-verified installed schema module, transaction journal,
additive SQLite migration and `rollback()` against a disposable private tree.

The file-backed fixture includes an existing, recorded R3 public-canary comment
and R3 proposal. Acceptance checks:

1. Successful update: candidate hashes, code, exact HTTPS release binding,
   `complete` journal, complete empty R4 tables, no added public send, and
   unchanged legacy R3 publication receipt.
2. Failed candidate HTTPS **postflight**: host boundary deliberately fails after
   migration; updater automatically restores R3 code/registry, while preserving
   the new inert R4 tables and all existing historical records.
3. Process interruption **after `migrated` and before completed restart**:
   the `migrated` journal remains recoverable. Explicit code-only rollback
   restores R3 binaries/registry and **does not overwrite a later attempted
   publication record in SQLite**.

### Real ephemeral HTTPS smoke

`tests/test_r4_https_host_smoke.py` launches the generated R4 Manager on a
**loopback-only ephemeral TLS socket**, with a temporary signed CA and
synthetic Basic credentials, using the original R3/legacy manager stack.
It checks six authenticated R4 GET pages plus legacy routes, rejects missing
authentication and spoofed Host, rejects invalid Origin and CSRF for private
POST actions, prevents on-read schema creation, rejects plaintext HTTP, and
rejects a certificate from an untrusted CA. This harness caught and repaired
the canonical sidebar routing error for R4 subpages before installation.

### What this does NOT prove

This is **not** a second publisher, a Windows/WSL install, a real systemd
migration or a live HTTPS socket test. The transaction test mocks the host service restart and authenticated HTTPS
postflight; the separate socket test supplies genuine TLS/route coverage but
still does not execute a real WSL/systemd service restart. No physical OMEN paths,
credentials, Moltbook API requests, or installed databases are used. The
existing independent R4 route/auth/CSRF and transport tests supplement this
fixture, but cannot replace an actual operator acceptance after deployment.

**Critical release boundary:** the installed R3 updater cannot identify the
new R4 release's HTTPS transport. A promoted, trusted, updated checkout must
run the reviewed `scripts/bob_release_updater.py` for this bridge install.
Do **not** use the old installed updater for R4, manually execute schema DDL,
run the rehearsal against the live database, or copy a SQLite backup over
newer publication attempts.

## Final R3-canary-aware host preflight

An important last-review incompatibility was corrected: the previous R4
`bob_release_updater.py` called `preflight_r3_diagnostics_only()`, whose
historical `_installed_cutover_off()` check deliberately accepts older R3
release identities **but not the actually installed
`v0.8.0-r3canary1`**. An otherwise healthy owner installation would have
been refused before the R4 UPDATE prompt.

The R4 path now calls `preflight_r4_installation()`, which delegates only
to the new **read-only** `scripts/report_r4_preinstall.py --check` and
requires the exact signed R3 canary source, matching `openclaw` owner,
active existing publisher/Scout/R3 proposal timers, inactive original
publisher, disabled shadow and absent competing publisher, reviewed effective
publisher service/timer with no unknown blockers, verified CA HTTPS Manager
and no incomplete updater transaction. It returns *readiness for a distinct
owner prompt*, **not installation approval**.

Importantly, the guarded migration also reruns the original publisher idle,
effective service/timer and competing-worker topology checks **after staging
the exact candidate files and before the additive SQLite transaction**. A
changed/unknown unit fails closed and invokes the normal code-only rollback.
This is not a guarantee against arbitrary subsequent host changes; running
the reviewed report on the actual OMEN remains essential before install.

These checks are offline-mocked in `tests/test_r4_preinstall.py`. The read-only host report was subsequently executed by the owner on the OMEN
(2026-11-01 PDT): **7/7 checks PASS, zero blockers**. It did not stop timers,
disable Scout, change HTTPS, migrate schema or send Moltbook actions.

## Source-to-host handoff (no release promotion)

A consolidated **read-only** check now exists: `scripts/report_r4_go_nogo.py --check`.
It independently runs the complete exact 23-file candidate-source audit and the
live R3-canary-specific OMEN systemd/CA HTTPS/updater-journal gates. The output
contains only named booleans and fixed refusal codes. No host state is changed.
The tested one-paste procedure clones the draft branch into a separate
`~/bob-r4-review` checkout, leaving the trusted `~/bob-next` channel and
installed R3 binaries alone. See [R4 live host check](R4-LIVE-HOST-CHECK.md).

**GitHub CI cannot supply host evidence.** The owner subsequently supplied the
actual OMEN `report_r4_go_nogo.py --check` result (2026-11-01 PDT):
`candidate_files_checked:23`, `candidate_source_verified:true`,
`live_host_readiness_verified:true`, `blockers:[]`, all seven host checks true,
`ready_for_separate_release_review:true`, no changes to host files, SQLite or
systemd, and zero Moltbook API requests. This is owner-supplied observed output,
not evidence of an install. A report PASS does not authorize manifest promotion,
migration or any public social send.

## Promotion-only update (PR #138)

The original source audit ran while `releases/current.json` still pointed to
R3 canary. After the source-only promotion, `report_r4_candidate.py --check`
requires `current.json` to **exactly equal** the reviewed 23-file R4 candidate.
Historical R3 canary tests now use their archived release manifest instead of
mistaking current source promotion for a mutation to the running OMEN host.
`report_r4_go_nogo.py --check` requires the promoted exact current manifest
*and* the unchanged installed R3 canary with its existing HTTPS/one-publisher
systemd topology. The trusted `~/bob-next` checkout must be fast-forwarded
before checking; `bobctl update` from the old installed R3 release is not a
valid bridge to R4. See [R4 promotion and installation](R4-PROMOTION-AND-INSTALL.md).

## Remaining release gates

- [x] Final code source CI on `0eb9342`: **1,269 Python tests** and Windows workflow PASS. The CI path-trigger update also passed: 1,269 Python tests and Windows checks on `2d191b4` (run `41370326709`).
- [x] Review exact 23-file candidate manifest and the independent real-send Off markers in original publisher, adapter, owner-send adapter and outbox. No real R4 dispatch enabled.
- [x] Source R4 preinstall probes review unique original publisher unit/timer, effective unit shape, current R3 canary hashes, existing Scout/R3 proposal schedule and competing-worker absence; migration repeats the topology check.
- [x] Prepare one consolidated source+host check and isolated review checkout, tested with fail-closed synthetic cases; no production modification.
- [x] **Owner-submitted actual OMEN** read-only `report_r4_go_nogo.py --check` PASS on 2026-11-01 PDT, seven host checks true, zero blockers. This is a snapshot, and deployment must recheck the live host.
- [x] Isolated real ephemeral CA-verified TLS socket smoke passed with six R4 routes and legacy routes; Host/Origin/CSRF and plaintext/wrong-CA were refused. Real deployed R4 HTTPS acceptance remains post-install only.
- [x] Add a separate owner-typed **post-`complete`** rollback:
      `python3 scripts/bob_release_updater.py --rollback-r4` accepts only
      a completed exact autonomy1 journal, its archived r3canary1 registry,
      unmodified current source and an inactive original publisher, then
      requires `ROLLBACK-R4` before the existing **code/registry-only**
      rollback. It NEVER restores SQLite. Tested for success, later attempted
      publication preservation, invalid archive and active publisher refusal.
      **Do not invoke until an actual owner decision to roll back.**
      This differs from `--recover`, which remains interruption-only.
- [x] Source PR #137 was merged into `next` after the owner-submitted live host read-only PASS. The separate release-promotion change is PR #138. It does not touch the OMEN installation.
- [ ] One owner-confirmed OMEN R4 install, then read-only
      `python3 scripts/report_r4_installed.py --check` and LAN browser smoke.
- [ ] Independent, subsequent owner decision and new signed release for any
      real R4 upvote/follow/comment/post path. **Installation alone grants no
      real R4 API sends.**

Do not request terminal commands from the operator until the source and
promotion gates are complete. All pending checks must be reported as pending,
not silently implied by passing Python unit tests.
