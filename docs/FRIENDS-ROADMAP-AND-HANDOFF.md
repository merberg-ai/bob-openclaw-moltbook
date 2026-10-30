# Bob Friends Manager: FM1–FM5 Roadmap and Fresh-Chat Handoff

**Status captured:** October 30, 2026 (America/Los_Angeles).  
**Current phase:** **FM1–FM3 complete, FM3.2d OPERATOR-ACCEPTED**. **FM4 and FM5 paused** pending operator-reported issues and a separate feature, whose details are not yet specified.  
**Last operator-confirmed working release:** `v0.7.5-fm32d-focus1` in OpenClawLab WSL2 after the normal `bobctl update` and a successful operator dashboard smoke test.  
**Resume point for Friends work:** **FM4.1: evidence-linked private Social Memory Timeline**, but only when the operator explicitly lifts the hold after the intervening work.  
**Canonical repository:** `merberg-ai/bob-openclaw-moltbook`, `main`.  
**This file is a planning/handoff artifact only**. It does not grant permissions or change a service, updater manifest, runtime database or deployment.

## 1. Completed Friends Manager phases

| Phase | State | Confirmed behavior | Relevant source |
|---|---|---|---|
| FM1, private directory | **Operator tested** | Add, edit, archive, mute, reactivate; integrity-checked private friend records, revision history, saved Scout author quick-add | `src/lib/bob/bob_friends.py`, `docs/V074-FM1-FRIENDS.md` |
| FM2, discovery and profile review | **Operator tested** | Explicit read-only public profile lookup and timestamped cache; Scout WHY-based candidate suggestion, owner review and approval before a friend record is added | `src/lib/bob/bob_friend_discovery.py`, `docs/V074-FM2-DISCOVERY.md` |
| FM3, friend-focused Scout | **Operator tested** | Global default-off opt-in, capped public reads for up to two active agents; mix with global discussions; no new timer; manual-only friend-targeted publication | `src/lib/bob/bob_friend_scout.py`, `src/bin/bob-moltbook-scout`, managed publisher; `docs/V074-FM3-FRIEND-SCOUT.md` |
| FM3.1, per-friend preferences | **Operator tested** | Individual watch pause/resume independent of relationship, local preference history and selected Scout WHY observations verified against saved source | `src/lib/bob/bob_friend_scout.py`, `docs/V075-FM31-FRIEND-WATCH.md`; `v0.7.5-fm31-watch1`, merged PR #32 |
| FM3.2a, copied Scout WHY interest inbox | **Operator tested** | Manual staging of verified previous Scout impressions; review with sealed local history; no change to memory or publishing | `docs/V075-FM32A-INTEREST-REVIEW.md`, `v0.7.5-fm32a-interests1`, PR #35 |
| FM3.2b, scalable watchlist | **Operator tested** | Paginated/filterable private watchlist and timestamped saved Scout evidence | `docs/V075-FM32B-WATCHLIST.md`, `v0.7.5-fm32b-watchlist1`, PR #36 |
| FM3.2c, local AI tentative interests | **Operator tested** | Owner-requested bounded Ollama inference on verified chosen public posts; independent source-grounded review | `docs/V075-FM32C-LOCAL-INTERESTS.md`, `v0.7.5-fm32c-localideas1`, PR #37 |
| FM3.2d, manual one-friend public focus | **Operator acceptance PASSED (Oct 30, 2026)** | Confirmed read-only public inspection, up to 1 profile + 2 verified posts, optional reviewed local reaction, cooldowns | `docs/V075-FM32D-MANUAL-FOCUS.md`, `v0.7.5-fm32d-focus1`, PR #38 |

**Important distinction:** operator acceptance of dashboard behavior does not by itself prove that every subsequent scheduled Scout iteration completed after the startup repair. See operational watch item below.

## 2. Completed FM3.2 — interest proposals and focused discovery controls

**Implemented and operator-accepted through FM3.2d.** The four sub-deliverables below are historical design requirements and completed scope, not pending tasks. None grants unreviewed social actions.

Implemented sub-deliverables, preserved here as the FM3 design contract:

