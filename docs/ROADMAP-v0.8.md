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
