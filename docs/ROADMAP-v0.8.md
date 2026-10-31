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
