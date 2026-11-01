## Source-only proposal-worker handoff and owner-to-one-publisher synthetic rehearsal

R3 proposal generation cannot silently steal the existing R2 shadow timer or run an extra publisher. The new guarded handoff source at `scripts/r3_service_handoff.py` provides **two uninstalled** exact-name user units: `bob-r3-propose.service` (oneshot, launches the existing package-verified `bob-r3-propose --once` with no Moltbook credential/post capability) and its distinct `bob-r3-propose.timer` (interval after the previous proposal run, randomized delay). The original systemd Scout and single credentialed publisher timers/services are never disabled, restarted or modified by this handoff. A second `bob-r3-candidate-publisher` service/timer is a hard review blocker.

The guarded future owner `--apply` requires the **actually installed** `v0.8.0-cutover1` release, exact updater-verified installed file hashes, confirmed HTTPS manager protocol and all four R3 publish-enabling source flags still **hard Off**. It refuses a busy shadow service or unrecognized unit state, demands a typed `ACTIVATE R3 PROPOSALS` owner phrase, stages only the two hashed proposal-only user unit files, journals before transitions, retires only the previous R2 shadow decision timer, and enables the new proposal timer. Interrupted/failed activation has a private journal; `--recover` requires `RECOVER R3 SHADOW`, disables only the new timer if armed, removes only unchanged unit files, restores the former R2 shadow schedule, and **never** restores older SQLite after any attempt. A completed timer handoff does not grant any public R3 posting right. Keep this code **uninvoked** until the actual owner-approved release acceptance.

A separate full synthetic test `tests/test_r3_end_to_end_offline.py` connects real production-shaped saved-source verification and proposal creation, typed owner-only manual enable/approve/queue, the actual single legacy publisher adapter and fake fixed-target POST. The mock verifies exact content, one credential lookup, no publication on archived/invalid installed R3 ZIP or revoked controls, manual legacy job priority and uncertain-send no-replay behavior. The fake-systemd test rehearses success, partial-install interruption, recovery and refusal on unit drift/competing publishers. All tests use isolated SQLite and filesystem fixtures, with NO actual Moltbook API or owner host changes.

These checks are necessary but **not sufficient** for production cutover: the final isolated full release proof must still validate the checkout-source updater self-upgrade, fixed TLS CA behavior, publisher and proposal worker service states, current installed schema and code-only rollback. The owner should get one consolidated cutover report after the package is reviewed; a real first comment remains independently authorized with exact text and target.

---

## Signed R3 package activation and rollback rehearsal (source engineering)

The versioned Activity Manager imports R3 code only after checking that the **installed updater registry** records its SHA-256. The previous updater stored the candidate registry *after* restarting Activity Manager; for a changed signed ZIP that order can cause a legitimate startup to fail because the new package bytes do not match the old registry. The R3 integration source updater now verifies every candidate file and atomically publishes the new signed registry **while the transaction journal is still incomplete**, **before** restarting the manager. A completed release is recorded only after CA-verified HTTPS health passes. On any failed restart or health check, rollback restores original code and previous signed registry, then restarts the old manager. SQLite is never reverted.

The offline test `tests/test_r3_candidate_registry_order.py` runs the real versioned updater `update` and `rollback` functions against disposable binaries, registry/journal, private dirs and a synthetic SQLite database. Systemd, backup invocation and HTTPS health are mocked. It proves: signed candidate archive validates during simulated restart; failed health rolls back code+registry; interrupted restart leaves a recoverable journal; restart exceptions roll back; and a synthetic `attempted` event created *after* upgrade persists across code rollback. This is a source-only simulation, **not** owner acceptance of the actual Windows/WSL host or a license to send.

Both source updater versions remain pinned to HTTPS for `v0.8.0-cutover1`, and no new R3 dispatch permission has been granted. The final deployment gate still needs integration of the managed single-writer timer handoff, authenticated owner permissions, actual installed-code rehearsal and separately authorized canary.

---

## Single-writer verified-package boundary (source candidate)

The source-only R3 publisher adapter now verifies the installed, registry-pinned **R3 ZIP before importing any Bob v0.8 modules**, including those referenced by the private-host schema review. This closes a subtle module-loading gap in the future one-writer path: the existing legacy publisher is not launched with the new R3 archive on its Python path by default. The loader checks exact installed hash, regular-file/private ownership and a trusted cached Shadow/R3 namespace; it creates **no second sender** and neither opens credentials nor performs network activity. When the installed hard-Off gate is in force, even the package loader is not invoked. Offline tests exercise both hard-Off short-circuit and fail-closed invalid archive/host cases.

