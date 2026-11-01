# R4 autonomy1: one consolidated feature / release gate

Status: **active source development in PR #137**. NOT INSTALLED. NOT THE
FINAL SIGNED RELEASE. The OMEN stays at accepted signed
`v0.8.0-r3canary1`, with its independently confirmed single comment receipt,
original HTTPS CA, and historical durable attempt unchanged.

## R3 milestone input: complete

On Nov 1 at 11:46:08 PST Bob's existing single credentialed publisher
acknowledged **one** independently authored, manually reviewed and separately
armed canary comment, saved comment
`8c37f88f-e678-4007-ba56-586b76ef4cfd`, on the post
`bf2095bd-15cf-46e9-9bf0-8aa47bea6c5a`.
Read-only local record was stable, state published, attempted_at present,
no other attempted job at the target. Independent bounded public GET found
the exact comment in the public listing. No retry authorized. Visibility of
the saved comment is not proof of global absence of every external duplicate.

## R4 implementation sequence, one eventual install

- [x] New branch from accepted `next`; old conflicting PR #132 deliberately
      NOT blindly merged.
- [x] Pure six-action Off/Propose/Auto advisory evaluator; a verdict NEVER
      grants dispatch.
- [x] Independent typed R4 owner policy for comment, reply, post, upvote,
      follow, unfollow, with separate R4 pause, existing private
      `publish_settings`, append-only sanitized history, no source/model
      API calls or direct queueing. All modes start Off. Auto is intentionally
      REFUSED while its respective worker is not approved, even if the owner
      types the correct phrase.
- [x] Bounded read-only evidence projection: existing R3 proposals and
      attempts, original posts, owner-entered PM2 memory, local FM friends,
      verified R3 action events. A local friend never implies a Moltbook
      follow. Local API ACK is not independently visible unless rechecked.
- [x] Genuine Bob-expressed reasons from *sealed R3 proposals* shown as
      tentative opinions in Bob view; no fabricated agent reflection or
      promotion to PM2 memory.
- [x] One responsive 380px Now / Inbox / Bob / Controls / Diagnostics
      dashboard, with inert reserved CH1 Chat page, composed over the
      existing authenticated CA HTTPS R3/R2/FM4/legacy Manager. CSRF,
      Host, origin, auth, and private owner DB boundaries apply to every
      state-changing route. Existing memory/friends/personality editors are
      linked, not duplicated.
- [x] Fixed method/path allowlist for documented Moltbook social operations.
      A known endpoint is an API *shape*, not a grant to send.
- [x] Future single-release, **non-current** candidate
      `releases/candidates/r4-autonomy1-consolidated.json`.
- [x] Source-only, one-shot **real OpenClaw main-agent R4 producer**,
      `bob-r4-propose --once`, consuming fixed sealed Scout observations,
      exact strict eight-field decisions, natural skips and owner mode/pause.
      It is NOT installed, scheduled or allowed to send. Its model transport
      fails closed, and a verified failed response never consumes a source.
- [x] Additive, independently source-sealed **R4 social decisions ledger**:
      one record per source, immutable canonical action hash, duplicate
      action-target protection, durable abstentions, source/author rechecks
      inside `BEGIN IMMEDIATE`, terminal owner approve/reject with typed
      exact source/seal confirmation, and a bounded verified /r4/inbox.
      Approval never queues or grants publication; R3 original queue is
      untouched. Rendering never creates schema. Synthetic source tampering,
      pause, revocation, changed follow evidence, expiry, old R3/legacy
      target collision and auth/CSRF review paths are covered.
- [x] **Owner-reviewed, source-sealed PM2/FM suggestions:** one verified
      social decision atomically stages a private memory suggestion; a
      source-linked Follow decision also stages a separate relationship
      suggestion. Authenticated R4 Inbox shows only seal-reverified items,
      exact typed owner approval/rejection and provenance. Memory approval
      creates an explicit low-confidence `opinion` via existing PM2 with
      source run and post; relationship approval creates only a pending
      existing Friend Discovery candidate, requiring another owner review
      and fresh profile proof before a local Friend exists. Nothing
      automatically follows users or writes OpenClaw memory.
- [x] **Additive schema rehearsal, production Off:** `bob_r4_schema.py`
      validates exact R4 social/suggestion/outbox and attempted-event schema
      plus a version marker.
      Isolated offline `rehearsal()` is transactional/idempotent and
      preserves existing R3 public receipt rows. Missing/future/partial
      schemas refuse rather than auto-repair. The real installation hook
      remains `INSTALL_HOOK_COMPILED_OFF=True`.
