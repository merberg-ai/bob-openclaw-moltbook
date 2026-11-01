# R3 first public canary → consolidated R4 autonomy delivery

Status: **engineering foundation only; no public R3 canary and no R4 production release**.
Track all remaining feature engineering on one R4 branch/PR sequence and deploy
**one** versioned `v0.8.0-autonomy1` release after the independent live R3 canary
has been accepted. This document is not a live-host instruction to enable posting.

## Natural skip replay diagnosis and source-only repair

At 20:38 PDT the next genuine timer tick again returned `skipped` with
`source_run=20261101T024801Z`, exactly the same source as the 20:01 tick.
Source audit found that R3 previously filtered proposed/queued sources but did
**not persist accepted skips**. Unless another newer eligible Scout source
appeared, Bob could be asked about one snapshot repeatedly.

The development branch now writes a validated, source-linked **skip event** to
the *existing* `r3_lab_audit` table and excludes that source run from later
natural selections. Invalid model output, transient OpenClaw failures and
unverified files are **not** recorded as a legitimate Bob abstention. A valid
skip remains a skip: no fabricated comment, queue, approval, key or public POST.
Concurrent duplicate skip markers fail closed, and source files are reverified
before the event is committed. Offline tests cover persistence, natural
advance to another saved Scout source and refusal/immutability.

**Important release boundary:** the new behavior is *not* installed on the
OMEN. The accepted `v0.8.0-r3format1` archive is still built from immutable
baseline copies of the two changed source modules. A future separately signed
release must use explicit `build_development()` or another reviewed versioned
builder and the normal owner-approved updater. Do not mutate the accepted
release identifier or assume the current proposal timer already records skips.
R3 public sending remains compiled Off and independent of this correction.

## Confirmed boundary (October 31, 2026)

The operator accepted installed signed `v0.8.0-r3format1`. The natural R3
proposal timer ran at 20:01 PDT. Bob returned `skipped` with reason
`bob_chose_not_to_comment`. This is a **valid model decision** and evidence
that the strict JSON contract worked. It is **not** a `proposed` sealed draft,
owner approval, queued item, public comment or independent public receipt.

The original Scout and one credentialed legacy publisher remain intact.
All existing R3 live dispatch switches remain compiled Off. In particular,
the R3 proposal producer has no key, network POST or authority to send.
Neither the source-only R4 evaluator nor a dashboard setting can override that.

## Finish R3, with exactly one genuine candidate

1. **Observe, never manufacture:** wait for a *natural* scheduled R3 tick
   yielding `proposed` from a fresh, independently saved Scout source. A
   `skipped`, `none`, refused, malformed or stale decision remains a
   legitimate non-candidate. Do not invoke the producer manually, replay a
   source or weaken its five-field validator to elicit a draft.
2. **Inspect safely:** after updating only reviewed checkout source, run
   `python3 scripts/report_r3_first_draft.py --check` from `~/bob-next`.
   This only opens the fixed real queue SQLite in read-only mode, verifies
   the installed R3 package and source seals, and reports counts and run IDs,
   **never the draft text or credentials**. The authenticated HTTPS `/r3`
   page is the sole place to inspect Bob's *exact* reason, text and source.
3. **Explicit separate owner review:** reject unsuitable content. For one
   genuinely selected run, enable independent R3 manual control with its
   existing typed phrase, approve its exact sealed draft, then separately
   queue it with `QUEUE BOB COMMENT`. Existing approvals never carry over
   from legacy Scout and never authorize a send. Recheck target uniqueness,
   source freshness and pause. A queued draft is still held.
4. **Source-level canary unlock is a separate reviewed change:** stage a
   minimal **manual-only, one-run, one-seal, one-target, expiring** publisher
   allowlist. Do not flip all three R3 dispatcher flags to broadly enable
   every queue row. Require the pinned installed package/registry, exact
   owner-approved action, existing one credentialed publisher, final public
   GET/source check, budget, pause, duplicate and atomic durable intent.
   No second publisher or credential exposure. CI must show zero writes
   without that exact owner capability, including race/reboot/expired cases.
5. **One bounded real send only after independent authorization:** install
   the reviewed signed canary release with typed owner approval and explicitly
   authorize *that exact* target/draft. Preserve the nonretryable
   `attempted_at` record before POST. API ACK alone is not a public receipt.
   Verify the exact saved remote comment ID with a bounded anonymous public
   GET, or keep ambiguous responses `uncertain` without automatic replay.
6. **Close R3 or stop:** compare before/after queue histories (especially
   the existing 23 historical attempts), pause and duplicate protection,
   proposal/legacy timer and publisher single-writer state, HTTPS health and
   code-only recovery. Do not restore SQLite over a possible public send.
   Only a confirmed canary or a deliberately documented no-send stop can
   unlock the R4 production decision.

### What can be run now

On OMEN, the proposal-only timer is already active. No new timer or
publisher action is needed. The next naturally observed outcome can be
viewed using read-only `journalctl --user -u bob-r3-propose.service
--since '1 hour ago' --no-pager -n 30`. The repository report is read-only
and requires a reviewed checkout; it cannot itself supply or invent a
`proposed` decision.

## R4: one integrated feature/release, not a chain of micro-installs

**Branch and candidate:** `feature/r3-canary-r4-consolidated-foundation` for
source development against `next`; reserve `v0.8.0-autonomy1` for the
later single signed install. Keep `releases/current.json` and the OMEN
installation unchanged during integration.

### Work streams combined in one candidate

- **Policy and action envelopes:** six strict actions `comment`, `reply`,
  `post`, `upvote`, `follow`, `unfollow`; skip as valid abstention.
  Central Off/Propose/Auto switches and independent category-specific typed
  owner opt-in. A pure advisory evaluator is added first, but its
  `candidate_auto` verdict is **never** dispatch authority. The verified
  signed one-publisher adapter remains the only external writer.
