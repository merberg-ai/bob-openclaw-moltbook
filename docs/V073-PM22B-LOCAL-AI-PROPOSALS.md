# PM2.2b — on-demand local AI memory proposals

**Release:** `v0.7.3-pm22b-local-ai1`, from operator-verified PM2.2a `v0.7.3-pm22-scout-review1`.

## Scope and limitations

A new authenticated dashboard page **Bob's Mind → AI ideas** at `/mind/memory/ai` shows verified Scout sources, local generation status, untrusted AI proposals, and owner approval/rejection. It generates **new concise memory ideas** (observations, questions and tentative opinions) from a real selected, saved Moltbook Scout post. This is not generic reformatting of an old draft.

- Generation is **manual, never scheduled**. After owner POST+CSRF, the server stores one queued job and starts one daemon thread **after** the database transaction commits, avoiding a blocked browser request.
- The worker reads only the chosen post from the saved, checksum-verified Scout snapshot via the existing `load_record` verifier. It takes no Moltbook API credentials, and **does not fetch any external content**.
- One bounded model call through Python stdlib HTTP client to **127.0.0.1:11434/api/generate** (local Ollama), with optional `BOB_MEMORY_OLLAMA_MODEL` (default `qwen3.5:9b`). The model call has a 90-second network timeout, is non-streaming, bounded to 65,536 response bytes, and is asked for strict JSON and 0–3 proposals. It has **no OpenClaw agents, tools, browser, or publisher capabilities**.
- Returned candidates must contain a source post ID exactly matching the verified post and a small schema of title, note, category, low/medium confidence and rationale. Overlong, malformed, contradictory source IDs, unsupported confidence/status, or some obvious instructions/prompt tokens fail the entire batch. **This is not a guarantee of factual truth or a full defense against prompt injection**: all proposed text remains untrusted and must be reviewed.
- One active job at a time (database unique partial index), three generation attempts per Scout run, max 3 proposals/job, 30 pending / 120 total proposals. Exact deduplication of normalized same-run proposal content, persistent state `queued/running/completed/failed`, and friendly status text. Interrupted stale jobs are marked failed, not silently retried.
- **Approval is always manual**. Owner can edit the candidate title/text, category and confidence and must supply a reason. Only then does the reviewed proposal become a new private PM2.1 memory. Source attribution is server-owned (Scout run and post ID) and reverified before acceptance. Rejection creates no memory. Review decisions and source fingerprints stay local.
- Failed generations store only fixed error codes. Raw model output, host exception tracebacks, private directories and credentials never appear in dashboard error pages.
- Data are in additive private SQLite tables `bob_memory_ai_jobs` and `bob_memory_ai_proposals`; no change to existing memory records/PM2.2a tables or publication state. No auto-recall, SOUL.md/IDENTITY.md editing, scheduled reflection, publishing or outbound Moltbook activity.

### Runtime/network prerequisite

Ollama must be reachable from **OpenClawLab WSL2** on its loopback interface `127.0.0.1:11434`, with model `qwen3.5:9b` available (or a model set in the Activity Manager's process environment via `BOB_MEMORY_OLLAMA_MODEL`). This is **not the same test as Ollama being available from Windows**. If WSL networking does not forward loopback, jobs will display **Local Ollama could not complete the request**. Do not expose Ollama publicly to make this work. Any explicit trusted-LAN host configuration belongs in a separate hardened connectivity change.

The Activity Manager itself currently uses HTTP Basic on a trusted LAN and is **not HTTPS**. Memories may be personal: keep it private behind VPN or a TLS reverse proxy, never public Internet.

## Acceptance

1. From WSL OpenClawLab run `bobctl update`. Confirm the exact path `v0.7.3-pm22-scout-review1` to `v0.7.3-pm22b-local-ai1` (three installed files) and approve with `UPDATE`. Activity Manager restart only.
2. Visit **Bob's Mind → AI ideas** and choose one previously verified Scout post. Click **Ask local Ollama for memory ideas**. The request should promptly redirect to the same page with a queued/running status. Refresh later to see completed or failed status; there is no fake percentage.
3. If completed, inspect 0–3 proposals. Model-generated text is marked unverified, with source run ID/post ID, rationale and confidence. If Ollama is not accessible, the page reports an accurate fixed failure status; it must not hang indefinitely.
4. Edit a proposal for accuracy, enter a reason, and approve. It appears as a new private memory with source attribution. Reject a second proposal and verify it is not added.
5. Attempt to resubmit a stale review form: the server must refuse a second memory. Check **Scout & review**, **Bob's Mind → Suggestions**, **Personality** and existing queued posts are unchanged. No new Moltbook post is authorized or generated.
6. Verify the new job can recover from process restarts without repeating API requests; stale jobs become failed, and no auto-retry occurs.

## Follow-ons

PM2.2b is **operator-triggered**. For truly autonomous but safely permissioned suggestion *scheduling*, build a separate PM2.2c job worker with model/publisher privilege separation, source privacy retention/export, additional evidence validation and explicit opt-in. PM2.3 remains explicitly opt-in **bounded read-only recall of owner-approved active memories**, never control prompts or tool instructions. FM1 Friends Manager comes after PM2 acceptance.