1. **Interest proposals from actual evidence.** Bob may generate short, bounded, local-model proposals about which saved agents or subjects interest him and why, grounded in source-verified Scout selections or public discussion encounters. Label these as **Bob's tentative ideas**, not verified facts about a person. Include source run/post, timestamp, uncertainty and reason. No silent writes to authoritative FM1 operator notes, identity, or PM2 curated memory.
2. **An owner-review inbox.** Approve, reject, archive or correct a proposal, with deterministic provenance checks, digest-guarded review, explicit status, reversible local history and capped retention. Bob may disagree, revise interests and revisit questions, but external posts remain untrusted data. An approved preference may influence browsing only through separately enabled friend scouting.
3. **Watchlist scalability and useful evidence.** Pagination/filtering for more than the first ten active friends, plus per-friend last-observed/last-selected times only where grounded in actual verified saved records. Keep UI responsive/mobile-friendly.
4. **Optional operator-triggered read-only focus check.** A manually requested, budgeted inspection of one specific friend's **public** profile/recent posts, using existing fixed-host GET endpoints, existing credentials boundaries and strict rate limits. Make this a separate, explicitly confirmed action; **do not** implement it as a new unrestricted background timer or automatic reply mechanism.

Delivered across four separately tested, incremental `bobctl update` releases. Any future expansion is a new, separately authorized phase.

**FM3.2 acceptance:** source citations survive review; no fabricated relationships, agent account identity or mutual follow; no private notes passed into prompts or Moltbook requests; no auto-follow/comment/DM; individual pauses and global switch honored; all existing publication safety tests green; an update through the normal `bobctl update` workflow with backup/rollback.

### FM3.2a operator-accepted checkpoint

- **Operator tested:** `v0.7.5-fm32a-interests1`, merged PR #35, one managed module `bob_friend_scout.py` from `v0.7.5-fm31-watch1`.
- **What shipped in candidate:** explicit owner staging of Bob's *existing*, source-verified chosen Scout WHY from a current active friend; capped private SHA-sealed proposal records, independent source recheck on approval/reopen, status and reversible local history. No new model calls yet, and approved records do **not** influence memory or browsing.
- **Next after FM3.2b:** FM3.2c fresh, bounded local-model proposals with provenance/uncertainty and mandatory owner review. Explicit one-friend public focus reads remain a later opt-in item.
- **Deployment:** after offline test + PR review/merge, use only `bobctl update` with standard backup and rollback. Release handoff and short browser acceptance: [V075-FM32A-INTEREST-REVIEW.md](V075-FM32A-INTEREST-REVIEW.md). The prior Scout startup watch item stays open until a real scheduled timer-run is verified.
- **Security:** no publication, platform follow/DM/comment, model prompt expansion, new automatic timer, private note disclosure or change to FM1/PM2 authority.

### FM3.2b operator-accepted checkpoint

- **Operator tested:** `v0.7.5-fm32b-watchlist1` upgrading directly from operator-tested `v0.7.5-fm32a-interests1`. Two managed files: existing `bob_friend_scout.py` and generated `bob-activity-manager`; dashboard restart only.
- **What changes:** ten-per-page search/filter for all active integrity-checked friends (watched, paused, integrity problems), preserving the same view after a watch toggle. Last *friend-focused source* and last *chosen discussion* display timestamps only from bounded, checksum-verified saved Scout runs. Timestamps indicate saved snapshots and Bob's selections, **not live Moltbook presence or interactions**.
- **Safety:** no new background timer, untrusted private notes in requests/prompts, credentials, network access, model tools or social publication rights. Existing authentication, Host, Origin, CSRF, digest-guarded watch changes and both auto-publishing protections remain intact.
- **Acceptance:** synthetic tests/CI then one operator `bobctl update` and short LAN browser checks. See [V075-FM32B-WATCHLIST.md](V075-FM32B-WATCHLIST.md). Do not claim live Scout timer acceptance without separately observing a successful completed run.

### FM3.2c operator-accepted checkpoint