- **API evidence first:** document real Moltbook request/response shape,
  scope, rate-limit and public verification of each action. Missing,
  undocumented or mutable endpoints stay unsupported and Off. A local
  Bob friend is not proof of following or mutuality; unfollow requires
  independently verified remote-following evidence.
- **Single-writer lifecycle:** append-only source/proposal/attempt/ACK/
  verified/uncertain ledger; atomic reservation and idempotency per
  category, global and per-action hard caps, cooldowns, duplicates, source
  age, pause, immutable owner approvals and no-replay uncertain outcomes.
  Manual-first precedence and original-post review remain unchanged.
- **Bob's evolving social perspective:** consolidate FM4.2 corrections,
  FM4.3 optional owner-reviewed recall, FM5 discovery and relationship
  reflections. Mark each item as observed fact, Bob's tentative opinion,
  owner-confirmed, or unverifiable. No silent edits to identity/PM2 memory,
  no fabricated relationships or remote actions.
- **One responsive authenticated HTTPS Activity Manager:** Now (live state,
  last decision, budgets), Inbox (sealed review and digest), Bob (interests,
  social history, reviewable memory proposals), Controls (category dials,
  pause and hard-cap readout), Diagnostics (bounded sanitized events).
  Retain the current `/r3` and legacy routes through an accepted release.
  Reserve a visible but inert Chat route for later real OpenClaw CH1.
  Test navigation/forms at 380px and at desktop width; preserve LAN-only
  authentication, origin checks, CSRF and CA HTTPS.
- **Experience digest/anomalies:** derived only from durable Scout and
  publisher observations; distinguish seen/drafted/queued/attempted/
  acknowledged/publicly verified. Skip and uncertainty are valid. Repeated
  malformed model decisions or verification mismatches trigger a safe
  hold with evidence, not auto-resubmission.

### One release acceptance gate

CI runs entirely offline and includes strict parser/prompt-injection,
unsupported API, identity/personal data separation, duplicate and crash
races, consent revocation, rate-limit, manual-first, restart, upgrade and
rollback, 380px layout and authenticated route tests. An isolated OMEN
rehearsal then proves exact signed manifest, HTTPS CA, preserve-only data
migration, one credential owner, timer ownership and rollback. The operator
gets **one** `bobctl update` and **one** consolidated installed report.
New categories remain Off/Propose on install. Each Auto mode requires
separate opt-in and verified evidence even after R4 acceptance.

### Moltbook API discovery snapshot (not production endpoint authorization)

Checked October 31, 2026: official
[skill.json](https://www.moltbook.com/skill.json) reports version **1.11.0**
and points to [the live skill reference](https://www.moltbook.com/skill.md).
Publicly documented/example operations suggest these **candidate** adapters:

| Action | Candidate method/path | Additional verified evidence needed |
| --- | --- | --- |
| original post | `POST /posts` | destination submolt, title/content format, challenge and receipt |
| upvote | `POST /posts/{post_id}/upvote` | exact post and vote ACK/remote state |
| follow | `POST /agents/{name}/follow` | actual public agent identity and followed state |
| unfollow | `DELETE /agents/{name}/follow` | **current remote following**, not local friend list |
| reply | `POST /posts/{post_id}/comments` with parent linkage | thread semantics, exact parent and receipt |

Do **not** treat a community report as API contract. A March 2026
[agent endpoint audit](https://www.moltbook.com/post/732d5881-af80-414d-9e62-19a4bee67855)
reported that read-back following/follower list endpoints were unavailable.
Therefore automatic unfollow stays Off unless a current documented,
fresh and verifiable remote relationship can be established. Version
metadata alone never unlocks any endpoint. All public write tests remain
in-memory/synthetic until separately owner authorized.

### Non-goals

No anonymous/public Activity Manager, second publisher, unrestricted
model-origin URLs, API keys in a model session, invented Moltbook API, fake
social follow graph, mandatory CH1 Chat in R4, schema-destructive reset,
or forced real model decision. Do not interpret this foundation PR as a
candidate release, a successful public canary, or permission to change host
services.

## Exact canary source lock prepared, still hard Off

The existing single credentialed publisher now has a *second, narrower*
source-level barrier at `src/lib/bob/bob_r3_canary_lock.py`. Its immutable
`PIN = CanaryPin()` is empty in this branch, so **no future R3 send can
succeed merely by changing older enablement flags**. A later reviewed signed
manual-canary release must pin one concrete observed run, sealed source hash,
UUID target and expiration, in its **source**, and package that exact source
through the guarded updater. There is no environment or dashboard override.

Even with a future pin, the existing owner permission, source verification,
original publisher and shared durable-attempt ledger remain required.
The pinned run is checked again when selecting the candidate; target and
expiration are checked just before the credentialed POST. Expired/ambiguous
attempts cannot automatically retry. This is a defense-in-depth *candidate*
and not evidence of a completed source review, model proposal, receipt or
installed release. CI must run the complete adapter and race/crash suite
before preparing a future send-capable candidate.

## Source baseline of this foundation change

- `scripts/report_r3_first_draft.py`: read-only, content-free host check.
- `tests/test_r3_first_draft_report.py`: skipped/proposed/approved/queued/
  attempted and untrusted-schema invariants.
- `src/bob_v08/r4_policy.py`: pure, no-I/O and default-Off advisory rules.
- `tests/test_r4_policy.py`: explicit opt-in, unverified API, pause,
  duplicate, cooldown, caps and genuine remote-following invariants.

These are source engineering, **not the finished R4 release**. Subsequent
implementation for UI, event projection, source-verified adapters and
versioned upgrade must land in the same consolidated milestone before
promotion.
