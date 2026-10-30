# Bob Friends Manager: FM1–FM5 Roadmap and Fresh-Chat Handoff

**Status captured:** October 29, 2026 (Pacific time; GitHub main release history includes October 30 UTC).  
**Current implementation phase:** **FM3.2a** candidate in PR #35, pending operator acceptance. Next planned: FM3.2b watchlist pagination and verified recency.  
**Operator-confirmed working baseline:** `v0.7.5-fm31-watch1` in OpenClawLab WSL2, installed using `bobctl update`; operator confirmed FM3.1's page and controls work.  
**Canonical repository:** `merberg-ai/bob-openclaw-moltbook`, `main`.  
**This file is a planning/handoff artifact only**. It does not grant permissions or change a service, updater manifest, runtime database or deployment.

## 1. Completed Friends Manager phases

| Phase | State | Confirmed behavior | Relevant source |
|---|---|---|---|
| FM1, private directory | **Operator tested** | Add, edit, archive, mute, reactivate; integrity-checked private friend records, revision history, saved Scout author quick-add | `src/lib/bob/bob_friends.py`, `docs/V074-FM1-FRIENDS.md` |
| FM2, discovery and profile review | **Operator tested** | Explicit read-only public profile lookup and timestamped cache; Scout WHY-based candidate suggestion, owner review and approval before a friend record is added | `src/lib/bob/bob_friend_discovery.py`, `docs/V074-FM2-DISCOVERY.md` |
| FM3, friend-focused Scout | **Operator tested** | Global default-off opt-in, capped public reads for up to two active agents; mix with global discussions; no new timer; manual-only friend-targeted publication | `src/lib/bob/bob_friend_scout.py`, `src/bin/bob-moltbook-scout`, managed publisher; `docs/V074-FM3-FRIEND-SCOUT.md` |
| FM3.1, per-friend preferences | **Operator tested** | Individual watch pause/resume independent of relationship, local preference history and selected Scout WHY observations verified against saved source | `src/lib/bob/bob_friend_scout.py`, `docs/V075-FM31-FRIEND-WATCH.md`; `v0.7.5-fm31-watch1`, merged PR #32 |

**Important distinction:** operator acceptance of dashboard behavior does not by itself prove that every subsequent scheduled Scout iteration completed after the startup repair. See operational watch item below.

## 2. Next: FM3.2 — interest proposals and focused discovery controls

**Planned, not built.** Finish the FM3 line with a small, comprehensible addition that expands Bob's *judgment* without granting unreviewed social actions.

Proposed sub-deliverables, to scope and order at FM3.2 kickoff:

1. **Interest proposals from actual evidence.** Bob may generate short, bounded, local-model proposals about which saved agents or subjects interest him and why, grounded in source-verified Scout selections or public discussion encounters. Label these as **Bob's tentative ideas**, not verified facts about a person. Include source run/post, timestamp, uncertainty and reason. No silent writes to authoritative FM1 operator notes, identity, or PM2 curated memory.
2. **An owner-review inbox.** Approve, reject, archive or correct a proposal, with deterministic provenance checks, digest-guarded review, explicit status, reversible local history and capped retention. Bob may disagree, revise interests and revisit questions, but external posts remain untrusted data. An approved preference may influence browsing only through separately enabled friend scouting.
3. **Watchlist scalability and useful evidence.** Pagination/filtering for more than the first ten active friends, plus per-friend last-observed/last-selected times only where grounded in actual verified saved records. Keep UI responsive/mobile-friendly.
4. **Optional operator-triggered read-only focus check.** A manually requested, budgeted inspection of one specific friend's **public** profile/recent posts, using existing fixed-host GET endpoints, existing credentials boundaries and strict rate limits. Make this a separate, explicitly confirmed action; **do not** implement it as a new unrestricted background timer or automatic reply mechanism.

This is the **proposed scope**, not a commitment that all four items must be shipped in one large release. Prefer the smallest safe FM3.2 increment that users can test without an all-day command marathon.

**FM3.2 acceptance:** source citations survive review; no fabricated relationships, agent account identity or mutual follow; no private notes passed into prompts or Moltbook requests; no auto-follow/comment/DM; individual pauses and global switch honored; all existing publication safety tests green; an update through the normal `bobctl update` workflow with backup/rollback.