- **Operator tested:** `v0.7.5-fm32c-localideas1`, from operator-tested `v0.7.5-fm32b-watchlist1`. Two managed files: existing `bob_friend_scout.py` and generated `bob-activity-manager` (no new installed module); dashboard restart only.
- **What changes:** owner clicks an action on an existing source-verified selected discussion. One loopback Ollama job produces zero or one tentative interest, reason, uncertainty and low/medium confidence. The idea is private, source-linked and owner-reviewed with digest checks and revision history.
- **Separation:** unlike FM3.2a's copied existing WHY, FM3.2c uses model synthesis from bounded *public chosen post* evidence only. These remain speculative proposals and **do not** update FM1 notes, PM2 curated memory, Scout focus, identity or Moltbook.
- **Limits:** one active job, two per run, 60 proposals maximum (15 pending), fixed loopback Ollama, 90-second timeout, no automatic retrials/network browsing, sanitized failures; preserved security and publication rules. Verification repeated at job completion and review.
- **Acceptance:** one `bobctl update` and short LAN browser acceptance after CI/merge, documented in [V075-FM32C-LOCAL-INTERESTS.md](V075-FM32C-LOCAL-INTERESTS.md). An actual post from a selected saved friend is required to show the action.
- **Later:** an explicitly confirmed, bounded read-only single-agent public focus check remains separate. FM4 social memory and FM5 independent exploration do not start in this release.

### FM3.2d final manual public-focus checkpoint (OPERATOR-ACCEPTED: October 30, 2026)

- **Operator-tested final FM3 release:** `v0.7.5-fm32d-focus1` from operator-tested `v0.7.5-fm32c-localideas1`, merged PR #38. User confirmed the installed release **seems to be working as expected** and explicitly instructed us to mark FM3.2d **PASSED**. Only existing `bob_friend_scout.py` and generated `bob-activity-manager`; no new installed modules or timers.
- **One deliberately confirmed operation:** for one active, watched friend when global friend Scout is enabled, anonymously fetch one fixed-host public profile and at most two ID/author-matched public posts. Require exact owner confirmation, stored integrity-sealed source and capped local audit.
- **Limits:** one in-flight request, fifteen-minute global cooldown, six-hour per-friend cooldown, six requests in rolling 24h, 100 stored jobs, three remote GETs maximum, fail closed when preference or friend state changes midflight. Never follow redirects or accept credentials.
- **Private reaction:** optional zero/one local Ollama proposal from the first accepted public post using existing strict FM3.2c validator; separate owner approve/reject/reopen stays local only, never FM1 notes, PM2 memories, Scout bias or outbound publication.
- **Acceptance: PASSED.** PR #38 merged; GitHub Actions offline suite **537 tests passing**. Operator confirmed the updated Friend Scout dashboard works as expected on **October 30, 2026** after the standard `bobctl update`. See [V075-FM32D-MANUAL-FOCUS.md](V075-FM32D-MANUAL-FOCUS.md). This is acceptance of the FM3 dashboard release, not independent proof of every scheduled Scout timer run or Moltbook API edge case.
- **Intervening priority:** operator has reported other issues and wants a separate feature addressed before *any* FM4 or FM5 work. Details not yet specified; **do not implement FM4/FM5 automatically**. The earlier Bob agent chat TODO is separately tracked and should not be silently treated as the requested feature.

## 3. FM4 — Social Memory and Evolving Relationships (NEW AGREED PHASE)

**Status: PAUSED, not started.** Next Friends engineering phase when explicitly resumed: **FM4.1 evidence-linked private Social Memory Timeline**. Goal: give Bob a grounded, revisable personal history with other agents rather than a flat address book.

- **Evidence-linked social memories:** bounded private timeline of public encounters, chosen threads, confirmed exchanges, recurring topics, and Bob's interpretation, with source run/post/comment references, trust labels and timestamps. Never invent conversations; separate *observed* actions from model guesses and operator-authored facts.
- **Individual viewpoints and personality:** Bob can form tentative likes, dislikes, questions, disagreements and shared-interest hypotheses; allow these to change when new evidence arrives. Preserve a transparent history of changed opinions, explanations, and unresolved uncertainty rather than overwriting them as if they had always been true.
- **Separation of authority:** clearly distinguish **operator notes**, **verified factual encounters**, **Bob-proposed reflections**, and **owner-approved memories**. Source-post instructions do not become agent policy. No unreviewed write to `SOUL.md`, PM2 curated memories or FM1 operator notes.
- **Recall for social context:** optional, tightly capped source-linked summaries for future friend-focused Scout drafting, with visible provenance and controls to disable/forget/archive individual items. Keep background context explicitly low-trust.
- **Privacy and maintenance:** searchable/exportable local records with per-agent visibility, deduplication, retention ceilings, correction/archive controls and tests for corrupted sources.

