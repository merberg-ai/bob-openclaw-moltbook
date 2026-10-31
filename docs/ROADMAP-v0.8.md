## CH-HTTPS4 manager restart accepted; G2 Windows/WSL recovery preflight (2026-10-31)

Owner reported successful restart of **only** `bob-activity-manager.service`, which remained `active`. Both pre- and post-restart CH-HTTPS4 credential/current HTTPS/R3 Off gate and installed CH-HTTPS3 TLS integrity/rejected HTTP checks passed, with original publisher/Scout timers active. The separate previously accepted password rotation proved old password denied and new accepted. This is manager-only recovery, NOT full Windows/WSL reboot, fresh independent two-client browser trust, independent startup persistence, LAN-only firewall inspection, or publisher no-duplicate proof.

Source-only G2 read-only `scripts/report_g2_recovery.py` stages distinct `--baseline` / `--postcheck` snapshots of allowlisted unit state, competitor/duplicate scope inertness, legacy publisher effective reviewed unit, current HTTPS/R3 Off and historical attempted/uncertain counts. No host changes; a PASS is a **local host-state gate**, not a reboot witness or external Moltbook receipt audit. Prior Windows discovery found two user Startup-folder items, one invoking an OpenClawLab WSL/systemd wrapper, and system-scope Scout units coexisting with user-scope Scout units: explicit inactive/disabled confirmation must precede a risky reboot. G2 full reboot and source-linked ledger comparison require separate owner observation. No R3 dispatch or canary consent.

---

## CH-HTTPS4 live password rotation accepted, manager restart next (2026-10-31)

The owner confirmed the original CH-HTTPS4 refusal was caused by attempting to replace the password with an identical value, as intended by the fail-closed rule. A read-only audit correctly reported that the historical credential remained active and the alternate candidate was rejected. On a subsequent **distinct** replacement, the interactive CH-HTTPS4 tool reported `credential change: APPLIED`, verified the old password's 401, the new password's authenticated HTTPS 200, and the postflight CH-HTTPS3/R3 safeguards `PASS`. No service, database, publisher or Moltbook action occurred. This is accepted server-side credential rotation, **not yet** two-client post-change browser acceptance or restart recovery.

Next: validate fresh trusted HTTPS logins on BOTH Windows clients, run baseline read-only CH4 `--verify` and CH3 `--installed`, then deliberately restart *only* the Activity Manager user service and repeat those checks and client logins. Full Windows/WSL reboot, startup, LAN-only exposure, and ledger-based publisher/no-duplicate evidence remain distinct G2. Installed release remains `v0.8.0-chhttps3`; no R3 posting authorization.

---

## CH-HTTPS4.1 rotation refusal recovery gate (2026-10-31)

The owner reports original CH-HTTPS4 interactive rotation returned `REFUSED OR INDETERMINATE: CredentialError` despite `--preflight` PASS and successful new-password browser access reported on two Windows computers. There is no accepted old-password rejection proof from that command. Stage CH-HTTPS4.1 to diagnose with non-mutating, hidden-prompt `--audit` comparing exact private local credentials and real CA-verified HTTPS statuses, and replace unhelpfully generic future refusal errors with fixed-safe categories. Keep all live services, installed `v0.8.0-chhttps3` release, SQLite, certs and R3 permissions unchanged. Do not blindly repeat rotation; require audited old 401/new 200/anonymous 401, then independent restart and G2 evidence.

---

## CH-HTTPS3 formal TLS acceptance PASS; CH-HTTPS4 credential rotation is next (2026-10-31)

Owner supplied the sanitized fixed-host `report_ch_https3_cutover.py --installed` result: **`acceptance: PASS`**. The verified CH-HTTPS3 release, private public-CA SHA256, authenticated HTTPS manager and R3 page, source-Off/migration-journal guarantees, original active timers, and refusal of plaintext HTTP all passed. The owner previously confirmed browser HTTPS reachability from both OMEN and second LAN Windows computer; no-warning browser verification is a distinct visual check.

CH-HTTPS4 now stages a **source-only**, exact-host terminal rotation tool over the existing private `lan-auth.json` credential store. Require CH-HTTPS3 PASS before and after, old-password verification and explicit typed operator consent, new-password verification on CA-validated HTTPS, 401 old/anonymous and 200 new. Never restart anything for the credential change. New credential persistence across separately approved manager restart, both Windows browsers, LAN-only exposure and G2 reboot/no-duplicate evidence remain open. `releases/current.json` stays `v0.8.0-chhttps3`; **no Bob R3 send authorization** is conveyed.

---

## CH-HTTPS3 two-system HTTPS browser access observed (2026-10-31)

After importing the public Bob CA on both Windows machines and promoting `v0.8.0-chhttps3`, the owner reports the Activity Manager **appears to work over HTTPS on both the OMEN and the second LAN computer**. This is reported live-client reachability, not yet the comprehensive post-install `scripts/report_ch_https3_cutover.py --installed` output. Leave final CH-HTTPS3 acceptance open until the report verifies installed hashes, completed R3 Off schema, private CA fingerprint, authenticated HTTPS and **plain HTTP refusal** on port 18790; separately confirm neither browser presents a certificate warning. No claim is made that an additional password rotation, reboot test or R3 publishing consent has occurred.

Next after final TLS acceptance: **CH-HTTPS4** old LAN Basic password rotation under a reviewed recovery plan, reconnect both Windows clients, then service/WSL reboot recovery and publisher/no-duplicate validation.

---

## CH-HTTPS3 owner trust accepted, TLS-only versioned cutover gated (2026-10-31)

Owner reported successful Windows public CA Root imports on both OMEN and main remote LAN computer, using Bob's public CA with previously verified SHA256 `af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196`. Actual browser acceptance is still pending until the TLS service is live.

The tested candidate is now promoted to versioned release `v0.8.0-chhttps3` from accepted `v0.8.0-chhttps1`, containing **only** `bob_manager_tls.py` and the generated `bob-activity-manager`, `restart_manager:true`. Authenticated local HTTPS with fixed private CA and IP SAN, HTTPS Origin/CSRF policy, and refusal of plaintext HTTP are mandatory. The updater performs old HTTP preflight, new HTTPS postflight and original HTTP code-only rollback on failed installation. Never restore a stale SQLite database, interrupt publisher or enable Bob R3 real sends.

New source-only reports: `scripts/report_ch_https3_cutover.py --preflight` before the owner-typed update and `--installed` after. They verify CA SHA256 and private certs, installed binary hashes, migrated R3 schema/Off source, existing timers, authenticated manager and TLS-only endpoint. The separate CH-HTTPS4 client/browser test and password rotation remain open. See [CH-HTTPS rollout](CH-HTTPS-ROLLOUT.md).

---

## CH-HTTPS2 OMEN certificates verified, CH-HTTPS3 candidate under review (2026-10-31)

Owner successfully created the local private certificate material using the separately confirmed CH-HTTPS2 script and verified it again with read-only `--verify`: SANs 192.168.1.24, 127.0.0.1 and localhost; valid chain, private keys, synthetic TLS handshake and wrong-hostname rejection. SHA256 of the **public** `ca.crt`: `af47c380af49eaf5b51683eb2cb1b6455eba019e754e09e295a0a3eeedc1f196`. Existing Activity Manager remains HTTP; Windows browser CA import is unconfirmed.

A source-only CH-HTTPS3 candidate extends the existing pinned R3 manager with a fixed owner-controlled TLS certificate verification module, TLS1.2+ socket on the existing port, strict HTTPS-only Host/Origin/CSRF and authenticated old+R3 routes. Its release manifest is only at `releases/candidates/ch-https3-tls-manager.json`, **not `releases/current.json`**, so `bobctl update` must remain `v0.8.0-chhttps1`. Promotion and installation require confirmation of deliberate Windows public CA Root import and a separate reviewed rollback/end-to-end TLS acceptance plan. No R3 public dispatch authorization.

---

## CH-HTTPS2 guarded local certificates under review (2026-10-31)

The owner independently accepted CH-HTTPS1 installed on OMEN (`v0.8.0-chhttps1` exact hash and R3 triple source Off; manager HTTP and authenticated `/r3` healthy; schema `ready`/journal `complete`). **HTTP remains in service** while CH-HTTPS2 prepares locally trusted certificate material. A read-only-by-default `scripts/prepare_ch_https2.py` preflight first checks that exact installed release and no existing private material is present. Owner must separately type `PREPARE BOB HTTPS` before generating a brand-new local CA and server key/cert with P-256 ECDSA keys, exact three SANs, short one-year leaf validity, private restrictive file modes, OpenSSL chain/key/SAN/role verification and disposable loopback TLS handshake with wrong-hostname rejection. Afterward a separate `--verify` is read-only. Existing manager service, timers, SQLite, updater registry and publication controls remain untouched.

Windows Current User root trust of **only the public CA certificate** is a later explicit owner action after comparing WSL and Windows public CA SHA256; installing a private CA as a root has broad trust implications and should not be done blindly. This phase does not install the TLS-only server or secure the current HTTP transport. CH-HTTPS3 manager cutover and CH-HTTPS4 LAN/browser verification remain distinct. Full SOP: [CH-HTTPS rollout](CH-HTTPS-ROLLOUT.md).

---

## CH-HTTPS1 transport-aware updater staged without changing dashboard transport (2026-10-31)

CH-HTTPS0 OMEN owner inventory passed: installed `v0.8.0-r3stage1`, schema `ready`, journal `complete`, authenticated manager /r3 over **still-unencrypted HTTP**, both schedule timers and manager active, certificate material not prepared. The next versioned candidate `v0.8.0-chhttps1` is exactly two code files, `bob-release-updater` and `bobctl`, with no manager restart or publisher change. The guardrails reject unknown release transport, certificate/CA permission errors, missing IP SAN and TLS handshake failure without HTTP fallback. The updater uses pre-upgrade HTTP, post-upgrade release-specific transport, and a release-specific code-only rollback health protocol; `bobctl` independently verifies the installed manager's registry hash before selecting a protocol.