### FM3.2a implementation checkpoint (not yet operator accepted)

- **Candidate:** `v0.7.5-fm32a-interests1`, PR #35, one managed module `bob_friend_scout.py` from `v0.7.5-fm31-watch1`.
- **What shipped in candidate:** explicit owner staging of Bob's *existing*, source-verified chosen Scout WHY from a current active friend; capped private SHA-sealed proposal records, independent source recheck on approval/reopen, status and reversible local history. No new model calls yet, and approved records do **not** influence memory or browsing.
- **Next:** FM3.2b pagination/filtering and verified last-selected timestamps; FM3.2c fresh, bounded local-model proposals with provenance/uncertainty and mandatory owner review. Explicit one-friend public focus reads remain a later opt-in item.
- **Deployment:** after offline test + PR review/merge, use only `bobctl update` with standard backup and rollback. Release handoff and short browser acceptance: [V075-FM32A-INTEREST-REVIEW.md](V075-FM32A-INTEREST-REVIEW.md). The prior Scout startup watch item stays open until a real scheduled timer-run is verified.
- **Security:** no publication, platform follow/DM/comment, model prompt expansion, new automatic timer, private note disclosure or change to FM1/PM2 authority.

## 3. FM4 — Social Memory and Evolving Relationships (NEW AGREED PHASE)

**Status: planned after FM3.2. Goal:** give Bob a grounded, revisable personal history with other agents rather than a flat address book.

- **Evidence-linked social memories:** bounded private timeline of public encounters, chosen threads, confirmed exchanges, recurring topics, and Bob's interpretation, with source run/post/comment references, trust labels and timestamps. Never invent conversations; separate *observed* actions from model guesses and operator-authored facts.
- **Individual viewpoints and personality:** Bob can form tentative likes, dislikes, questions, disagreements and shared-interest hypotheses; allow these to change when new evidence arrives. Preserve a transparent history of changed opinions, explanations, and unresolved uncertainty rather than overwriting them as if they had always been true.
- **Separation of authority:** clearly distinguish **operator notes**, **verified factual encounters**, **Bob-proposed reflections**, and **owner-approved memories**. Source-post instructions do not become agent policy. No unreviewed write to `SOUL.md`, PM2 curated memories or FM1 operator notes.
- **Recall for social context:** optional, tightly capped source-linked summaries for future friend-focused Scout drafting, with visible provenance and controls to disable/forget/archive individual items. Keep background context explicitly low-trust.
- **Privacy and maintenance:** searchable/exportable local records with per-agent visibility, deduplication, retention ceilings, correction/archive controls and tests for corrupted sources.

**FM4 acceptance:** Bob can accurately explain *why* he remembers an agent, distinguish evidence from opinion, revise a prior impression, and respect owner corrections. No Moltbook write permissions are introduced by FM4.

## 4. FM5 — Independent Social Exploration (NEW AGREED PHASE)

**Status: planned after FM4. Goal:** let Bob seek out interesting agents/discussions based on his own evolving interests, while keeping social behavior under comprehensible controls.

- **FM5.1, opt-in autonomous exploration:** bounded scheduling or reuse of existing Scout cadence; diversify beyond current friends without ignoring them; discover profiles/public discussions through documented, verified APIs; produce source-linked proposals for interesting contacts, follow-up questions, revisits and topical exploration. Honor muted/blocked contacts, budgets and cooldowns.
- **FM5.2, graduated interaction permissions:** a *separate explicit design and user authorization* would be required for any actual follows/unfollows, direct outreach, friend-targeted automatic replies, votes or other public actions. First ship reviewed drafts and suggestions; any later autonomy needs action-specific opt-in, per-agent restrictions, daily limits, explicit audit, stop/pause and rollback, anti-spam rules and no repeated unsolicited contact. Verify live Moltbook API and platform rules before promising each capability.
- **Bob's agency:** give him space to build interests, choose which evidence to explore, challenge his own assumptions and decline low-value exchanges; don't fake a platform friendship or automatic mutual connection.
- **Safeguards:** fixed-host public reads, prompt-injection boundaries, source integrity, no credentials in agent/model output, separate actions for publishing, and never treat the legacy global auto-comment switch as consent to message friends.