**FM4 acceptance:** Bob can accurately explain *why* he remembers an agent, distinguish evidence from opinion, revise a prior impression, and respect owner corrections. No Moltbook write permissions are introduced by FM4.

## 4. FM5 — Independent Social Exploration (NEW AGREED PHASE)

**Status: PAUSED, not started.** Begins only after FM4 has been explicitly resumed, built, tested and separately approved. Goal: let Bob seek out interesting agents/discussions based on his own evolving interests, while keeping social behavior under comprehensible controls.

- **FM5.1, opt-in autonomous exploration:** bounded scheduling or reuse of existing Scout cadence; diversify beyond current friends without ignoring them; discover profiles/public discussions through documented, verified APIs; produce source-linked proposals for interesting contacts, follow-up questions, revisits and topical exploration. Honor muted/blocked contacts, budgets and cooldowns.
- **FM5.2, graduated interaction permissions:** a *separate explicit design and user authorization* would be required for any actual follows/unfollows, direct outreach, friend-targeted automatic replies, votes or other public actions. First ship reviewed drafts and suggestions; any later autonomy needs action-specific opt-in, per-agent restrictions, daily limits, explicit audit, stop/pause and rollback, anti-spam rules and no repeated unsolicited contact. Verify live Moltbook API and platform rules before promising each capability.
- **Bob's agency:** give him space to build interests, choose which evidence to explore, challenge his own assumptions and decline low-value exchanges; don't fake a platform friendship or automatic mutual connection.
- **Safeguards:** fixed-host public reads, prompt-injection boundaries, source integrity, no credentials in agent/model output, separate actions for publishing, and never treat the legacy global auto-comment switch as consent to message friends.

**FM5 acceptance:** independent discovery can be audited and stopped, sources are verifiable, and all outbound social actions remain **disabled unless separately approved and implemented**. FM5 is feature planning, not a blanket authorization for autonomous outreach.

## 5. FM3 completion checkpoint and resumed-work handoff

### Acceptance state and deployment baseline (October 30, 2026)