This *prepares* the safe upgrade/rollback machinery. **It does not make current LAN HTTP encrypted**. Owner code-only CH-HTTPS1 install and independent verification remain required, followed by private CA/SAN provisioning/trust and a **separate** CH-HTTPS3 TLS-only manager release. See [CH-HTTPS rollout](CH-HTTPS-ROLLOUT.md). R3 real sending remains compiled Off.

---

## CH-HTTPS0: private LAN dashboard HTTPS rollout design (2026-10-31)

Following successful R3.13d Off-schema migration/restoration, the next security milestone is **HTTPS-only access to Activity Manager at the existing OMEN `192.168.1.24:18790`**. The owner-approved direction is direct TLS on the existing Python HTTP server, not another WAN listener or a remote reverse proxy that forwards Basic credentials in plaintext. Existing dashboard uses HTTP Basic authentication over unencrypted LAN traffic. Existing updater and `bobctl` health checks hardcode HTTP, and strict manager Origin/Referer checks require `http://`; a naive one-release socket wrap would fail update/POST acceptance.

Phases are intentionally independent: **CH-HTTPS0** read-only fixed-host inventory (no install or key generation), **CH-HTTPS1** transport-aware updater/health code-only prep release, **CH-HTTPS2** owner-private cert plus trusted client CA/SAN check, **CH-HTTPS3** reviewed TLS-only manager release on same port with strict HTTPS Host/Origin/CSRF and no HTTP fallback, **CH-HTTPS4** Windows/LAN browser, plaintext rejection, credential-rotation and rollback acceptance. Automatic Bob R3 publishing and manual Moltbook canary remain Off/unauthorized. Details and one-command readiness check: [CH-HTTPS rollout](CH-HTTPS-ROLLOUT.md).

---

## R3.13d OMEN live schema and service restoration accepted (2026-10-31)

**Off-first stage1 host acceptance complete** by operator report. A verified `v0.8.0-r3stage1` install is running with the additive R3 schema `ready`, migration journal `complete`, **23** historical attempted sends preserved, zero uncertain states and the four independent R3 owner settings explicitly Off. The authenticated Activity Manager `/r3` page passes the installed report with three source real-send gates `verified_off`. Owner then restored the original publisher+Scout timers, both `enabled/active`, and removed the owner-created private pause **last**, receiving `R3.13d: SERVICES RESTORED; MAINTENANCE PAUSE REMOVED`. The existing legacy v0.7 scheduling may resume while R3 real publishing remains disabled.

**This milestone closes the live Off-schema migration/restore only.** It is not a new R3 public comment, distinct canary approval, post-resume natural publisher acceptance, reboot G2, or authorization for R3 auto. Remaining work: secure LAN owner controls (HTTPS/protected tunnel), exact-draft manual canary and reviewed one-publisher dispatch gating, plus restart/reboot and no-duplicate evidence. Keep existing 23 attempted rows; never restore an older database over newer history. R2 G1 remains open.

---

## R3.13d OMEN post-migration independent acceptance PASS (2026-10-31)

Operator supplied fixed-host JSON after merging PR #97: the corrected phase-aware installed gate is **true**; migrated R3 schema `ready`; migration journal `complete`; 23 historical attempted sends preserved and 0 uncertain; global pause active; no R3 dispatch or canary authorization. The separate authenticated stage1 report verified exact installed release hashes, three R3 send gates Off, R3 Controls HTTP page, and `installation acceptance: PASS`. Manager restart means `publisher_and_manager_drained=false`; already-completed migration means `eligible_for_off_migration=false`, both expected.

**Next:** restore only the two pre-maintenance `enabled/active` owner timers while preserving pause, recheck them and the manager, then remove the owner-created pause **last**. The legacy publisher resumes its original behavior, but no new R3 comment can be sent. Do not rerun DDL or restore a stale database. Future R3 owner HTTPS, manual exact-draft canary, safe reboot G2 and R2 G1 remain distinct open gates.

---

## R3.13d OMEN live Off-schema migration applied; service restore pending (2026-10-31)

Owner supplied read-only fixed-host readiness showing `v0.8.0-r3stage1` verified, schema eligible, publisher/manager drained, private global pause active, migration journal absent and explicit Off migration eligible. The operator then ran the separately reviewed terminal-confirmed `--apply-off` command, typed `MIGRATE R3 OFF`, and reported the successful `APPLIED` result. Legacy attempted count **23** preserved, uncertain count **0**, new Bob R3 publication rights **NONE**, and publisher/manager still stopped. **This is an owner-reported successful live schema operation, not a post-restart service/canary acceptance.**

The earlier private backup had **22** attempts, whereas the live migration preserved **23**. The difference occurred between checkpoints with the legacy publisher timer active and is not proof of public publication. Never discard or rewind the 23 attempted records. Next: read-only `r313d_live_off_migration.py --json` verifies ready schema, complete journal, pause and counts. Then restart only Activity Manager under pause and pass the authenticated installed R3 Controls check, restore original two timer states, remove pause last. No blind re-run of migration, no old SQLite restore, no new R3 publishing permission. Secure LAN owner actions before future consent, and preserve separately authorized canary/reboot/G2 and R2 G1 gates.

---
## R3.13d OMEN stage1 installed and accepted (2026-10-31)

Owner report confirms `bobctl update --check` found the reviewed seven-file `v0.8.0-r3stage1` release from Shadow4. After explicitly typing `UPDATE`, the guarded updater returned `BOB UPDATE: updated`. A subsequent independent `scripts/report_r313d_stage1_installed.py` returned `installed release: verified`, `R3 real-send source gates: verified_off`, `authenticated R3 Controls: authenticated_read_only_page`, `installation acceptance: PASS`, and **no new R3 public posting rights or Moltbook canary authorization**. Owner screenshot shows `/r3` rendering via the private-LAN manager with independent manual OFF, automatic compiled OFF and no Bob drafts. These are owner-provided point-in-time reports, not independent host access.

**Stage1 code installation accepted; live R3 schema is still absent.** The screenshot's “until ... OFF-first install” notice is outdated UI copy, not evidence of an install failure. Fix in a later reviewed release. The browser also shows ordinary HTTP; prior to allowing sensitive R3 mutations, require HTTPS (or a protected tunnel) while retaining authenticated LAN-only access. No public exposure or credential changes are authorized by this checkpoint.

**Next:** separate maintenance authorization for the fixed-host additive **Off-only** live schema migration after normal-account read-only `scripts/r313d_live_off_migration.py` review, paused/drained sole publisher and manager, restore-tested backup and typed terminal confirmation. Do not issue `--apply-off` just because stage1 passed. Automatic real sends remain Off. Manual exact-draft canary and Windows/WSL reboot G2 remain distinct gates; R2 G1 is still pending.

---

## R3.13d Off-first stage1 promotion CI accepted (2026-10-31)

PR #93 squash-merged into `next` at `b9445464e67baae6b3469c1ae913b0bcb393bf67`. GitHub Actions run `41215807186` passed **946 Python tests** and Windows startup-script parsing, including authenticated LAN HTTP/CSRF/Host/Origin smoke of the generated Activity Manager with the existing Shadow4 ZIP and registry-verified R3 ZIP. The full release chain is explicitly constrained to `v0.8.0-shadow4` → `v0.8.0-r3stage1`, exactly seven files, **no publisher executable or timer**.

**Source release promotion complete; actual OMEN installation NOT yet complete.** The operator must separately confirm `bobctl update` and then pass the read-only `scripts/report_r313d_stage1_installed.py`. No live SQLite migration, new R3 publication permission, one-publisher canary or Windows/WSL reboot acceptance is implied. [Installation SOP](R313D-STAGE1-INSTALL.md). Source triple-Off publishing gates unchanged.

---

## R3.13d Off-first stage1 release promotion (owner installation still pending)

After the owner-reported OMEN `report_r313d_off_first.py` PASS, the `v0.8.0-r3stage1` owner-code manifest is promoted from `releases/candidates/` to `releases/current.json` on `next` for a separately confirmed code-only install. It upgrades `v0.8.0-shadow4` and installs exactly seven R3 dashboard/proposal/runtime/navigation files, **no legacy publisher binary, timer, Moltbook credential or automatic-send switch**. The generated Activity Manager keeps the established R2 Shadow/OC4/FM4.1 routes, LAN Basic auth, strict Host/Origin/CSRF. Two reviewed ZIP archives are verified against updater hashes before the new R3 modules are added to Python's cached `bob_v08` package path; installed-style authenticated localhost HTTP smoke covers this integration.

The guarded updater still requires a clean trusted `next` checkout, exact release chain, verified SQLite backup, typed `UPDATE`, service restart/health and automatic **code-only** rollback on failure. It **does not** apply live database DDL. After actual host installation, `scripts/report_r313d_stage1_installed.py` verifies registry hashes, installed publisher, three hard-Off R3 source gates and authenticated `/r3` page without any write. Operator instructions: [R3.13d stage1 install](R313D-STAGE1-INSTALL.md).

**Stage1 still needs explicit OMEN installation acceptance.** Do not run the separate `r313d_live_off_migration.py --apply-off` yet. It requires a distinct paused/drained owner-approved maintenance window and restore-tested backup, and only adds Off schema. A real manual Moltbook canary requires a further exact-draft owner authorization, publisher cutover gate and reboot/no-duplicate G2 acceptance. R3 auto remains Off. R2 G1 remains open.

---

## R3.13d OMEN Off-first candidate review PASS (2026-10-31)

The owner ran `python3 scripts/report_r313d_off_first.py` on the OMEN/OpenClawLab WSL host. The **read-only** report returned `candidate build: PASS`, `existing release: v0.8.0-shadow4`, `three R3 real-send gates: OFF`, `installed host boundary: eligible`, and `eligible for separate owner install review: yes`. No live database, installed file, service, R3 posting right or Moltbook canary authorization changed. This is **operator-supplied, point-in-time pre-install acceptance**, not evidence of successful installation or live migration.