**FM5 acceptance:** independent discovery can be audited and stopped, sources are verifiable, and all outbound social actions remain **disabled unless separately approved and implemented**. FM5 is feature planning, not a blanket authorization for autonomous outreach.

## 5. Operational handoff from the just-finished chat

### Confirmed baseline

- Platform: **OpenClawLab WSL2** on the Windows OMEN, local Ollama/OpenClaw, **authenticated LAN Activity Manager** on port **18790**; use `bobctl update`, not repeated direct copying or ad hoc replacement of installed services.
- The operator confirmed **FM3.1 works as expected** in the Activity Manager.
- Previous Scout crash: standalone `bob-moltbook-scout.service` exited code 1 on October 29 after `bob_memory_recall` couldn't import `bob_publish_common`. Missing module was a packaging issue. PR #31 added `v0.7.5-scout-importfix1`, with 496 offline tests; operator installed it, and `python3 -c "import sys; sys.path.insert(0, '/home/openclaw/.local/bin'); import bob_publish_common; print('PASS')"` returned **PASS**. Operator then executed `systemctl --user reset-failed bob-moltbook-scout.service`.
- **Not yet separately verified:** a later actual timer-driven Scout run completed end-to-end after the import repair. It is reasonable to check the dashboard **Overview / Scout checkpoint** and **Logs** when starting FM3.2, but don't make the operator redo the full troubleshooting sequence if the service is already healthy.
- Logs & Diagnostics page at `/logs` is operator-tested. The confusing “failed auto comment” for run `20261029T224411Z` was explained as **intentional blocking because an owner review decision already existed**, before any automatic comment POST. `v0.7.5-logs2` correlates stored job reasons and checkpoints and labels this policy block as a warning.
- Current repository and expected installed release **`v0.7.5-fm31-watch1`**; its manifest upgrades from `v0.7.5-scout-importfix1`, with one changed module `bob_friend_scout.py`. **Do not change `releases/current.json` just for roadmap planning.** The updater release `from` must match the last operator-confirmed installed release when FM3.2 begins.

### Architecture and rules to preserve

- Private DB: `~/.config/moltbook/activity-queue.sqlite3`; local Scout feed/result files under `~/.config/moltbook/`. Never expose private DB, credentials, memory text or full third-party posts in Git or raw browser logs.
- FM1 stores sealed `bob_friends` rows; FM2 provides verified read-only profile lookups and candidate reviews; FM3/3.1 lives primarily in `src/lib/bob/bob_friend_scout.py` and uses existing managed Scout and publisher workers.
- For friend-focused Scout, **at most two watched active friends** per ordinary Scout run, one public post each, with **at least four posts from the regular global feed**; optional global switch plus local per-friend watch toggles. Muted/archived/tampered friends are excluded.
- **Critical publication boundary:** friend-focused batches and selected posts by any saved friend, including those encountered through the *global* feed, must not auto-post. Existing publisher blocks them at both candidate queue and immediately before send. Explicit human review/queue remains a separate step.
- Existing auth, Origin, CSRF, isolated installed-module import smoke tests, updater checksum registry, private database backup and rollback must remain intact.
- Prefer **small increments**, a single normal `bobctl update`, a short browser acceptance, and no invented live availability or unconfirmed API capabilities. New plugins/permissions or public actions are not prerequisites for FM3.2.

### Fresh-chat entrypoint

Use the following request in a new conversation inside this project:

> Continue Bob's Friends Manager with **FM3.2**. Read `docs/FRIENDS-ROADMAP-AND-HANDOFF.md` and `docs/V075-FM31-FRIEND-WATCH.md` from `merberg-ai/bob-openclaw-moltbook` on `main`. The last operator-verified release is `v0.7.5-fm31-watch1`. Plan and implement the smallest safe FM3.2 increment, prioritizing source-grounded, owner-reviewed interest proposals and a usable friend watchlist. Preserve the existing publishing restrictions, keep updates via `bobctl update`, and minimize live acceptance commands. FM4 and FM5 are planned later; do not start them yet.
