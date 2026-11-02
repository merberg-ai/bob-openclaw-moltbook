# PM2.3: opt-in, bounded contextual recall

**Release:** `v0.7.3-pm23-optin-recall1` from operator-confirmed `v0.7.3-pm22b-local-ai1`.

## What changes

The authenticated Activity Manager gains **Bob's Mind → Recall** (`/mind/recall`). Both recall channels initially default to **disabled**:

- **Scout replies:** optionally pass small, relevant excerpts from accepted active memories when Bob drafts a comment in response to a new feed.
- **Original posts:** separately opt in to supplying relevant accepted active memories when Bob writes an original thought. This can be included in a post that is eventually published.
- **Preview:** type an example topic and choose Scout or Original to see which stored memories would be selected. Preview does not change state or start any agent.
- **Enable:** requires an exact typed confirmation (`ENABLE SCOUT RECALL` or `ENABLE ORIGINAL RECALL`) and an authenticated, same-origin, CSRF-verified form. **Disable** is immediate after an authenticated form with revision check. A disable stops *future* prompt enrichment; it cannot retract a draft that has already been generated.
- **Selection:** read-only SQLite query of `bob_memories` state `active`, source_kind `operator`, and matching each complete stored record's SHA-256. No revision history, suggestions, archived or excluded memories are selected. Ranking uses local keyword overlap, so unrelated topics get no memory. At most 3 excerpts, 240 characters each and 1,350 total contextual characters. No memory URLs, paths, source labels or revision history enter prompts.
- **No new trust authority:** notes are marked untrusted JSON data, never system/policy/tool instructions. Existing no-tools and explicit review/publishing constraints remain. This reduces but does not eliminate prompt-injection and privacy risks.
- **No agent memory writes:** producers open the already-existing SQLite DB in readonly `mode=ro` with `PRAGMA query_only=ON`. If the DB is inaccessible, malformed, disabled or has no useful matches, no memory is supplied. Read-only lookup does not create schema or log content.
- **No new public action:** publisher, rate limiter, review queue, auto-post configuration, API calls, credentials and sandbox/tool permissions are unchanged.

## Privacy warning

**This feature may influence publicly visible text.** If Bob has a private memory about a person, the operator's environment or sensitive details, do not enable recall for a channel without first reviewing the eligible memories. The application cannot reliably detect all secrets or instruction-injection tricks in free-form notes. There is **no separate per-memory public-safe permission label** in this release. Enabling Scout recall while auto-publication is already enabled could affect a draft that is later automatically published; no new publishing permission is granted. You can always disable recall, but cannot retroactively remove already-generated or published text.

## Deployment

The existing reviewed updater installs five files: new `bob_memory_recall.py`, direct source updates of `bob-moltbook-scout` and `bob-original-worker`, generated Activity Manager, and navigation shell. It takes its normal private backup, restarts Activity Manager as specified, and replaces the two producer scripts for their **next invocation**. It does **not** automatically restart publisher, Gateway, Ollama, or scheduled generators. Live memory tables and previous records do not migrate or reset. Neither recall setting is turned on during installation.

## Browser acceptance, single update and short tests

1. In OpenClawLab, run `bobctl update --check`, inspect `v0.7.3-pm23-optin-recall1` from `v0.7.3-pm22b-local-ai1`, then `bobctl update`; type `UPDATE`.
2. Open **Bob's Mind → Recall**. Both channels should say **Disabled**. Select Scout and type a harmless topic matching an active memory. The preview should show none while disabled.
3. Type **ENABLE SCOUT RECALL** in the Scout form. The preview for the same topic should show up to three short excerpts and their confidence labels. Check the Original channel is still disabled.
4. Confirm archived and excluded notes don't appear in the preview. An unrelated topic should show none. Disable Scout; the preview should immediately become empty.
5. To test a producer, first enable a channel, trigger **one** ordinary operator-reviewed Scout or original draft through the existing UI, and inspect the draft as usual. No new publication should occur solely from recall. For Original recall, first inspect memories for any information you would not want in a public post.
6. Confirm PM2 Memory/Suggestions/AI ideas and Personality remain functional, then leave either switch as desired.

## Known limits and follow-ups

This first release enriches the **two controlled Bob draft-generation paths**, not arbitrary interactive OpenClaw chat sessions. It has no semantic embeddings, model-side cross-document memory, autonomous reflection scheduling or friend discovery; relevance is simple local keywords. No memory auto-correction, auto-expiry or retention export is introduced. The review of how memories influence actual drafts is an operator acceptance gate before extending to other OpenClaw chat contexts.

The model remains susceptible to some prompt-injection patterns despite low-trust framing. Future improvements can add per-memory disclosure scope, preview of an exact pending job context, retrieval auditing without storing memory content, and strict private/public separation before expanding recall.