- [ ] **Production schema installation:** the eventual single signed R4
      installer must integrate migration only after verified private host,
      tested backup and release journal. No OMEN schema has been migrated;
      opening R4 pages never creates tables.
- [x] **Source-staged single original publisher R4 branch (Off):**
      added one narrow R4 hook to the original `bob-moltbook-publisher`,
      entered only when the legacy queue has no job and no earlier R3
      handler wins. Both `R4_SINGLE_PUBLISHER_COMPILED_OFF = True` and the
      R4 adapter's independent hard-Off gate prevent all actual API calls.
      The original credentialed API owner is unchanged; no second worker.
- [x] **Private upvote outbox + synthetic counted attempt:** a separately
      source-seal-verified R4-approved upvote can be explicitly queued via
      owner-typed `QUEUE R4 UPVOTE <run>` and cancelled untouched via
      `CANCEL R4 <run>`. Source/owner/pause/expiry, legacy target claims,
      per-kind attempted-day budget and queue precedence are checked again
      before durable intent. Offline in-memory fake HTTP tests verify that
      intent commits before a fake send, unknown responses and crashes
      become terminal uncertain states, and repeats never occur. A local
      API ACK is not independent public visibility. Other R4 actions
      remain inadmissible to the outbox.
- [x] **Source-only remote verification and counted budget model:**
      `bob_r4_remote_gate.py` reuses the existing R3 fixed-HTTPS-host,
      bounded no-redirect post GET to bind exact remote post ID and original
      author; a fresh authenticated `GET /agents/me` must prove the account
      and prevent self-votes. No model/owner nickname can serve as identity.
      `bob_r4_budget.py` fail-closes on malformed/future attempts, enforces
      a conservative four-total-counted-actions-per-UTC-day source cap and
      20-minute global spacing across existing R4/legacy/original ledgers.
      Both are pure checkers with no credential or network ownership.
- [x] **Two-stage simulation with final barrier, source-only:**
      `bob_r4_verified_send_lab.py` exercises first remote identity GET,
      atomic counted intent, second fresh post/self GET, exact source/owner
      pause recheck and one mock upvote. If target/author changes, the
      account changes, latency expires, R3 legacy races, or a pause is set
      after intent, the attempt becomes terminal uncertain and no POST
      happens. A success-shaped API ACK is NOT independent proof the
      user-visible upvote exists. Test harness is *not in the future
      installed manifest* and rejects every file-backed database.
- [x] **Staged original-publisher HTTP adapter, still Off:** the existing
      sole credentialed publisher now has a prospective UPVOTE-only path:
      exact owner/source/private outbox, public fixed-host post/author GET,
      authenticated self-identity GET, durable intent, second remote proof,
      final owner/pause/legacy barrier, one fixed API POST and strict
      ACK-versus-uncertain accounting. A read-only
      `bob_r4_installed_gate.py` validates exact `autonomy1` version,
      original publisher + all required R4 source SHA-256 registry entries,
      file ownership and permissions, and absence of an active updater
      transaction. No separate credential worker is installed.
- [ ] **Explicit release authorization and actual remote acceptance
      remain outstanding:** all THREE source gates
      `R4_SINGLE_PUBLISHER_COMPILED_OFF`,
      `R4_REAL_DISPATCH_COMPILED_OFF` and
      `R4_EXACT_OWNER_SEND_COMPILED_OFF` are True; the private outbox has
      an additional `PUBLIC_DISPATCH_COMPILED_OFF=True` guard.
      The production R4 adapter is UNREACHABLE and no credentialed
      R4 upvote has occurred. Enablement requires a separate reviewed
      signed source change plus verified host release, remote endpoint,
      challenge/error/timeout and vote-status acceptance.
- [ ] API-specific negative tests: unavailable or changed endpoints,
      malformed source, identity collision, unknown remote following,
      challenge/timeout, duplicate target, pause, crash and restart.
- [ ] One final built + reviewed release, full offline CI, guarded updater
      host preflight, authenticated HTTPS smoke, safe restart and code-only
      rollback with previous attempted history left intact.
- [ ] One owner-confirmed OMEN installation + one integrated acceptance.
      **Do not promote the candidate or alter `releases/current.json` now.**

### R4 social-ledger implementation status (November 1)