## Source-only candidate assembly: v0.8.0-cutover1 Off bundle (2026-10-31)

The first integrated source-only **12-file** candidate lives at `releases/candidates/r3-cutover1-integration-off.json` and intentionally does **not** replace `releases/current.json`. It chains `from v0.8.0-chhttps3` (actually installed on the OMEN) to the reserved `v0.8.0-cutover1`. It packages the single existing credentialed publisher with the stronger final duplicate claim, previously accepted R3 owner/proposal/ZIP modules, generated **HTTPS-only** manager/navigation, and exact future updater/`bobctl` sources. All four reviewed literal R3 automatic/manual send-enabling gates remain **hard Off**. It installs no new publisher timer or systemd service and conveys no canary or production send authority.

**Important release upgrade contract:** the **currently installed** release updater and `bobctl` only recognize release IDs up through `v0.8.0-chhttps3`. Using the old installed `bobctl update` on a promoted `cutover1` manifest could cause an avoidable postflight-transport refusal and rollback. The updated **source** updater and `bobctl` now include a tightly pinned `v0.8.0-cutover1 -> https` mapping and never downgrade to HTTP. When the entire final cutover is reviewed and owner-authorized, the one-install mechanism must explicitly run the guarded checkout-source updater `python3 scripts/bob_release_updater.py` with its existing backup/typed approval/journal/code-only rollback, while installing the newer updater and CLI together. This is a *planned* deployment procedure, not authorization to run it now. A rehearsal must verify this exact self-update/rollback path, and a separate operator acceptance contract is required.

**Source-only audit available for CI:** `python3 scripts/report_r3_consolidated_candidate.py --check` validates exact files, source guards, release chain and compiles the deterministic 12 artifacts. It returns `ready_to_install_or_cutover: False`, and never loads credentials, private SQLite, Moltbook API or systemd. The owner does **not** need to run this before release acceptance.

**Remaining to achieve a genuine cutover release:** final reviewed single-publisher source/ZIP loading and protected owner permissions, atomic pre-POST checks, recovery of interrupted sends without replay, exact timer ownership transition, CA-verified health and **code-and-unit-only rollback** in a complete offline rehearsal. Keep Off until those pass; the first real canary still requires a separate exact-comment owner approval. Do not mistake a successfully built source candidate for an install-ready or active publishing cutover.

---

## Owner-accepted G2 receipt baseline and R3 first integrated source fix (2026-10-31)

The owner reported `G2 LEGACY COMMENT RECEIPTS` with 23 historical attempts/23 inspected, all 23 saved comment IDs confirmed visible in their corresponding public listings, no duplicate attempted target groups, no reused receipt IDs, no truncate, and a stable DB during the GET review. This completes the **known public-comment receipt matching** gate. It is not a universal negative proof for unrecorded remote posts and does not cover original posts; none of the public GETs performed writes.

**First R3 integrated source improvement:** The existing production-shaped credentialed publisher's old local duplicate check did not protect all rows with a past `attempted_at` once a job ended in `failed`. In the cutover development branch, that check now matches `attempted_at IS NOT NULL` regardless of final job state. The same protection is embedded atomically into both manual and auto final SQLite pre-POST claims, guarding against a duplicate attempt recorded after the earlier GET began. Offline source tests require a prior failed attempt and a newly appearing attempted duplicate to prevent a second POST, while an unattempted historical failure does not automatically block the legitimate exact approved job.

**Not deployed:** The current release registry stays `v0.8.0-chhttps3` and original installed publisher remains unchanged. This source hardening is part of the later **one integrated cutover** engineering batch, not a request for an incremental host install. Remaining integration must verify actual versioned ZIP imports, single publisher timer/process ownership, independent owner approvals/auto opt-in, source pinning, pause/limits, crash/uncertain states, public verification vs API ACK and code-only rollback. Keep every real R3 send gate Off until explicit separate release and canary authorization.

---

# Consolidated v0.8 R3 cutover: G2 receipts and one guarded release

**Status:** source and acceptance plan. The installed v0.8.0-chhttps3 release is unchanged.
**Safety:** R3 real Moltbook publishing remains hard Off. No owner cutover or canary authorization follows from this plan.

## Accepted production baseline

R1 updater and R2 Shadow4 have been accepted. The R2 timer has run, although a naturally scheduled **source-linked decision** remains a distinct outstanding G1 observation; do not force replay for it.

R3.13d additive Off-only schema/journal is installed and preserves 23 attempted legacy jobs and 0 uncertain, both before and after Windows reboot. The Activity Manager is HTTPS only; OpenClawLab, Gateway, manager and original timers recovered successfully at Windows interactive login. The WSL Hyper-V firewall is enabled/default Block with an allow rule for TCP 18790 from 192.168.1.0/24. The owner reports no outside reachability. These are good operational observations, not a comprehensive independent WAN scan.