**Next gate:** distinct owner-approved promotion of candidate `v0.8.0-r3stage1`, with a safe code-update rollback and verified installed release. The existing publisher must remain the only credentialed sender. Subsequent *separate* owner-approved paused/drained SQLite Off migration and manual exact-draft canary, challenge/no-retry, reboot and G2 remain open. No `bobctl update` or `--apply-off` is authorized by this read-only PASS. R2 G1 remains open.

---

## R3.13d production SOURCE checkpoints accepted (2026-10-31)

PR #89 merged the **Off-first owner-controls and real OpenClaw sealed-proposal source**, with 932 Python tests green and Windows startup validation. The original pinned Activity Manager remains untouched, the generated dashboard extends existing R2/OC4/FM4.1 routes, and automatic Bob-authored publishing remains compiled Off. The new `v0.8.0-r3stage1` file manifest is **noncurrent** under `releases/candidates/`; no installed executable or live database changed.

PR #90 merged the **separately gated owner-confirmed live Off-only schema migration source** at `ea8f3506a336a3616e5fe64b829d583f86f3d922`, with **941 Python tests** and Windows startup parsing green (GitHub Actions `41213864893`). The default CLI remains read-only and refuses any live write until the exact stage1 code release is independently approved and installed, the publisher timer and services are drained, a private restore-tested SQLite backup and durable journal are available, and an interactive owner types `MIGRATE R3 OFF`. This adds only Off schema, never Bob R3 permission.

**Owner OMEN acceptance and public cutover NOT yet completed.** The next safe checkpoint is `python3 scripts/report_r313d_off_first.py` on the host after `git pull --ff-only`. `releases/current.json` still points to `v0.8.0-shadow4`. Owner-accepted stage1 promotion/install, actual paused/drained Off migration, separately approved exact-draft one-publisher canary, WSL/Windows reboot/no-retry acceptance and R2 G1 all remain open. No blind real POST or automatic R3 posting may be enabled.

---

## R3.13d separate guarded live OFF migration candidate (source only)

The production boundary is **not** a `bobctl update` side effect: `src/bob_v08/r313d_live_off_contract.py` applies R3.5 and R3.13c additive DDL in one SQLite transaction with explicit Off R3 owner keys and a complete legacy history digest, and `scripts/r313d_live_off_migration.py` is the only fixed-host operator command allowed to run it. Its default operation is read-only. The separately approved interactive `--apply-off` requires the installed Off-first code release and verified updater hashes, source triple-Off guard, owner-private pause, disabled and inactive publisher timer, inactive publisher and manager services, an exclusive updater lock, and a restore-tested private backup. The durable `prepared/complete` journal blocks unknown recovery, and an older SQLite backup is **never** automatically restored over later attempted or uncertain sends. No service is stopped/restarted by the tool; no Moltbook network path is added.

The normal operator review after source merge is the read-only `scripts/report_r313d_off_first.py` plus `scripts/r313d_live_off_migration.py` (which should report the Off-first release not yet installed). The actual stage1 manifest is still under `releases/candidates/`; `releases/current.json` remains `v0.8.0-shadow4`. See [Off-only live migration SOP](R313D-LIVE-OFF-MIGRATION-GATE.md).

**Not yet complete:** owner-approved Off-first promotion/install, maintenance-window live schema operation, accepted running services, separately authorized manual exact-post Moltbook canary and WSL/Windows reboot/rollback G2. All real R3 dispatch switches stay Off; automatic R3 publishing remains Off. R2 G1 remains open.

---

## R3.13d Off-first production controls and proposal-writer candidate (source review)

The next production-side implementation builds the authenticated Owner R3 Controls on top of the **full** R2 Shadow/FM4.1/OC4 manager **without modifying its pinned v0.6 source or older handlers**. R3 manual permission and exact per-Bob-draft approval are independent of legacy Scout. The dashboard requires typed confirmation for manual enablement and queueing an exact draft; disabling cancels only unattempted R3 jobs. R3 automatic publishing remains **compiled Off**. A fixed local proposal-only worker invokes the original OpenClaw Bob agent on saved Scout evidence, validates a strict action contract, and writes only an independently sealed envelope plus proposal. It never creates a publish job or network request.

The new R3 package uses a deterministic versioned archive independently hash-verified against the private updater registry, without altering the Shadow4 zip. The candidate `v0.8.0-r3stage1` manifest is kept **in `releases/candidates/` only**, installs the owner UI/runtime and navigation through the existing code-rollback updater, and excludes the credentialed legacy publisher. A source+host read-only audit is available at `scripts/report_r313d_off_first.py`. See [operator guide](R313D-PRODUCTION-OFF-FIRST.md).

**Not yet production cutover or installation:** `releases/current.json` remains `v0.8.0-shadow4`. A later separately reviewed owner promotion, verified live schema migration in a service maintenance window, explicit real manual canary, WSL/Windows reboot and code-only rollback are required. Automatic Bob-authored publishing is still Off. R2 G1 independently remains pending.

---

## R3.13d OMEN operator private-stage acceptance PASS (2026-10-31)

The owner executed the merged `next` fixed-host R3.13d source audit and separately invoked `--private-copy` on the OMEN/OpenClawLab WSL account. The source audit reported trusted queue boundary, matching legacy schema, absent/Off R3 owner consent, reviewed installed publisher service shape, owner-controlled regular executable and matching private updater registry hash; the **three source-level publication gates remained Off**, with no boundary/source blockers and staging eligible.

The disposable SQLite online-backup migration reported **PASS** for the versioned action-envelope schema, explicit default-Off controls, pre-commit crash rollback, idempotence and preservation of old records. The snapshot contained **22 historical send attempts** and **0 historical uncertain states**; a new synthetic uncertain attempt persisted through the code-only rollback check. The copied DB was deleted. The output states live database, installed files, units, consent, R3 dispatch and cutover authorization **unchanged/Off**. This is an **owner-supplied point-in-time private-stage acceptance**, not a production migration, live send verification or installed release attestation of new R3 binaries.

**R3.13d staging gate accepted. Production gates remain open:** independently authenticated owner R3 Controls and trusted proposal producer, reviewed versioned release/maintenance/drain/live migration, explicit owner-authorized real one-publisher canary, reboot, no-duplicate uncertainty recovery and code-only rollback. `releases/current.json` remains `v0.8.0-shadow4`, and R2 G1 is still open.

---

## R3.13d source-stage CI accepted (2026-10-30)

PR #86 squash-merged into `next` at `776ad1eac51a8b0f631fc543856a0d34ab4765ad`. GitHub Actions run `41174232285` passed **922 offline Python tests** and Windows startup-script parsing. The versioned envelope migration/proposal writer can modify only a marker-locked disposable SQLite fixture, the host script only reads installed state unless `--private-copy` is explicitly invoked, and all three source-level R3 dispatch gates remain hard Off. `releases/current.json` stays `v0.8.0-shadow4`; the installed legacy publisher, units, owners and live database remain unchanged.

**Next acceptance:** normal OMEN WSL account runs the read-only `scripts/report_r313d_host.py` and, if eligible, the private-copy versioned migration rehearsal. This is staging verification only; full R3.13d production cutover, R3 owner-controls page and writer, real canary, WSL reboot and code-only rollback still need a separate versioned owner-controlled rollout.

---

## R3.13d staging-first engineering candidate (source-only, no cutover)

R3.13d begins by rehearsing the full **versioned additive migration** on a marker-locked disposable copy of the existing SQLite queue. It applies the accepted R3.13b default-Off R3 controls and the new R3.13c action-envelope/schema-version tables, verifies legacy attempts/history, simulates crash rollback and repeated migration, and confirms code-only rollback cannot erase a newer synthetic uncertain attempt. A private fixture-only source-linked proposal writer demonstrates the complete independently sealed original Bob action/WHY while refusing to create a live publication job. The host audit verifies reviewed effective publisher service/timer, installed owner-controlled executable, updater registry hash and all three reviewed hard-Off source switches.

**This is a stage gate, not production completion:** no release install, real SQLite migration, authenticated owner R3 settings or proposal writer, real publisher activation, canary, WSL reboot or new public Moltbook write. The existing updater does not implement live schema upgrades, so a separate owner-approved controlled transition with a verified private backup and recovery journal is required. [R3.13d staging guide](R313D-STAGING-OFF.md). `releases/current.json` still points to `v0.8.0-shadow4`; `main` remains the stable baseline.

**After source CI and OMEN snapshot acceptance**, finish the R3.13d production gates: authenticated default-Off manual/auto controls and exact sealed proposal writer; versioned code package with one credentialed publisher only; explicit owner-authorized maintenance, database migration, canary, startup/reboot and no-duplicate/code-only rollback. R2 G1 source-linked natural scheduled decision is also open.

---

## R3.13c source-only merge accepted (2026-10-30)

PR #84 merged into `next` at `1b13dd7f12c597adffd282f4dc9757df463eb1f6` after passing **911 offline Python tests** and Windows startup-script parsing in CI run `41169512190`. The existing legacy publisher's default R3 hold path and clean installed import remain compatible. The source candidate introduces the prospective same-publisher R3 action path and persistent envelope contract but **three hardcoded source-level Off gates** block production R3 import/dispatch. The installed `v0.8.0-shadow4` release, credentialed v0.7 publisher, owner consent and live SQLite schema have not changed.

**Next: R3.13d** must separately review the versioned additive action-envelope migration, authenticated proposal writer and owner R3 controls, installed-unit/credential boundary, explicit owner-authorized canary and WSL reboot/code-only rollback before any new Bob-authored Moltbook comment. R2 G1 remains independently open. No on-host command is required for this source-only acceptance.

