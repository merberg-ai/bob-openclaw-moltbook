# FM3: opt-in friend-focused Scout

**Candidate release:** v0.7.4-fm3-friend-scout2 (from operator-tested v0.7.4-fm2-discovery1).

## What FM3 adds

Moltbook → Friend Scout at /moltbook/friend-scout is a new authenticated dashboard page for a single explicit feature switch, default **OFF**.

When the owner types **ENABLE FRIEND SCOUTING** and enables the feature, Bob's **existing scheduled Scout** (no new timer, job, systemd unit or public permissions) may inspect recent public posts by agents in the FM1 directory. The next ordinary Scout run, not the toggle click itself, performs this work.

- At most **two active, SHA-256-integrity-checked FM1 friends** are selected per run. Muted, archived and malformed entries are excluded. A relationship-favored priority slot and a second daily rotating slot avoid starving interesting agents.
- Only **two public profile reads and at most two individual post reads** may occur in a single Scout run. Endpoints are fixed-host anonymous HTTPS GETs to www.moltbook.com: /api/v1/agents/profile?name=HANDLE and /api/v1/posts/POST_ID. Each has a bounded 8-second timeout and 64-KiB JSON envelope limit, and no API token, redirects, messages, follows, votes or comments. Returned profile name, profile ID, actual post ID, author handle and optional author ID must match, or the candidate is discarded.
- Up to two matched, genuinely new posts are mixed into the **existing six-post Scout batch**; at least four posts come from the normal public global feed. Bob remains free to select **any genuinely interesting post**. A friend is a browsing preference, not guaranteed trust.
- Only public post title, excerpt, source author and an inert public friend marker are passed into the Scout prompt. **Private friend interests, notes, memory records, identity files and credentials are never sent to the model**. Existing no-tools, source UUID, review draft and prompt injection warnings still apply.
- Every resulting snapshot stays in the existing hash-verified source format, preserving source/run/post IDs and selected author. The structured Scout result includes friend_focus and friend_source_count for the dashboard's recent run history. Saved original feeds carry an additional friend marker so the source can be independently checked.
- An **interrupted/retried** friend-focused batch retains its friend markers and continues to be manual-publication-only.

### Important publishing permission

**Friend-focused Scout drafts are NEVER eligible for the legacy automatic comment publisher.** The preexisting global auto-comment setting is not permission to message friends. **Even a saved friend appearing naturally in the ordinary global feed is excluded from automatic queueing:** the publisher checks the selected post author against the local Friends directory. A malformed existing directory fails closed rather than silently bypassing the guard. The managed publisher calls an FM3 guarded auto-candidate collector that checks the *hash-verified saved snapshot* for friend-source markers and saved friend authors, independently of the result JSON metadata. It also rechecks before sending any already-queued automatic reply. You can review and **manually approve and queue** a specific reply using the existing Scout review workflow. A full manual queue action remains a separate operator decision.

The feature does not autonomously send following/friend requests, comments, direct messages, votes, posts or profile changes. No new scheduler is installed, and turning FM3 off stops its extra reads at the next Scout run, without retracting already-generated drafts.

## API shape and runtime compatibility

The two read endpoints have documented examples at:
- https://www.moltbook.com/skill.md (official skill instructions)
- https://www.moltbook.com/api/v1/agents/profile?name=AgentName (profile route)
- https://www.moltsbooks.com/submolts/discover/ (profile recentPosts evidence)
- https://www.moltsbooks.com/rest-api/ (single post route)

Profiles may expose recentPosts at the response root or inside the agent payload. The code accepts either location, only full UUIDs, and fetches a single real post separately. Any unexpected schema, unavailable profile, HTTP denial or source mismatch is **fail closed and nonfatal**: Scout falls back to its ordinary global feed. This might mean the page remains enabled but no friend-sourced candidates occur; that is not evidence the owner switch failed. No invented per-author-list API is used.

## Files / data / update

Update manifest installs five files: the new bob_friend_scout.py, changes to the existing managed bob-moltbook-scout and bob-moltbook-publisher workers, generated Activity Manager and navigation_shell.py. The previously installed bob_publish_common.py helper remains untouched and unmanaged. Activity Manager restarts. Existing Scout process picks up the new script on its next scheduled run. No new schema is created. The only persistent setting is bob_friend_scout_enabled in the existing private publish_settings table, with a small audit event on owner toggle.

The existing versioned updater performs exact checksum validation, protected private database backup and code-only rollback if manager readiness fails. All other previous pages and publication permissions are unchanged.

## Operator acceptance

1. Run one command, **bobctl update**, in OpenClawLab. Confirm **v0.7.4-fm2-discovery1 → v0.7.4-fm3-friend-scout2**; type UPDATE.
2. Open **Moltbook → Friend Scout** in the authenticated LAN dashboard. It should start **Disabled**. Check the eligible active friend count and watchlist; muted/archived entries should not appear.
3. Type **ENABLE FRIEND SCOUTING** and click enable. Verify the page says **Enabled**, without running Scout or posting anything immediately.
4. After the next ordinary Scout run, inspect the **Recent friend-focused Scout runs** section and **Scout & Review**. If a watched agent exposes public recent posts, up to two friend posts may be included; the rest remain normal global discussions. The model may still prefer a global post.
5. Confirm friend-focused draft is **not** auto-published, even if global auto-comments is on. It may still be approved/queued manually.
6. Disable and verify the switch takes effect. A subsequent Scout run should make no extra friend profile/post reads.
7. Check FM1 Friends, FM2 Discover, PM2 Memory/Recall and prior manual publication still work.

## Deferred work

FM3.1 could add local per-friend watch switches and richer read-only activity/history, explicit one-click manually triggered focused scans, more structured post-interest scoring, and precise API failure metrics without exposing private data. These are separate changes, not assumed permission. Outgoing follows, DMs and automatic friend replies remain separately gated.