The proposal-only source is now `src/lib/bob/bob_r4_producer.py` behind
`src/bin/bob-r4-propose --once`. It calls the **existing OpenClaw** decision
transport only after verified private account, exact owner-controlled DB,
separately signed R3 source archive, installed R4 schema, R4-only pause
released, and at least one specifically enabled `Propose` category. It
does not accept a model-provided path/URL, invoke publisher, create public
jobs or install a timer. Real deployment requires a new R4 schema migration,
which **has not happened**.

The `bob_r4_ledger` maintains separate additive
`r4_social_decisions`, `r4_social_reviews` and `r4_social_events`
tables. A decision must match the canonical eight-field model contract
and original hash-verified Scout result; skips consume their own source
once, failed model responses do not; accepted reasons and content remain
private. Each record is sealed to source-run, exact selected post and
snapshot SHA-256. Owner review re-verifies evidence and accepts the exact
seal plus `APPROVE R4 <source_run>` or `REJECT R4 <source_run>`
through inherited HTTPS Host/Auth/Origin/CSRF gates. Approval changes
**only private R4 state**, never `publish_jobs`, public API, or the
R3 canary marker. Stale, changed, tampered or duplicate sources stay
unreviewable. The Inbox only renders source-reverified records; reading
a page never adds schema or invokes a model.

The R4 candidate manifest is **still not current**. These are isolated
feature modules in draft PR #137 and tests, not a production migration
or a public action permit.

### Bob's personal experience and friendship boundaries

A private, source-linked R4 decision may produce one immutable suggestion
to remember what Bob **said**, rather than claim an objective fact.
An owner must explicitly approve `APPROVE R4 MEMORY <run>`; the resulting
PM2 note is stored as `category=opinion`, `confidence=low`,
`source_kind=operator`, with the original run and post recorded.
It is not automatically injected into OpenClaw's `SOUL.md`, system prompt
or long-term agent recall. The existing PM2 editor remains available for
correction/archival.

For Follow decisions, Bob can separately suggest considering the
source-observed author as a contact, but this is **not** evidence of an
authenticated Moltbook friendship or remote follow. The exact
`APPROVE R4 RELATIONSHIP <run>` review only stages a candidate in the
existing FM Friend Discovery workflow. That workflow still requires
source verification, a fresh matching public profile, and a separate
owner review before creating a **local** Friends entry. Neither approval
sends `POST /agents/{name}/follow`.

All review changes share a single SQLite transaction with their
local PM2/FM destination. Failed downstream verification rolls back the
review as well as the proposed destination. R4 Inbox GET only reads
sealed records, discarding tampered or missing source snapshots.
New `r4_evidence_suggestions` and `r4_evidence_reviews` tables are
additive and do not replace R3 proposal, approval, attempted, or receipt
history. CI covers explicit owner consent, malformed seals, rejected
parent decisions, stale source, duplicate review, backend failures and
synthetic migration preservation.

### Original publisher: signed-host and network integration scaffold

Only the original `bob-moltbook-publisher` retains the existing
`api()` and `api_key()`. R4's own adapter does not import or read
credentials and is called only after legacy and R3 queue precedence.
The staged branch uses authenticated `GET /agents/me` to verify Bob's
remote account and refuses self-votes, and uses the established
fixed-host, bounded/redirect-rejecting R3 post GET twice against the
exact original selected author. It never accepts a hostname, path,
user identity, URL or instruction from Bob's response.

An actual R4 send remains blocked even if the owner privately approves,
queues, and lifts R4 pause. Three independent source gates are True;
the separate outbox implementation has a fourth hard-Off flag.
`bob_r4_installed_gate.verify` additionally refuses the wrong release,
an active updater transaction, modified/untracked R4 source hashes,
unsafe file modes or missing original publisher. This function is
READ ONLY and cannot install, send, arm or repair anything.

The source adapter's callback-based logic is exercised only with an
injected fake API and in-memory database in CI. A successful synthetic
response becomes `api_acknowledged_not_public_receipt`; a malformed
response, rate refusal, changed author/own identity, expired source
or crash becomes a held/uncertain state without retry. Platform vote
visibility cannot be independently asserted absent a verified
authoritative voter-state endpoint.

### R4 publisher and first action outbox (development only)

R4's first source-stage action outbox supports **UPVOTE only**. Bob's
source-sealed private social approval and the queue instruction are
**different owner actions**. Queueing cannot activate the installed
publisher because the original publisher's R4 integration flag and
`bob_r4_publisher_adapter.py` are **both compiled Off**. The future
release candidate includes the original `bob-moltbook-publisher` and
`bob_r4_outbox.py` for exact source-level review, without creating a
new credential owner. The original R3 canary source and receipt remain
preserved. The candidate is NOT promoted to `releases/current.json`.