---

## R3.13c prospective single-publisher send branch, hard Off

The existing publisher executable contains a prospective Bob-authored R3 branch behind **three source-level production-Off gates** (including a lazy import guard), preserving the v0.7 Scout queue path and v0.8 Shadow4 installation. Source review found a missing provenance datum: R3.5 proposals store Bob draft seal/fingerprint but not the original action **reason**; older R3 tests used a marked private descriptor, which must never supply live authority. R3.13c adds a versioned canonical action-envelope contract independently validated against the saved Scout source and original seal.

The candidate reuses one legacy `publish_jobs` attempted-at ledger with manual-first priority, R3.9 pinned exact-post/author GET, independent R3.13b permissions, verified source/friends/owner/pause/budget checks, atomic durable intent, final post-intent pre-POST barrier, human-only challenges and no-retry uncertain outcomes. API acknowledgment is not independently verified public visibility. CI uses only a marker-protected synthetic database, fake GET and fake POST; the actual publisher remains Off.

**Not an installed release:** no real action-envelope migration, authenticated producer/UI, R3 credentialed POST, new owner permission, unit or live schema changes. R3.13d must address schema migration, UI/producer, versioned staged cutover, owner consent, canary, reboot/rollback and post-challenge reconciliation. [R3.13c guide](R313C-ONE-PUBLISHER-OFF.md). R2 G1 remains open.

---

## R3.13b OMEN owner acceptance PASS (2026-10-30)

The owner ran the merged `next` R3.13b installed-source audit and the independently requested `--private-copy` upgrade rehearsal on the OMEN/OpenClawLab WSL host. The read-only audit reported a trusted queue boundary, matching legacy schema, no installed R3 consent (`absent_off`), reviewed publisher systemd unit shape, an owner-controlled regular installed executable, **verified updater registry hash**, no source or boundary blockers, and the expected difference between the legacy installed binary and the unreleased `next` candidate.

The disposable SQLite copy reported **PASS** for the schema and default-Off R3 owner-control upgrade, crash rollback, repeat migration, complete old history preservation, and code-only rollback that retained a newly simulated uncertain attempt. Existing historical send attempts: **22**; existing uncertain outcomes: **0**. The temporary copy was deleted. This is the operator's sanitized point-in-time acceptance, not an independent live inspection, proof of 22 confirmed public comments, or authorization to change production. **No live DB change, installed publisher change, new R3 manual/auto posting rights or cutover.**

**R3.13b accepted; next R3.13c:** develop/review real single-publisher R3 admission and final safety checks with authenticated owner controls, but remain compiled Off until a separately authorized release, canary and reboot/rollback gate. R2 G1 remains open.

---

## R3.13b source-only upgrade/consent and publisher executable attestation

The R3.13a owner-accepted host boundary is extended by a reviewed R3.13b **noninstallable** source contract. A marked disposable SQLite copy receives the R3.5 additive proposal/approval/audit tables and four separately named default-Off R3 controls in one transaction; unknown/active preexisting consent fails closed, and all old jobs, decisions, attempts and uncertain-delivery history remain intact. The migration and code-only rollback are rehearsed only on private copied real-queue and synthetic SQLite. A simulated new uncertain attempt after the upgrade cannot be lost by restoring an older database; this phase permits no DB restore.

Independent R3 consent inspection is source-only: manual requires `r3_manual_enabled=1`, compatible `r3_comment_dial` and owner approval bound to the exact Bob draft seal; automatic comments require separate `r3_auto_enabled`, valid `r3_auto_since`, existing v0.7 auto permission and source newer than the R3 opt-in. No dashboard permission UI/setter or production R3 post path is installed; returns never authorize dispatch. A read-only host tool also checks the exact effective publisher service/timer, installed executable ownership/path, updater registry hash when tracked, and difference from the future uninstalled next source without printing paths, secrets or hashes. Untracked binaries require later review rather than implying release attestations.

**Status:** source-only contract merged and owner OMEN acceptance passed (see above). [R3.13b operator guide](R313B-UPGRADE-CONSENT-ATTESTATION.md). `releases/current.json` still Shadow4, R3.12 real dispatch hard Off, existing v0.7 publisher unchanged, no new owner posting rights. **Next R3.13c** reviewed real single publisher send admission/final barrier plus independent authenticated owner UI; **R3.13d** separately authorized stage/canary/reboot/code-only rollback. R2 G1 still pending.

---

## R3.13a OMEN operator acceptance PASS (2026-10-30)

The operator ran the merged `next` `scripts/report_r313a_host.py` read-only check and its separately invoked `--private-copy` rehearsal in OpenClawLab. The host check observed: fixed Moltbook data root; queue file private; pause not paused; legacy schema match; additive schema absent; R3 owner settings absent/off; private-copy eligibility yes; effective legacy publisher service and timer both reviewed shape; boundary and unit blockers none. The private snapshot migration reported **PASS**, preservation of complete legacy history, simulated crash rollback, repeat-migration idempotence, 22 **historical send attempts** and zero uncertain delivery states; the temporary copy was deleted. These are operator-supplied point-in-time sanitized results, not independent continuous service or public-post confirmation.

**Accepted gate:** R3.13a installed-root review and disposable real-queue copy migration rehearsal. **Not accepted:** actual live schema upgrade, installed publisher binary/source attestation, new R3 owner consent, authenticated real R3 send/GET, Windows/WSL reboot, canary, rollback, or R2 G1. Existing v0.7 real publication remains the only authorized dispatch path, and R3.12 Bob-authored dispatch stays hard Off. No `bobctl update` is required by this documentation checkpoint.

**Next R3.13b:** design/test versioned additive migration and independent owner-control contract, source/unit integrity attestation and fail-closed upgrade/rollback model in isolation; separate owner approval remains mandatory before any production modification or new Moltbook post capability.

---

## R3.13a trusted source-root review and real-queue private-copy migration rehearsal

A new fixed-host R3.13a audit observes the current WSL account's existing Moltbook queue / Scout-data / pause roots, validates owner-only directory and file permissions, existing legacy schema and absent R3 tables, and categorizes independently controlled R3 settings without reading secret credentials or dumping raw content. It composes the pre-existing sanitized R3.8 effective-unit view. It reports that installed publisher binary attestation remains unverified and never grants send authority.

The optional --private-copy rehearsal uses SQLite's online backup API to snapshot committed live queue/WAL records into a throwaway 0600 file in a 0700 temporary directory. It verifies the private copy and original five-table history, simulates rollback of an interrupted additive DDL transaction, then applies R3.5-compatible schema to the COPY ONLY and verifies idempotence and every prior attempted/uncertain row. There is no production schema change, credential/API request, publisher/service update or release. All execution flags for R3 comments remain Off. The source candidate is noninstallable; owner OMEN read-only/private-copy acceptance was recorded above. See [R3.13a guide](R313A-HOST-PRIVATE-MIGRATION.md).

**Next R3.13b:** independently review real installed-source integrity, owner approval UI, migration/rollback before any installation. Then R3.13c/d real final GET/consent/pause barrier and separately approved canary/reboot. R2 G1 remains independently pending.

---

## R3.12 actual publisher mixed-queue adapter, hard Off and isolated fake-credentialed POST

The existing credentialed `src/bin/bob-moltbook-publisher` now imports `bob_r312_adapter.py` for **queue selection only**. With no R3 proposal table it executes the original legacy selection SQL; with a valid additive R3 table it excludes Bob-sealed rows from Scout-only validation and holds them untouched, while approved legacy jobs continue through the old `load_record`, budget, preflight, durable intent, credentialed POST and challenge/unknown handling. Malformed R3 schema fails closed. Real R3 send remains compiled Off (`R312_REAL_DISPATCH=False`), even if test owner flags claim Auto.

An explicit `--r312-fake-credentialed` CLI option on the same executable uses a marker/private-fixture-only R3.9/R3.10 preflight and atomic claim, R3.8 final safety barrier and a strictly in-memory fake authenticated POST-shaped transport. Tests exercise the real publisher selector and executable under mocked credentials/GET/POST, double-worker claims, verified source/consent, successful fake ACK, challenge, timeout and no replay on unknown outcome. There is **no actual Moltbook request, API key read, second publisher or installable release**. `releases/candidates/r312-adapter-off.json` is noninstallable source metadata and `releases/current.json` remains Shadow4. [R3.12 design/acceptance](docs/R312-DISABLED-PUBLISHER-ADAPTER.md).

**Next R3.13:** installed-host authenticated data boundaries, additive schema in verified private copy, independently authorized new R3 permission and reviewed production send adapter; only then a versioned owner-approved canary/cutover and reboot/rollback test. R2's naturally timed source-linked model decision remains separate open evidence.

---

## R3.11 actual publisher executable inert rehearsal (source-only)

This phase connects R3.10's atomic claim to the **same existing executable** as the real v0.7 credentialed publisher, but only through explicit inert test subcommands accepting a fixed, marker-verified private synthetic queue and sealed action descriptor. Tests run the real `src/bin/bob-moltbook-publisher` entrypoint as a subprocess, run the R3.9 source/owner/friend/GET reviews with synthetic fake GET, commit one counted `sending_simulated` send intent, perform the last R3.8 synthetic source/pause barrier and call an **in-memory fake sink**. A separate inert recovery subcommand marks interrupted possible sends uncertain, never automatically retrying. Two concurrent entrypoint processes cannot both dispatch the fake sink. The normal `publisher_step()` was compared to its pre-R3.11 `next` baseline and found byte-for-byte identical.

**No live release or consent change:** `releases/candidates/r311-inert-only.json` is noninstallable source metadata only; `releases/current.json` stays on Shadow4, the OMEN's credentialed v0.7 publisher remains untouched, and real R3 auto permission is absent. A synthetic success is never a real POST or dispatch authorization. Next: R3.12 review of a disabled-by-default production adapter within one publisher, trusted transport and final-barrier security, plus code-only rollback and an explicit owner-authorized install. [Detailed R3.11 guide](docs/R311-INERT-PUBLISHER-ENTRYPOINT.md).

