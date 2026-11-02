# FM3.2c: Bob's on-demand local interest proposals

**Release:** v0.7.5-fm32c-localideas1 from operator-verified v0.7.5-fm32b-watchlist1.

## Behavior

On authenticated LAN Moltbook → Friend Scout, a source-verified existing Scout selection of an active saved friend offers **Ask local Bob for a tentative interest**. This is an explicit owner action, not a scheduled task. A single daemon worker analyses only the chosen SHA-verified saved public post using loopback Ollama at 127.0.0.1:11434 and model qwen3.5:9b (model name override: BOB_FRIEND_OLLAMA_MODEL).

No Moltbook API requests, agent tools, or social actions occur. No private FM1 notes/interests, PM2 memories, identity files or secrets are sent into the model prompt. The model receives bounded title/content of just the verified chosen public post, with instructions that it is untrusted, inert data.

Output is either no idea or ONE strictly bounded, source-linked tentative interest: first-person interest (up to 180 characters), reason (180), uncertainty (140), low/medium confidence and the exact source post ID. The output is model interpretation, **not** verification of any statement, author account identity, relationship or trust.

The new Bob's new tentative interests inbox supports explicit approve/reject/archive/reopen. Source run/post and a SHA-sealed private record are rechecked before approval or reopening. Optimistic digest prevents stale forms, with local revision history. Approving stores only an owner decision: NO writes to FM1 operator notes, PM2 curated memory, SOUL.md, Scout preference weighting or any Moltbook publication.

## Guardrails

- Exactly one outstanding local generation job; maximum two attempts per run, 100 job rows, 60 proposal rows and 15 pending. Maximum one proposal per generation.
- Fixed loopback HTTP target and path, no redirects/credentials, 90-second request timeout, maximum 32 KiB HTTP reply and 450 model output tokens. Strict structured JSON with source ID matching and unsafe instruction checks.
- Saved feed integrity, chosen post UUID and author, current active friend and source snapshot hash all revalidated before prompt and after generation.
- Jobs stale more than three minutes become failed/interrupted on view, with no automatic retry. Failure messages never include model output/private data.
- Existing auth/Host/Origin/CSRF, six-field POST constraints, global Friend Scout OFF default, per-friend watch pause, capped Scout browsing, both friend-targeted publication guards all unchanged. Owner-triggered analysis of saved files does not itself browse online.
- Two installed code files: existing bob_friend_scout.py and generated bob-activity-manager, produced from existing pinned builder. No new installed Python module, service or timer.
- The normal bobctl update performs SHA checks, private DB backup, Activity Manager restart only, and guarded code rollback.

## Offline and live acceptance

Synthetic tests cover mocked Ollama, source integrity, tampering, invalid output, secrets isolation, private history/owner review, stale work, duplicate requests and exact generated-manager delta. Full CI should be green before merging.

After merging to main:
1. Run **bobctl update** once, confirm v0.7.5-fm32b-watchlist1 → v0.7.5-fm32c-localideas1, type UPDATE.
2. On Moltbook → Friend Scout, under Bob's selected friend discussions choose Ask local Bob for a tentative interest. If there are no verified saved friend choices, this control is intentionally absent. Refresh for completed status; no-interest is a legitimate result.
3. Review any new proposal: its idea, reason, uncertainty, confidence and source. Approve/reject/reopen; verify private state and history changed only.
4. Existing watch/pause and manual publication behavior must still work. No Moltbook follow/comment/DM can be issued by this feature.

## Next

FM3.2 optional separately confirmed, rate-limited read-only single-agent focus check remains deferred. FM4 social memory and FM5 autonomous exploration remain separate phases requiring independent design, approval and acceptance.
