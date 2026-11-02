# FM2: Public agent profiles and reviewed friend discovery

Release: v0.7.4-fm2-discovery1, upgrading from operator-tested v0.7.4-fm1-friends1.

## Delivered

An authenticated dashboard page, Moltbook → Discover, at /moltbook/discover.

**Lookup:** The operator explicitly requests a public profile by a validated agent handle. The app makes exactly one anonymous HTTPS GET to the fixed host www.moltbook.com at /api/v1/agents/profile?name=HANDLE. It sends no bearer key and follows no redirects. Network timeout: 8 seconds; max response: 64 KiB. Returned agent name must match requested name (case-insensitive) and an agent UUID must be supplied. Only bounded, escaped public fields are cached: handle, UUID, description, karma, follower and following counts, provider-reported claim flag and UTC retrieval date. A same-handle UUID change is rejected, not silently trusted. The cache flags entries fresh for 24 hours or stale thereafter. The API provider's claimed flag does not prove identity or friendship.

**Review:** Bob's own saved Scout WHY explanation from the exact chosen discussion becomes a source-linked potential friend. To stage this candidate, the operator clicks the stage button. The server verifies the locally stored Scout record, digest-checked feed, chosen post ID and author identity again. Staging makes no network call and does not add a friend. The operator may edit relationship, display label, interests and private notes, and must supply a reason. Approval requires a cached recent matching public profile and a fresh recheck of the Scout source. The new FM1 friend record and candidate-approved decision are written in one local SQLite transaction. Rejecting creates no friend. A handle already in FM1 is not duplicated.

**Limits:** 300 cached profiles, 30 pending candidate suggestions, 200 total decisions, 8 visible cards per group. Full source links and all remote profile text are treated as untrusted. No background checks, new agent tools, messages, follows, votes, posts, auto-approval, auto-scouting or publisher/recall changes.

**Profile API evidence:** https://hivebook.wiki/wiki/moltbook-api-agent-profile and https://github.com/giordano-demarzo/moltbook-api-crawler document GET /api/v1/agents/profile?name=... . Moltbook's https://www.moltbook.com/developers page describes a DIFFERENT identity-token verification feature; it is not used here. This public endpoint has not yet been live-tested from OpenClawLab. A 401/403 error will explain that authentication is required instead of silently attempting private keys. If necessary, a separately reviewed read-only credentials adapter would be FM2.1.

## Installation

Run bobctl update in WSL OpenClawLab, verify v0.7.4-fm1-friends1 → v0.7.4-fm2-discovery1, and type UPDATE. Three files are installed: bob_friend_discovery.py, bob-activity-manager and navigation_shell.py. Activity Manager restarts. Existing updater code rollback and verified private DB backup remain in place. Two new additive SQLite tables are created only on page access: bob_friend_profile_cache and bob_friend_candidates.

## Operator acceptance

1. Open Moltbook → Discover. Look up a known Moltbook agent. Check the retrieved timestamp, API-reported fields and cautious claimed-state wording. Report a public-profile authorization error if present; do not expose or paste a private key.
2. Stage a saved Scout-authored candidate under Bob's suggested agents. It must NOT appear yet in Friends.
3. Look up that candidate's handle, then approve it with edited notes/interests and an explicit reason. It should appear in FM1 Friends with original source run and post ID.
4. Reject a different candidate and confirm no friend was added.
5. Check prior FM1, Memory, Recall, Scout and publishing operations. No outbound Moltbook action may be initiated by any review.

Future FM3: separately opt-in friend-focused scouting and recommendation, with capped reads and distinct permissions for any external interaction.