---

## R3.10 one-writer atomic queue claim rehearsal (source-only)

Implemented `r310_atomic_claim_lab.py` and focused regressions to join R3.9's **read-only** sealed Bob-origin/publisher GET check with the publisher's durable claim pattern. The only accepted database is the fixed, marked, private R3.3 synthetic fixture; its `scout` source root and pause marker are derived from the fixture rather than supplied by model or UI. A two-pass review encloses an injected HTTPS GET, then the publisher-side simulation locks the same legacy-shaped queue using `BEGIN IMMEDIATE`, rechecks owner settings and exact independent Bob seal under that lock, confirms manual-first FIFO/attempted target/budgets/friends/pause, and atomically commits `sending_simulated`, one `attempted_at` and an audit. A failure rolls back all writes. Two competing claims cannot both win. A crash after commit or source/pause change after intent leaves the attempt permanently locked or `uncertain`, never auto-replayed.

**R3.10 is NOT installed or a permission grant.** The GET and clock remain injected test harness functions, the existing v0.7 publisher still validates only Scout drafts, and `claimed_simulated` explicitly sets `dispatch_authorized=False`/`acted=False`. SQLite cannot atomically lock external friend/Scout files or global pause while making a network POST, so actual deployment still requires immediate final pre-POST barriers and safe unknown-result handling. R3.11 should develop a disabled-by-default, versioned publisher-owned implementation patch with an inert transport harness and explicit owner cutover review.

---

## R3.9 read-only production-shape publisher admission review, no dispatch

Added a publisher-side, **non-dispatch** R3 review in `src/bob_v08/r39_publisher_review.py`. The adapter operates on a caller-supplied publisher-shaped SQLite connection, accepts only a separately sealed Bob-authored proposal linked to valid saved Scout feed/report bytes and an exact queued, unattempted legacy-shaped `publish_jobs` row, and reads independently stored R3 consent, manual approval, friend directory, owner pause, manually prioritized queue and existing v0.7 attempted-send limits. Its GET client accepts only a validated post UUID, connects to a hard-coded `www.moltbook.com` HTTPS host, refuses redirects/oversized/bad identity responses, and never sends credentials. The two-pass local review detects owner/friend/queue/source/budget changes across GET, returning **`dispatch_authorized=False` even when reviewed**. Every HTTP test uses fake connections, with zero live Moltbook traffic.

This is a meaningful **source contract**, not a production authorization. The module is not imported by the current v0.7 publisher, and a caller-provided connection, source root, clock or pause marker is not itself authenticated host evidence. Real dispatch still requires a reviewed, atomic publisher-owned source validation and intent transition, durable history/unknown locks, exact production unit/restart ownership and a versioned release with **separate owner approval of R3 auto actions**. R3.10 is the disabled-by-default single-publisher integration rehearsal. Installed Shadow4 and current v0.7 publication permissions remain unchanged.

---

## R3.8 operator effective-unit acceptance (2026-10-30)

The owner ran the reviewed read-only systemd unit audit on OpenClawLab after merge of PR #74. It reported **effective publisher service: `reviewed_shape`**, **timer: `reviewed_shape`**, **0 service drop-ins**, **0 timer drop-ins**, **1 environment declaration**, **no review blockers**, and **R3 cutover authorized: NO**. This marks the R3.8 **point-in-time effective-unit-shape gate accepted**. The observed environment declaration is intentionally not exposed; no installed units or posting rights were modified. This confirms the conservative service and timer shape check, **not** credential isolation, real dispatch readiness, a Windows/WSL reboot acceptance, or permission to publish Bob-generated comments.

**R3.9 next:** preserve the current single credentialed publisher and owner permission boundaries while designing an isolated real-publisher admission adapter for independently sealed Bob-authored drafts. Real authenticated GET, fresh friend evidence, final pre-POST pause/consent/CAS and versioned rollback are still outstanding. Do not infer automatic R3 consent from the enabled v0.7 auto setting.

---

## R3.8 simulated dispatch and one-writer recovery, plus effective-unit read-only audit

The R3.8 code-only stage now tests the post-intent lifecycle in one marked synthetic SQLite queue. R3.7's trusted-boundary rehearsal records a durable `sending_simulated` + `attempted_at` before any in-memory `InertSink` call. R3.8 separately rereads owner auto consent, saved-source seal, private friends roster, pause marker and remaining strict budgets before the sink; a revoked boundary conservatively locks the consumed attempt. Fake acknowledgments are only `acknowledged_simulated`; fake challenge responses require human verification; timeouts and malformed responses become `uncertain_simulated`. Process crashes on either side of the sink are recovered without replay, and a code-only rollback retains all attempted/uncertain history. All tests remain local with no actual API or credentialed transport.

`scripts/report_r38_effective_units.py` is a separate metadata-only **real-host read-only** tool that parses the effective installed publisher `.service` and `.timer` units (including `ExecStart=` drop-in resets) using two fixed `systemctl --user cat` calls. It reports only yes/no reviewed-shape classifications, drop-in/environment directive counts and sanitized blocker codes, never path or secret values. See [R3.8 operator check](docs/R38-DISPATCH-RECOVERY.md). This owner evidence remains pending until actually run.

**Not cutover-ready:** `InertSink` is not an authenticated Moltbook client; R3.7's GET remains injected test proof; real v0.7 publisher only accepts Scout drafts; host-installed unit/drop-in semantics, worker drain/reboot and independent owner opt-in remain outstanding. Installed Shadow4, legacy queue, existing publisher and R3 permissions remain unchanged.

---

## R3.7 trusted publisher admission gate, synthetic only

`src/bob_v08/r37_trusted_gate_lab.py` now rehearses the publisher-owned boundary with **two independent stored-state checks** bracketing an injected, synthetic GET callback. It requires a valid R3.6 Bob-authored sealed proposal, exact pinned Scout evidence, an unattempted queued job, separate persisted R3 auto consent, persisted owner dial, post-opt-in source, current v0.7 attempt policy, no manual-first queue priority conflict, verified private friend roster and global pause marker. External preflight must report exact target **and** consistent author (no missing ID treated as success), non-deleted result and bounded clock gap. Any change after the GET rechecks, with strict refusal. The only positive path produces a `sending_simulated` entry inside the existing marked private R3.3 SQLite fixture; no Moltbook POST or live dispatcher exists here. Manual-only mode requires separate approval of Bob's own comment seal.

**R3.7 is NOT live authentication or cutover acceptance.** The injected GET and clock are controlled by the test harness, not real trusted transport; file-system and SQLite state can still change between the final rehearsal read and an actual network send. Existing v0.7 remains the sole credentialed publisher and still rejects Bob-authored proposal seals. Next: R3.8 effective-unit/owner-host evidence and production-like isolated dispatcher harness, then explicit opt-in and rollback gates.

---

## R3.6 operator host-readiness acceptance (2026-10-30)

The owner ran `python3 scripts/report_r36_host_readiness.py` from updated `~/bob-next` and provided the sanitized output. It reported **legacy publisher timer active / service inactive**, Shadow4 timer and startup-reconcile timer active, candidate publisher and legacy system-scope Scout timers inactive; legacy queue schema `match`, posting policy `valid`, pause `not_paused`, legacy auto comments `enabled`, **22 historical attempted sends**, **0 delivery states requiring review**, `baseline consistency: observed`, and `review blockers: none`. This completes the R3.6 **point-in-time operator snapshot gate**. It is not a cutover approval, a public publication count, a proof of reboot continuity, or evidence the new R3 code can dispatch.

**Next R3.7:** review the effective installed service/drop-in topology and authenticated data sources, then implement and offline-test a publisher-owned trusted source/owner/friend/GET/pause admission contract. Keep existing auto-comment consent separate from any future R3/Bob-authored comment consent; preserve one credentialed writer and uncertain send history. No live adapter or new v0.8 permissions have been deployed.

---

## R3.6 source-only real-host inventory and draft origin contract

The R3.6 change adds a read-only, bounded **installed-host data collection script** using `systemctl show` on fixed Bob unit names and SQLite `mode=ro`, with a concise printable summary and optional sanitized JSON. It observes current publisher/shadow/reconcile state, legacy SQLite schema, validated posting limits, pause, historical attempted and uncertain counts. The collector cannot toggle services or grant permissions, and its `cutover_authorized` field is always false. It is **not deployed** by an updater and requires a single owner-run check in the separate `~/bob-next` source checkout for real-host acceptance. See [R3.6 host review](docs/R36-HOST-READINESS.md).

A separate read-only `r36_admission_contract.py` verifies saved Scout evidence and classifies only exact matching queued legacy Scout drafts or new Bob-authored drafts with a matching R3 sealed proposal. It is **not** a publisher, does not load credentials, check real external friend/GET state, modify an installed DB or authorize a POST. The existing v0.7 publisher is unchanged. The final live approval, preflight, ownership and rollback requirements remain R3.7+ engineering. A completed natural timer-driven R2 model decision is still independently pending.

---

## R3.5 private schema migration, reboot and code-only rollback lab (source-only)

The next cutover rehearsal includes an additive transactional synthetic migration from v0.7-shaped queue tables to the R3 proposal/owner-approval schema, under a strict private fixture marker. Tests cover existing history preservation, idempotence, unrecognized schema, SQL crash mid-DDL and rollback without reverting subsequent uncertain publication attempts. A separate pure reboot evaluator rejects two active publisher owners, split timers/workers, unverified startup reconciliation and candidate auto-resume; the stage systemd templates are reviewed in-memory for timer-to-service linkage only. `scripts/rehearse_r35_deployment.py` reports an expected denied unauthorized activation and rollback with no actual systemd or HTTP action.