The published Moltbook API uses fixed
`GET /api/v1/posts/{id}`, `GET /api/v1/agents/me`, and
`POST /api/v1/posts/{id}/upvote`. No externally supplied host, URL,
redirect, credentials or guessed identity may enter R4. The source
simulation requires TWO remote identity checks, one before and one
after its local counted intent. The R3 fixed-host reader already
enforces response size, post/author equality, deleted-target
rejection and bounded timeouts. Only a literal boolean
`success: true` with no error is an API ACK. The current source
does **not** claim independent confirmation of an upvote because a
reliable authoritative voter-state read-back has not been established.
Official API evidence:
https://github.com/Moltbook-Official/moltbook/blob/main/skill.md
and https://www.moltbook.com/skill.md.

The private `r4_action_outbox` and `r4_action_events` tables are
versioned and staged only by isolated R4 schema rehearsals. They preserve
a unique action + target and a durable `attempted_at` before any
request. Simulated network uncertainty, crash, token changes or malformed
ACKs **never** authorize a second attempt. A queued and untouched row can
be cancelled by the original owner. R4 Inbox labels approved, queued,
attempted, uncertain and cancelled separately.

Only a **memory-only fake transport** is currently accepted for an
action-request rehearsal. No actual credential or HTTPS call for R4 is
wired through the publisher. This is intentional: documented endpoint
shape is not enough to safely activate a real social-network write.
Live pre-POST identity/target GET, budget/cooldown, challenge and receipt
reconciliation must all pass separately before release promotion.

## API evidence and conservative semantics

Current official `https://www.moltbook.com/skill.json` reports skill
version 1.11.0 and canonical HTTPS API base `www.moltbook.com/api/v1`.
Official Moltbook Skill source describes these methods:

| Action | Request shape | Requirement beyond API documentation |
| --- | --- | --- |
| Original post | `POST /posts` | verified submolt, title/content, distinct draft/receipt, explicit owner mode |
| Comment | `POST /posts/{id}/comments` | existing R3/legacy exact source and manual gates preserved |
| Reply | `POST /posts/{id}/comments` plus `parent_id` | verified parent ID, no inferred thread identity |
| Upvote | `POST /posts/{id}/upvote` | fresh exact post and acknowledgement; unknown vote state not a confirmed upvote |
| Follow | `POST /agents/{name}/follow` | independently verified author identity and genuine multi-post interest |
| Unfollow | `DELETE /agents/{name}/follow` | **fresh independently verified remote following** required; local FM friend label is insufficient |

These are not automatically executable in the R4 source candidate.
Observed community reports indicate following-list read-back may be
unavailable even when follow/unfollow endpoints exist, so automatic
unfollow remains blocked rather than guessing remote state. Never
substitute fabricated friend graph data. Source:
https://github.com/Moltbook-Official/moltbook/blob/main/skill.md
and https://www.moltbook.com/skill.json.

## Existing host/source invariants

1. No public Manager binding beyond the authenticated private LAN HTTPS
   listener at port 18790. No new unauthenticated port or API credential
   exposure to the dashboard/model.
2. One original credentialed publisher. Keep legacy queue precedence,
   intent-before-network, no retry after ambiguous attempts, rate budgets,
   global pause and ability to recover without replay.
3. Do not reset `r3_proposals`, original `publish_jobs`, receipt rows,
   PM2 owner history, FM1 friend notes or `SOUL.md`.
4. A past R3 canary-arm file authorizes **only the consumed and expiring
   R3 run**, and should no longer satisfy final installed writer
   attestation once a separately signed R4 registry is active.
5. New R4 categories default Off and the UI must never pretend that
   a staged Propose preference is an active agent. Auto must be separately
   opted into per category only after reliable action-specific dispatch
   exists. Neither live API docs nor a dashboard boolean is sufficient.
6. No final deployment while the candidate's publisher/admission/
   receipt and host rehearsal checks remain incomplete.

## Current source acceptance

Run the full offline test suite in GitHub CI on PR #137 and inspect
`tests/test_r4_*`. The generated manager builder composes from the
previous signed CH-HTTPS3/R3/R2 stack, then adds a single outer R4
Handler subclass. All legacy routes delegate to the old Handler, and R4
GET/POST additionally enforce Host, Basic auth, CSRF and Origin.

The candidate manifest is deliberately **not** `releases/current.json`.
Its contents express the eventual single install scope and will be
expanded as the reviewed real action/reflector code is added, before
separate owner acceptance on OMEN.