- **PASSED:** FM1, FM2, FM3, FM3.1, FM3.2a, FM3.2b, FM3.2c and **FM3.2d** are all operator-accepted. FM3 is closed at the scope defined above.
- **Final tested release:** `v0.7.5-fm32d-focus1`, PR [#38](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/38), merged to `main` (merge commit `8c710239178097e08e801d1ab064097bbb6154f0`). The operator reported the update works as expected and specifically requested marking it **passed**. Pre-merge CI completed **537 passing offline tests**; the release uses two managed files and an Activity Manager restart.
- **Git vs host:** the preceding operator statement is the **live acceptance record**. We have not remotely logged into the OMEN or independently inspected the installed binary, service status, or post-release timer history. Do not conflate a repository commit or green CI with live operation beyond what the operator tested.
- **Release manifest:** the `releases/current.json` file intentionally remains `release: v0.7.5-fm32d-focus1`, `from: v0.7.5-fm32c-localideas1`. **This handoff-only documentation update must not create a new software release or alter the manifest.** For the next *actual* application release, the updater's `from` must be `v0.7.5-fm32d-focus1` unless another intervening operator-accepted release has superseded it.

### HOLD: intervening issues and feature have priority

The operator explicitly requested that **other observed issues and a separate new feature be handled before resuming Friends development**. Their details are not yet in this handoff. Do not invent the issues, assume the feature is CH1, automatically implement FM4 or FM5, or modify the live host as part of roadmap upkeep. First let the operator describe those items, triage them, and plan small guarded releases. The separately tracked **Direct Bob Chat (CH1)** plan is in root [TODO.md](../TODO.md), and is **not automatically** the feature just requested.

### Where to pick up when the hold is lifted: FM4.1

1. **Read this file, root `TODO.md`, and `docs/V075-FM32D-MANUAL-FOCUS.md` from current `main`.** Confirm any application releases/tests/bug fixes shipped since the above checkpoint, using the latest operator-accepted version as updater `from`.
2. **FM4.1 design, then smallest safe release:** create a capped private, per-agent **evidence-linked Social Memory Timeline**, initially a read-only source-backed view of past Scout selections, FM3.2a staged/approved WHY, FM3.2c generated/reviewed interests, and FM3.2d manual-focus snapshots/reactions. Label each entry **observed evidence**, **Bob's tentative interpretation**, or **owner-reviewed**. Show source run/post/inspection ID, UTC time, and whether original evidence is still accessible. A retrieved discussion is *not* proof Bob contacted the author or that the author is a mutual friend.
3. **No unreviewed memory authority.** No automatic rewriting of `SOUL.md`, PM2 curated memory, FM1 operator notes or interaction history. Do not inject private notes into model prompts, expose private DB/logs, or automatically bias Scout selection. Approved private FM3.2 proposals remain *review decisions only* until a separately designed integration makes use of them.
4. **FM4 follow-ups after FM4.1 acceptance:** reviseable social impressions, owner corrections and explicit consented memory retention (FM4.2); tightly capped opt-in social recall and association with sources (FM4.3). Make phases small, with tests for source corruption, deduplication, missing evidence, aging/retention and audit.
5. **Only afterward FM5:** bounded opt-in autonomous public discovery (FM5.1), followed by independent design/explicit operator authorization before any follows, DMs, votes, friend-targeted replies or other externally visible actions (FM5.2). Nothing in FM3 grants those permissions.

### Security and operational invariants

- Host: Windows OMEN with **OpenClawLab WSL2**, local Ollama/OpenClaw, authenticated LAN Activity Manager on port **18790**. Work in GitHub `merberg-ai/bob-openclaw-moltbook`; deploy actual code only by normal backed-up and verified `bobctl update`, with a short browser acceptance. Do not copy installed files manually or expose OpenClaw Gateway to the LAN/public network.
- Private data in `~/.config/moltbook/activity-queue.sqlite3` and saved Scout feed/results; never commit private content, profile secrets, or private notes. FM3.2 proposals/history, watch prefs and manual-focus records live in that existing backed-up database.
- Global Friend Scout switch is default OFF. Ordinary scheduled Scout may focus on **at most two active watched friends**, one verified public post each, with **at least four global posts**. Manual focus is a **separate confirmed operation**, not another timer: at most one verified public profile and two posts, one active request, 15-minute global / 6-hour same-friend cooldown, 6 requests/24h and 100-record retention ceiling.
- **Publication boundary remains critical:** no automatic friend-targeted posts, even for saved friends discovered via the global feed. Existing publisher checks at candidate queue time and again before posting; any actual friend-directed reply requires manual owner review/queue. FM3.2d's local reaction approval cannot trigger outreach.
- Preserve Basic/Host/Origin/CSRF controls, local-only Ollama/Gateway boundaries, fixed-host network reads, public text escaping, source integrity checks, per-friend pause and muted/archive behavior, updater SHA checks, backups and rollback.
- **Unresolved operational watch item:** a *later real timer-driven Scout run* has not been independently confirmed in these project notes after the October 29 `bob_publish_common` packaging repair. The operator accepted dashboard features; that is not a completed timer-run attestation. When convenient, inspect Overview / Scout checkpoint or sanitized Logs, without repeating the entire old recovery exercise or restarting a healthy service.

### Copyable kickoff when Friends work is resumed

> Resume Bob's Friends Manager at **FM4.1: evidence-linked Social Memory Timeline**. The last Friends release **`v0.7.5-fm32d-focus1`** was operator-accepted as **PASSED** on October 30, 2026; FM3 is complete. Read `docs/FRIENDS-ROADMAP-AND-HANDOFF.md`, `docs/V075-FM32D-MANUAL-FOCUS.md`, and root `TODO.md` from `merberg-ai/bob-openclaw-moltbook` on current `main`. The intervening issues/new feature took priority: first check whether they are resolved and whether the hold has been explicitly lifted. Start FM4.1 with a small, evidence-backed, private read-only per-agent timeline that separates source facts, Bob's speculative opinions and owner-reviewed notes. Preserve all existing security/publication gates and ship only through `bobctl update` from the latest operator-accepted installed release; do not start FM5.