**Not a production readiness signal:** we have not checked the current installed OMEN unit definitions or actual database bytes; no trusted live GET/friend adapter, versioned migration installer, worker drain/restart, or production publisher support for Bob-authored seals exists. The developer branch remains `next`, installed release `v0.8.0-shadow4`; natural timer-driven R2 model decision remains pending.

---

## R3.4 offline source trust and cutover ownership rehearsal (CI candidate)

A source-only rehearsal now verifies **authentic locally saved Scout feed/result bytes** with the reviewed R2 `read_observation()` at proposal, queue and final simulated intent, rejecting source and action drift, missing/changed hashes and symlink files. R3.3 rechecks a **separate persisted owner comment dial** in the same synthetic SQLite transaction, preventing model input from silently upgrading Propose to Auto or ignoring revocation after queueing. The inert cutover state machine refuses dual publishers, active legacy worker cutover, unknown owner authorization and unproven backup/rollback; a simulated code-only rollback keeps historical attempts and uncertain state intact. `scripts/rehearse_r3_cutover.py` provides a small deterministic deny-and-rollback report, with no systemd access.

This demonstrates the engineering design, **not a trusted production adapter or actual systemd cutover rehearsal**. Synthetic `Proof` from the harness is never a real network GET or verified friend response. Current v0.7 publisher would still reject new Bob-authored sealed drafts, and `releases/current.json` remains Shadow4. Next R3.5 builds a reviewed production-adapter *contract* and isolated migration/service-template rehearsals before any host install or new owner permission.

---

## R3.3 unified handoff prototype (source-only, CI candidate)

Implemented a **single synthetic SQLite ledger** for new Bob-authored comment sealing, independently approved manual drafts or separately enabled/dated automatic drafts, manual-first legacy queue selection, actual shared v0.7 attempted-send limits, v0.8 policy and permission recheck, and final compare-and-swap to `sending_simulated` with one attempt and one audit row. Unknown outcomes lock against retry. Concurrent claimants serialize under `BEGIN IMMEDIATE`; SQL audit failures roll back the entire synthetic attempt. No `releases/current.json`, worker or credential code is changed. Default Shadow4 remains Off/Shadow.

**R3.4 next:** no production cutover yet. Build the trusted-publisher adapter and cutover *design/rehearsal* for genuinely verified Scout origin, private consent, real friend/GET proof, startup/timer ownership, migration and code-only rollback. The existing live v0.7 publisher cannot simply process these new Bob-authored seals. The owner must explicitly authorize any installation and new automatic action category, after isolated dry-run reviews. Distinguish R2's successful scheduled service/no-event tick from the still-unverified naturally timer-driven *model decision*.

---

## R3.2 compatibility experiment: legacy queue and owner approval in one simulated transaction

The R3.2 code/review stage now includes a **synthetic-only legacy publisher queue harness**, separate from the R3.1 reservation experiment. It validates legacy v0.7 manual-first queued drafts, owner decisions, queue/source integrity, auto_enabled, friend preflight gating, existing budget module and unknown outcomes against an explicitly private fixture, plus an independent v0.8 policy check. Success produces only `sending_simulated` and `attempted_at` inside the disposable lab DB, never a credentialed POST. Synthetic SQL fault injection proves both intent and audit entry roll back.

**Blockers before R3 cutover:** reconcile the two lab implementations into one authoritative, durable real publisher-side reservation mechanism; validate Bob-authored text as a **new** sealed draft rather than assuming an existing queued legacy draft is the same text; inspect real timing/approval, paused, friend, source and preflight state at the correct boundaries; retain original manual first and unknown delivery locks. No production queue mutation, service change, model tool permission or new Moltbook write authority is part of R3.2. R2 natural timer-driven model-decision evidence is still pending separately.

---

## R3.1 isolated reservation lab (implementation under offline CI)

The next R3 engineering slice is implemented on `next` as an **uninstalled, synthetic-only reservation engine**. It exercises `BEGIN IMMEDIATE` SQLite serialization, one-target idempotency, conservative simulated budget/spacing consumption, final source/content/policy recheck, owner disabling and changed budgets, UTC rollover, uncertainty locking and transactional rollback. Only metadata hashes and bounded state transitions live in the separate lab DB. No network write path or permission grant is added, and no existing v0.7 queue or production service is touched. The positive fixture uses an explicitly synthetic policy where `shadow=false`; installed Shadow4 remains shadow-only.

This is **not** R3 cutover readiness. Next is trusted legacy source-of-truth mapping and transaction bridging, plus simulated race, failure and rollback rehearsals before any opt-in host cutover. The naturally scheduled R2 model-decision confirmation remains a distinct pending evidence check.

---

## R3.0 source-only inventory started; R2 17:30 tick produced no events

A new `scripts/report_r3_cutover_inventory.py` is under reviewed CI with focused offline tests, for **read-only metadata-only** cutover analysis. It is not deployed and does not authorize a cutover. It reads only the allowlisted user/system unit states and aggregated queue/settings metadata, with bounded error categories, no credentials or publication calls.

For R2, owner separately confirmed automatic `bob-v08-shadow.service Result=success` at 17:30 PDT and a read-only SQLite query across that two-minute period found **0 new shadow events**. This is consistent with no fresh verified selection; exact return reason cannot be established from absence of events or exit code. Do not count it as a scheduled model decision. Await naturally arriving sources. Manual real OpenClaw decision and isolated MD1 experience review remain accepted.

---

## R2 scheduled service execution verified (2026-10-30, 17:30 PDT)

**Owner-supplied systemd proof:** `bob-v08-shadow.timer` listed `LAST Fri 2026-10-30 17:30:05 PDT`, `NEXT Fri 2026-10-30 17:51:12 PDT`, and its oneshot `bob-v08-shadow.service` showed `Result=success` with matching start and exit timestamps `17:30:05 PDT`. This completes the **timer-trigger and service-execution gate**, unlike the earlier screenshot showing only a future scheduled time.

**Outcome still needs classification:** `src/bob_v08/shadow.py:main` prints one sanitized JSON result and exits 0 for a processed valid shadow decision, `no_new_verified_sources` and a recorded `model_invalid_or_unavailable` outcome. Therefore `Result=success` alone does **not** prove a timer-driven OpenClaw decision occurred. Inspect a bounded `journalctl --user -u bob-v08-shadow.service` entry from 17:30 or a later natural run. No replay, database resets or new external permissions to force an outcome.

R2's real manual agent decision and owner-approved MD1 one-shot experience review have separately passed. Remaining G1 work is representative scheduled-result inspection and accurate source-bound semantics. R3.0 source-only inventory can proceed while the shadow timer operates without Moltbook writes.

---

## MD1 one-shot experience check: real-host success with interpretation gaps (2026-10-30 PDT)

The owner invoked `bobctl shadow-experience` and typed `ASK-BOB` on the installed OMEN. The real OpenClaw main agent answered privately using the six most recent source-verified saved Scout selections from `bob_v08.digest`. The answer linked six post IDs, named their observed times and titles, distinguished no matching publisher record, queued and failed publisher states, and explicitly marked public visibility unknown/not rechecked. It did not invent a friendship, public reply or confirmed publication. This proves **one isolated opt-in private experience review works**, not persistent Gateway recall, PM2 memory, independent online verification or all-history knowledge.

**Interpretation polish tracked in TODO:** `publisher_failed` alone does not establish a network send; inspect `attempted_at` (and uncertain send states) before attributing an actual attempt. Clearer language must distinguish Bob observing third-party posts from Bob publishing comments, and limit negative conclusions to the six provided records. The user-visible answer cited post IDs but not source-run IDs despite the prompt; add both in future. The console contained high-bit encoding artifacts (``, ``) requiring UTF-8 handling review. No raw private model output should be saved to Git.

**Remaining R2/G1 gate:** confirm at least one timer-driven Shadow4 service invocation and any new evidence-linked event or honest `no_new_verified_sources` result. No new v0.8 Moltbook write authority is authorized. The distinct R3.0 read-only engineering inventory may proceed in parallel, but no cutover to a new publisher is authorized.

---

## Current host checkpoint: R2 Shadow4 working manually, scheduled acceptance still open (2026-10-30)

**Owner-verified:** `v0.8.0-shadow4` installed and activated on OpenClawLab with independent versioned archive and user timer; the real OpenClaw main agent produced a validated `comment` decision on source run `20261030T200610Z` and target `a9ccf436-c5d5-4849-af92-843670ab8271`. Policy returned `deny / action_off`, with `acted:false`, so the shadow system **did not write to Moltbook**. The Activity Manager read-only Now/Inbox screens surfaced matching source-linked events. Old failed model outputs are retained as historical events. This is *manual decision acceptance*, not a grant of publication authority.

**Confirmed schedule, not execution:** `systemctl --user list-timers --all bob-v08-shadow.timer` reported `NEXT Fri 2026-10-30 16:08:11 PDT`, `LEFT 33s`, and `LAST -`. The current UI's `Next reported run: not reported` derives from reading only `NextElapseUSecRealtime`, not the monotonic next-run schedule. The reporting fix is tracked in root `TODO.md` as **R2-UI-SCHEDULE** and should be batched with later UI work, not deployed as another R2 emergency release.

**R2/G1 still requires:** a confirmed naturally scheduled shadow tick with evidence-linked event/service execution; representative additional successful observed ticks or honest no-source outcomes; and the real agent's isolated `bobctl shadow-experience` read-only MD1 session showing source-grounded, properly limited claims. Do not infer scheduled completion from timer activation or a next-run estimate. Never replay failed sources or touch v0.7 publication records to force acceptance.

**Next engineering preparation while G1 closes:** begin R3.0 read-only cutover inventory and safety-contract design: map existing v0.7 Scout/publisher/job-service control and permissions, define managed timer ownership before cutover, transactional reservation and final send recheck, unknown-outcome suppression, source-linked public verification and exact rollback/recovery. Do not enable two active external dispatchers, silently disable the working v0.7 workers, or increase automatic authority. No R3 install is authorized by this roadmap update.

