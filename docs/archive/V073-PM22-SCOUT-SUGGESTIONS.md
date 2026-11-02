# PM2.2a: source-verified Scout suggestion inbox

**Candidate:** `v0.7.3-pm22-scout-review1`, from operator-verified `v0.7.3-pm2-editfix1`.

## Delivered scope

A new authenticated **Bob's Mind → Suggestions** dashboard at `/mind/memory/suggestions` presents saved Bob Scout draft comments which can be **staged** for private memory review by the operator.

1. **Source:** only an existing `scout-result-<run-id>.json` that still passes `bob_publish_common.load_record()` verification against its original saved feed snapshot, post ID, generated draft SHA-256 and approval SHA. No internet calls, unsupported inferred Moltbook links or guesses about live source authenticity.
2. **Stage:** the operator explicitly chooses a verified Scout run. The app stores Bob's prior draft text as a pending, untrusted suggestion with source run ID, post ID, SHA-256 fingerprints and a separate private inbox ID. **No memory is created** at staging.
3. **Review:** the operator reviews and may rewrite the proposed title/text, category and confidence. A typed reason is required to **Approve as private memory** or **Reject suggestion**. Provenance is set by the backend and cannot be changed by form fields.
4. **Approve:** reverify the real local Scout source and stored fingerprints; reject absent/changed feeds or drafts, stale form tokens and already-reviewed suggestions. Create one existing PM2.1 private memory, linked to the review record, in the same SQLite transaction as the approved decision. Existing memory revision history still applies.
5. **Reject:** keep an audit record and reason, without adding any memory.
6. **Deduplicate:** one suggestion per Scout run ID, with 50 pending and 250 total bounded inbox records. Each candidate appears once; reviewed decisions remain visible.
7. **Isolation:** no worker/service identity, Ollama, OpenClaw, Moltbook API calls, external publishing, automatic memory recall, automatic generation or direct trust promotion. All external/source text is HTML-escaped and treated as lower-trust context.

**Accuracy boundary:** this release does **not** generate novel LLM summaries from discussions. The initial inbox uses *Bob's already generated, locally verified Scout draft comments* to establish and test review/provenance. A future separately reviewed phase can ask the model to propose distilled notes. A stored Scout snapshot proves provenance and consistency with the source captured locally, **not that the public discussion or Bob's draft is factually true**.

## Data and backups

Additive table `bob_memory_suggestions` in the same private SQLite database. It does not rewrite `bob_memories` schema, current memories, existing publication decisions or queue state. The existing updater takes a protected SQLite backup before installing code and restarts **only Activity Manager**.

Archive/retention/export for suggestion rows and automated suggestion generation are deliberately deferred until explicit review. The inbox is capped rather than silently deleting provenance.

## Operator acceptance

1. Run `bobctl update --check` then `bobctl update`; verify the release chain `v0.7.3-pm2-editfix1` → `v0.7.3-pm22-scout-review1`; type `UPDATE`.
2. Open **Bob's Mind → Suggestions** on the authenticated LAN dashboard. Select a locally verified Scout draft in **Stage from existing Scout work**, then click **Stage for memory review**.
3. Refresh: the draft appears in **Suggested memories · review inbox**, with its original run ID, source post ID and untrusted text. The main **Memory** list must remain unchanged until approval.
4. Edit title/content to a short accurate observation, select category/confidence, provide reason, and click **Approve as private memory**. Verify it appears in **Bob's Mind → Memory** and the recent decision links to it.
5. Stage a different verified Scout draft, supply a reason and **Reject suggestion**. Verify no second accepted memory appears. A duplicate stage or replayed submission should fail closed.
6. Confirm **Scout & review**, original publishing and Personality still behave as before. No new Moltbook posts or model calls should be triggered by the inbox.

## Next gated phases

- **PM2.2b:** model-authored candidate extraction with immutable source IDs, structured outputs, prompt-injection-resistant validation and human review only; privacy-safe export/retention planning.
- **PM2.3:** explicit opt-in, read-only, bounded recall of approved active memories, never tool/persona instructions.
- **FM1:** only after PM2 complete and operator-tested.
