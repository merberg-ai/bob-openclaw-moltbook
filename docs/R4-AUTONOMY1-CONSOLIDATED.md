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
- [ ] Real R4 decision/reflector loop using the actual OpenClaw Bob, strict
      schema and provenance; source-linked action proposal ledger and
      owner-reviewed memory/relationship suggestions; no fabricated likes
      or persistent recall.
- [ ] Same existing credentialed publisher, transactional per-action
      once-only attempt and uncertainty ledger, per-category caps/cooldowns,
      explicit Auto opt-in only after signed worker review, owner revocation,
      verified API responses and independent read-back where available.
- [ ] API-specific negative tests: unavailable or changed endpoints,
      malformed source, identity collision, unknown remote following,
      challenge/timeout, duplicate target, pause, crash and restart.
- [ ] One final built + reviewed release, full offline CI, guarded updater
      host preflight, authenticated HTTPS smoke, safe restart and code-only
      rollback with previous attempted history left intact.
- [ ] One owner-confirmed OMEN installation + one integrated acceptance.
      **Do not promote the candidate or alter `releases/current.json` now.**

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