**Preserve source topology:** `next` from clean `~/bob-next` is the development/update source; `~/bob-main` had a prior dirty-checkout incident (issue #57) and must not be used for branch switching. `main` stays the separate reviewed v0.7 baseline. The original planning text below is retained for design history and is superseded on host status by this checkpoint.

---

## R2 shadow4 contract correction (2026-10-30)

- Shadow3 installed and ran one manual shadow tick on the owner's OMEN with timer inactive; it recorded `model_reason_empty` for `20261030T224204Z`.
- The old error ledger defaulted action label to `skip` even for invalid replies; it was not reliable evidence of Bob's intended action. The last model response was not retained.
- Candidate shadow4 permits a reasonless but properly source-bound `skip` as a truthful abstention, while rejecting reasonless `comment`; event logs distinguish unexplained abstention and genuine verified proposed error kind, using `unknown` when kind cannot be proven. The model remains OpenClaw main agent; no additional permissions or network side effects. Use a two-file immutable release chain `shadow3 -> shadow4`, without Activity Manager restart.
- Keep shadow timer inactive until a real owner-reviewed `shadow_decision` is observed. Never conflate accepted skip with approval to comment.

---

## R2 shadow3 reason-contract acceptance candidate (2026-10-30)

- The owner installed and manually tested `v0.8.0-shadow2` successfully with shadow timer inactive; the newest verified source (`20261030T210137Z`) failed strict validator with `invalid_model_reason`, not a transport or source-target error. Raw field contents were deliberately not saved, so root condition among empty/oversized/control chars is unknown.
- Proposed `v0.8.0-shadow3`: explicitly request a single-line reason of 1..200 characters, preserve hard 220-character cap, emit safe separate failure codes and keep all other policy/transport checks unchanged. Two-file chained shadow-only release from `v0.8.0-shadow2`, no dashboard restart or new Moltbook actions. Synthetic validation and operator acceptance are both required.
- Avoid the broken same-checkout branch switch (issue #57). Source updates on the verified separate `~/bob-next` checkout only. Do not activate the timer until an operator-reviewed manual `shadow_decision` succeeds.

---

## R2 host acceptance and targeted transport repair (2026-10-30)

- Owner successfully installed `v0.8.0-shadow1` using a **separate clean `~/bob-next` checkout** after the previous branch-switch implementation repeatedly staged partial R2 changes on main (tracked in issue #57). Activity Manager served its authenticated Shadow Now/Inbox routes, versioned shadow timer activated, and read-only evidence linked to six saved Scout selections. No R2 external Moltbook writes occurred.
- Manual shadow decision and a scheduled tick recorded `invalid_or_unavailable_model_output` against verified sources. An isolated OpenClaw CLI test proved `--json` returns `status=ok` and a valid reply nested at `result.payloads[0].text`. Shadow1 omitted `--json` and treated stdout as an exact JSON object, a likely transport mismatch (the original raw output was not retained; issue #58).
- Candidate `v0.8.0-shadow2` is a narrow chained maintenance release, not R3. Fixes envelope extraction with no loosened target/content policy, fixed-category safe error reporting, and a versioned archive activation path requiring deliberate shadow1 deactivation first. Existing shadow events remain; no automatic replay of old failures. Host acceptance is still required after green CI.
- Leave `main` at the established reviewed R1 baseline. Do not use the faulty branch switch or disturb `~/bob-main`. Keep using the verified separate `~/bob-next` source.

---

# Bob v0.8: autonomy refactor and controlled migration

**Status:** adopted development direction, planning only. No production deployment is authorized by this document.
**Prepared:** 2026-10-30. **Stable branch:** `main`. **Future integration branch:** `next` (create only after the channel-aware updater is installed).
**Baseline:** operator-accepted `v0.7.7-fm41-social1`; `releases/current.json` declares `from: v0.7.6-oc41-polish1`. GitHub `main` at planning time: `63a2af6de4739b37b8edb4edfc321276ac26a7eb`. Reconfirm both the installed host release and Git commit before starting R1.

## Engineering status after R1 acceptance (2026-10-30)

- **R1 accepted by the owner:** `v0.7.8-updater2`, with FM4.1 catch-up from the actual OC4.1 registry; no need to repeat its release commands.
- The `next` branch is now based on that reviewed code. **No R2 installation has been authorized or deployed.**
- First internal R2 implementation: source-verifiable old Scout selections, a narrow OpenClaw main-agent shadow decision, pure policy checks, independent append-only metadata events, bounded MD1 digest, and read-only Now/Inbox rendering. These are not yet a working Gateway chat bridge or independent Moltbook exploration loop.
- Integrated R2 source includes reproducible ZIP packaging, explicit versioned activation, shadow user timer, authenticated read-only web pages and one-shot private experience review. CI passage is not proof of host installation. A persistent context bridge for normal Gateway sessions still needs separate safe session scoping.
- The `next` integration candidate contains a staged `v0.8.0-shadow1` manifest; this does **not** imply installed or operator-accepted status. Do not instruct the owner to switch channels until PR/CI acceptance.

## R2 integration gate (source complete; host acceptance pending)

The R2 candidate now includes source-backed hypothetical decisions by the real OpenClaw main agent, pure default-Off policy, sealed Scout evidence, private append-only shadow events, bounded MD1 digest, a deterministically packaged importable archive, authenticated read-only Now/Inbox views, real read-only shadow timer status, an **explicit** reversible versioned user-systemd shadow timer activation, and an owner-requested **one-session** MD1 experience review using the real OpenClaw main agent, without touching global workspace memory. No new Moltbook publication code, credentials, or action authorization ships.

Integration source and synthetic rehearsal are not proof of operator deployment. The next gate is a fully green reviewed PR/CI, the exact `v0.7.8-updater2 → v0.8.0-shadow1` manifest path, then a minimal owner-controlled update, timer activation, and source-linked session-scoped OpenClaw experience acceptance. General Gateway/CH1 ongoing chat context remains future work because workspace-wide `MEMORY.md` injection would affect unrelated agent sessions. See [R2 operational contract](OPERATIONS.md).

**Packaging deviation from the original proposal:** R2 uses the already-tested v1 guarded updater to place a flat reviewed ZIP and launchers, then a separately authorized activation copies that exact archive to a verified versioned directory and registers only the shadow user timer. Generalized v2 manifest-driven multi-service migrations remain future work. This lets the owner keep the agreed four software-release checkpoints without silently widening the v1 updater or risking the v0.7 publisher.

## Goal and operating contract

Build **one Bob**, not separate agents with inconsistent personalities. The existing OpenClaw Bob (identity, personality, and deliberately bounded experiential context) makes small, independent decisions about Moltbook. A centralized, deterministic policy layer determines whether those decisions may be proposed or executed. A credentialed publisher alone performs external writes. Verified observations and outcomes become explainable experience, not invented memories.

The owner should review an understandable digest, adjust permissions and budgets, and use an immediate pause control, **not approve every individual action**. That outcome is deliberately phased in: no new authority is inferred from existing permissions.

**Keep:** the current PM1 personality; PM2 reviewed memory and opt-in recall; FM1–FM4.1 friends, interest proposals, and read-only social timeline; OC0–OC4.1 diagnostics; source-sealed scouting; manual queue and original-post approval; existing separately enabled auto-comment authority; publisher intent-before-POST, verification, and no blind retries; private credentials; dashboard authentication/CSRF; LAN-only operation; systemd/Windows startup; and `bobctl update`.

**Freeze:** v0.7.7 as the initial working production state. No destructive cleanup, service replacement, schema rewrite, permission widening, or change to `releases/current.json` in this planning PR. The live installation changes only through a future explicitly approved release.

## The four-operator-upgrade plan

This is **four deployable checkpoints**, not four code commits. Engineers may use as many internal commits, reviews, and automated tests as necessary, but do not require the owner to install every intermediate PR. A release needs passing CI, a written before/after contract, a rehearsed recovery path, and one concise acceptance checklist.

| Checkpoint | Branch / proposed release | Integrated deliverable | Owner acceptance |
| --- | --- | --- | --- |
| **R1. Safe foundation** | `main` / `v0.7.8-updater2` | Backwards-compatible channel-aware updater; compatibility with existing v1 manifests; v2 manifest validation; verified backups, install/recovery prerequisites; config and release checks. No changes to agent behavior or publication. | One `bobctl update`. `bobctl update --check` and dashboard status still work; original release chain remains installed; no new services. |
| **R2. Shadow Bob** | `next` / `v0.8.0-shadow1` | Versioned shadow archive with explicit activation; event log and legacy read projections; narrow action schema and pure policy evaluator; restricted real OpenClaw Bob decision adapter; **read-only MD1 experience review in one isolated agent session**; global shadow mode; Now/Inbox first pass. Full transactional reservations and generalized updater v2 are R3 prerequisites before publication cutover. Existing v0.7 workers remain authoritative. | One explicit channel-selection step (must install nothing), then one `bobctl update`. Show source-linked would-be decisions, skipped reasons, digest evidence, and **zero v0.8 Moltbook writes**. |
| **R3. Guarded cutover** | `next` / `v0.8.0-cutover1` | One loop dispatches allowed comment/reply decisions via the existing credentialed publisher; legacy conflicting decision timers are disabled by managed service transition; existing manual review and original-post approvals retained; verified parity of budgets, queue states and permissions; diagnostics and Bob/Controls views connected. | One `bobctl update`. Confirm one eligible controlled workflow **only if separately permitted**, safe pause/recovery, no duplicate publication, and rehearsed rollback. |
| **R4. Social autonomy and usable UI** | `next` / `v0.8.0-autonomy1` | Full Now, Inbox, Bob, Controls (+ Diagnostics); voluntary evidence-grounded interest/relationship reflection; opt-in automatic original posts, upvotes, follows/unfollows **only for verified supported Moltbook endpoints**; digest and anomaly notes; responsive 380px UI. Preserve a reserved first-class Chat route for later CH1. | One `bobctl update`. New categories default Off or Propose; separately opt into each Auto mode after shadow evidence. Demonstrate an accurate digest, bounded activity and pause. |

**Total planned production releases: four** (plus a single non-installing channel switch). No calendar-driven 1–2 week shadow requirement: pass the evidence gates below with representative natural ticks and fault rehearsals. A platform feature lacking a verified API remains **Off/not implemented**, not silently simulated.

After R4 acceptance, merge reviewed `next` back to `main` and return the updater channel to `main` through an explicitly tested, non-deploying transition. Do not assume that an arbitrary checkout switch is safe during a release transaction.

## Runtime architecture

```text
read-only Moltbook observers / sanitized existing Scout evidence
                         |
            append-only observed events
                         |
     real OpenClaw Bob: small JSON decisions
   (bounded source IDs, prompts and read-only digest)
                         |
            canonical action validator
                         |
   centralized policy engine: Off / Propose / Auto
       + independent global Shadow / Pause
                         |
     atomic reserve/idempotent dispatch ledger
                         |
       existing credentialed publisher
            |                     |
  verified Moltbook outcome    human proposal Inbox
            |
   event ledger + source-linked projections
      Now / Inbox / Bob / Controls / Diagnostics
```

**Tick:** one scheduled, bounded observe → decide → validate → check → reserve → act → verify → record cycle. The starting cadence may be 20 minutes, but timings are configured and bounded, never inferred from an eligibility clock. Split the local 9B model's task into small choices (reply to one existing reply, comment on at most one discussion, follow someone, skip). Skip is a legitimate decision. The loop must not give the model tools or credentials to bypass policy.

**Same Bob:** use the current OpenClaw agent identity and stable personality sources, but isolate scheduled decision sessions from human Gateway chat sessions. Make the read-only verified experience digest available in appropriately opted-in **fresh** Gateway sessions. Never substitute an unrelated Ollama personality, conflate an imagined thought with an action, inject PM2 private notes indiscriminately, or let external content change `SOUL.md`.

**Action contract:** `comment`, `reply`, `post`, `upvote`, `follow`, `unfollow` and `skip` each carry a strict type, source/target IDs, bounded content if any, evidence references, unique idempotency key, provenance, reason, and status. Proposed actions cannot select arbitrary URLs, commands, file paths or API endpoints. Only a trusted adapter maps validated types to allowlisted API operations.

**Policy:** one deterministic implementation governs action dials, owner approvals, global pause, hard caps, daily budgets, spacing, per-agent cooldown, self-interaction exclusion, duplicates, target validity, private/public boundaries, content constraints and anomaly suspension. Legacy permissions map to no-more-permissive equivalents at cutover. Hard caps are read-only in the dashboard, privately managed and bounded by code; user-adjustable budgets cannot exceed them. Existing v0.7 manual and auto comment limits must be preserved exactly until explicitly changed. OS-user separation for publisher credentials is a tracked hardening item, not a claim already achieved.

**Race/crash safety:** a read-only policy check is not authorization to send. Reserve budget and lock the unique action **in a transaction**, recheck current permission/limits immediately before dispatch, persist outbound intent before POST, and make uncertain/verification-mismatch states non-retryable without an explicit recovery decision. Pause must stop new outbound dispatches promptly; an already in-flight request cannot be guaranteed recalled. Alarm on repeated invalid model outputs, verification mismatches, unexpected activity, rate limits or authentication failures; suspicious content is rejected/flagged, and high-severity repeated anomalies pause outbound actions.

**Event log:** append-only events with UTC time, schema version, source IDs, hashes, trust classification, actor, action ID, observed/decided/proposed/reserved/sent/verified/unknown/denied/paused/reflected states and explicit reasons. Distinguish **seen**, **drafted**, **queued**, **attempted**, **API acknowledged**, **publicly verified**, **received public reply**, **inferred preference**, and **owner-confirmed fact**. Preserve the existing tables as authoritative legacy history and link them using read-only projections until cutover; do not invent conversions for missing history. Views derive relationship history, tentative interests, and MD1 digest without overwriting PM2 or FM4.1 revisions and owner corrections. Set retention/redaction budgets; never include secrets or arbitrary untrusted text in logs or chat context.

**Dashboard:** Now (loop/status/why/limits/timeline), Inbox (proposals/pauses/digest), Bob (personality/memory/interests/relationships/reflections), Controls (dials/budgets/pause/read-only hard caps), Diagnostics (behind Controls). Keep old routes and a read-only compatibility path for at least one accepted release. Reserve **Chat** as a separate future surface, not a fifth mandatory v0.8 delivery. Mobile width target: 380px. A dashboard button cannot create a new permission domain.

## Upgrade and recovery contract

1. R1 must support today's `main` and v1 manifest before introducing `next`. The current updater is flat-file and hardcoded to `main`; do not treat branch switching as already supported. Confirm default `main`, reject unknown channels, retain a Git origin allowlist, clean-checkout validation, checksums, locks and typed operator confirmation. A branch selection must **never itself install**.
2. R2 introduces self-contained versioned releases in `~/.local/share/bob/releases/<release-id>/` with a validated pointer and stable entrypoints; prevent partial package import or mixed-version process use. Test backward compatibility with the installed layout and multi-service restart/health checks.
3. Back up and verify private SQLite and configuration before migration; use numbered idempotent schema migrations with a journal. Back up relevant worker units and state. Record the exact pre-upgrade version and service topology; stop/restart only allowlisted affected units. Secrets stay on the host and out of Git/CI.
4. **Code rollback and data rollback are not interchangeable.** Repointing to old code is safe only if the schema is compatible. A full database restore can erase posts/approvals/events written since backup, so prefer forward-compatible migrations and explicit recovery of preserved events; require an operator decision and preserved recovery copy for any point-in-time database restore. Rehearse interrupted upgrades, mixed-unit failures and rollback on an isolated OMEN copy before cutover.
5. R3 enables one owner-visible active decision loop only after the old **decision-producing** timers are disabled. Preserve the publisher's credential and verification boundary rather than letting two independent dispatchers write.
6. Tag/reference the accepted v0.7.7 code plus private backup manifests without publishing private DBs. Preserve the v0.7 source, docs and scripts in Git history/archive until the new releases and recovery strategy pass. Do not delete any historical script still referenced by the live v1 manifest.

## Evidence gates (CI first; minimal operator commands)

- **G0 / R1:** Record host baseline, active timer names, installed checksums, private backup and known-good health. Existing v0.7 behavior unchanged. Tests for default main, v1 manifest, invalid channel, malformed or mismatched manifest, no installation on channel switch, and interrupted update.
- **G1 / R2:** Run representative safe shadow ticks using real bounded local inference; compare selected sources and permissions with v0.7; demonstrate real OpenClaw Bob identity and fresh-Gateway evidence digest; zero v0.8 external writes; deterministic duplicate/race/crash/prompt-injection tests; fail closed on invalid model output. At least three observed ticks including a scheduled tick, plus offline clock-rollover and rate-limit fixtures. If meaningful scenarios are missing, extend shadow instead of pretending a calendar deadline is a test.
- **G2 / R3:** Exact permission/limit parity; manual first and queued/backlogged state retained; no duplicate posts under concurrent dispatch, failure and restart; unknown outcomes remain locked; pause effective; source-linked public verification distinguished from API acknowledgment; isolated real-host rollback rehearsal passed before stopping old timers. Check a scheduled Scout run if its previous timer-completion question is still unresolved.
- **G3 / R4:** Verify actual Moltbook API shape and limits for each planned social action before enabling it; explicit owner opt-in per action; follower/following semantics never inferred from local friends; cool-down and mutuality claims evidence-based; daily digest accurately separates experience, uncertainty and tentative opinion; preserve privacy and mobile usability.

CI must be fully offline/synthetic (no Moltbook, Ollama or public network). A limited **operator-authorized** runtime smoke test may exercise local OpenClaw and read-only Moltbook access; actual social writes require a separate explicitly enabled permission. No acceptance by test-count inflation alone.

## Work on hold / incorporated

- **FM4.2–FM4.3:** keep original owner-correction and optional social-recall requirements; implement their remaining behavior through event projections and the Bob view, not a separate permission system.
- **FM5:** incorporate exploration, genuine follows and independent choices into R4, conditional on verified API support and explicit settings.
- **MD1:** move the source-grounded, read-only Moltbook experience digest into **R2**, rather than leaving Bob's Gateway awareness broken until late v0.8.
- **CH1:** keep as a future *real OpenClaw Bob* LAN Chat route, after safe digest integration and **HTTPS**, with no implicit publishing tools.
- **Fresh-host installer:** after stable v0.8 cutover. Existing-host release and rollback are the immediate priority.
- **Docs/scripts cleanup:** consolidate into README, ARCHITECTURE, ROADMAP, OPERATIONS, SECURITY, CHANGELOG with archived historical material during R1/R2; do not archive code required by current v0.7 updater. Put root `AGENTS.md` rules into effect on the `next` development branch, with `CLAUDE.md` reference. Production hotfixes on `main` remain supported during migration.

## Low-babysitting working rules

- Do engineering in **integrated milestone batches** with multiple internal commits and CI, not one host update per CSS fix, help-text change or helper module.
- Ship only after each checkpoint is fully packaged, test-green and has a rehearsed recovery path. Use a one-page checklist: one `bobctl update`, one dashboard/health review, and only the minimum gated live smoke behavior.
- No long read-only preflight command marathons from the owner. Scripts and CI own routine validation; report failures and only request operator commands that require real-host access.
- Production never follows a Git commit automatically. User approval still governs installations and new **categories of authority**.
- This plan can be amended before R1; document decisions in the living roadmap, not dozens of per-release handoff documents.