## G2 reconciliation: ONE bounded owner command

The source-only `scripts/report_g2_public_receipts.py` uses the existing `audit_comment_visibility.py` anonymous public HTTPS GET checker on the fixed Moltbook endpoint, with no credentials. It reads the private `publish_jobs` table with SQLite `mode=ro` and `PRAGMA query_only`. It audits at most 40 historically attempted legacy comment jobs, and checks at most two bounded public listing pages per valid saved receipt. No source text, passwords, comments, or private IDs are printed. It performs no POST, database writes, systemd changes or R3 permission changes.

After reviewed CI/merge, run from the normal OpenClawLab `openclaw` shell:

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/report_g2_public_receipts.py --public-get
```

The flag explicitly permits **anonymous public GETs only**. Without it, the script is local-only. Optional `--json` prints aggregate counters, not content. It compares local snapshots around the network checks and marks a moving database or truncated history incomplete.

- `status: known_receipts_visible` means every attempted comment in this bounded scope had a saved comment ID visible in its public thread, and there were no local duplicate-target/receipt or unknown/uncertain-state flags. It **does not** prove there are no additional unrecorded external posts.
- `status: review_required` is an honest completed audit with missing receipts, failed/unavailable public lookups, incomplete pagination, repeated attempted targets (possibly legitimate), unfamiliar queue states, or moving/truncated history. It does **not** authorize replays or repeated forced publisher runs.
- `external_duplicate_posting_excluded` is always false. Public listings can omit entries; an extra unrecorded reply would not be ruled out by matching a known ID. Original posts are outside this comment audit.

If the audit returns unresolved rows, review only the flagged categories and actual remote receipts/source records. Never replay attempted or uncertain jobs, restore a stale SQLite backup, or change the publisher to make an audit pass.

## R3 cutover1: ONE integrated engineering and deployment batch

Build one versioned `v0.8.0-cutover1` candidate whose upgrade chain starts from the **actually installed `v0.8.0-chhttps3`**. Package all the following together:

1. A single source-sealed real-OpenClaw-Bob proposal/decision loop, with strict target/text identity and no new runtime Moltbook credentials. R2 Shadow remains unchanged until a reviewed service handoff.
2. Exactly **one external writer**: extend the existing credentialed legacy publisher hook in the same `publish_jobs` queue. No separate R3 HTTP publisher or second dispatch timer. Preserve manual approvals and legacy original-post flow.
3. Atomic intent-before-POST and final source/author, consent, friend-policy, pause, budget, manual-first priority and duplicate/unknown-history checks. Treat API acknowledgement, verified public comment, failed and uncertain states distinctly. Never auto-retry uncertain sends.
4. One owner-visible R3 Controls/Now/Inbox authority, with default-Off new automatic Bob actions. Managed, exact-name transition of any conflicting old decision timer; never disable existing publisher/Scout prematurely or silently enlarge permissions.
5. Additive schema/backward-compatibility and **code-and-unit-only rollback**, preserving historical and newly attempted posts. Never restore an earlier SQLite snapshot after any possible send.
6. Offline isolated CI for concurrency, crash/pause/rollback, rate/friend restrictions, duplicate cases, queue ordering, and source tampering. No external Moltbook writes during CI.

### One owner acceptance, not dozens of micro-tests

**Engineering:** implement in integrated batches on `next`, run all synthetic tests and isolated recovery rehearsal in CI, and review the exact candidate manifest. Do not promote or install an unfinished candidate.

**One release acceptance:** after explicit owner approval, `bobctl update --check`, one `bobctl update`, and **one consolidated installed health/permission report** with the new publisher still default Off. Do not require the owner to test each PR separately.

**Separate optional public canary:** only after the owner separately approves one exact source/post, draft and send attempt. Verify public receipt rather than treating API ACK as published. Auto-R3 remains Off until its own explicit opt-in. On failure, keep Off, preserve the ledger, and use code/unit-only rollback.

## After R3

R4 is one integrated social-autonomy and UI release: verified Moltbook follow/upvote/unfollow APIs if supported, independent exploration, evidence-grounded relationships/digests, consolidated Now/Inbox/Bob/Controls and robust anomaly pause, all opt-in. CH1 real OpenClaw LAN Chat is a later separate feature, not a hidden R3 prerequisite.

**Operator time budget:** one useful G2 read-only report, one consolidated R3 release acceptance, and an optional exact canary. No new chains of installer commands for trivial UI patches.
