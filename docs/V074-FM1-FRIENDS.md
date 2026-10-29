# FM1 — Private Moltbook Friends Manager

**Candidate:** `v0.7.4-fm1-friends1` from operator-accepted `v0.7.3-pm23-recallfix1`.

## Purpose

Bob needs a useful private directory of other interesting Moltbook agents **before** gaining the ability to discover, follow, monitor or interact with accounts independently. FM1 builds a manual database and reviewable relationship history. A **Friend** relationship label in this UI is only Bob's own private classification; it is **not** a verified Moltbook mutual friendship, follow state, or account-ownership claim.

## Delivered

- New authenticated responsive dashboard **Moltbook → Friends** at `/moltbook/friends`.
- Explicit operator **Add** using a unique case-insensitive handle (2–40 characters), display label, relationship (`interesting`, `acquaintance`, `friend`), topic interests and private notes.
- **Edit with reason** preserving prior snapshots and action history; stale edit SHA-256 checks prevent overwriting another browser tab's changes. Changes never edit the account handle or provenance.
- Local **Mute / Archive / Reactivate** statuses (reversible, with version history). These statuses are for later friend-focused scouting, not real Moltbook API mute/unfollow calls. No deletion of history.
- Search by handle, label, interests or notes; status filters and 12-per-page pagination. Dark theme and mobile layout, normal POST/303 without JavaScript.
- **Agents seen in Scout** section proposes up to six distinct new authors from existing locally verified Scout runs. Each quick-add explicitly requires operator action. Server re-verifies both the exact hashed feed snapshot and that the stored chosen author equals that particular source post's author, never trusts a hidden author field. Captured author string is untrusted public metadata, **not live profile verification**. Unknown/placeholder and malformed handles are rejected. No new network request is made.
- Private SQLite additive tables `bob_friends` and `bob_friend_revisions` in the existing backed-up Activity Manager queue DB. Limit 300 entries; immutable audit snapshots and concise event IDs, never notes in event logs. Source URL, keys or API credentials are not stored.
- Fixed whitelist for specific validation errors. Database exceptions and raw third-party text are never reflected to error pages.

## Security and independence

FM1 **does not** fetch Moltbook profiles, call any Moltbook endpoint, follow/unfollow, vote, comment, send messages, schedule scouting, inject friends into model prompts, change the Memory Manager, or grant Bob publishing authority. The browser is only a private local directory. Scout and publishing workers, Gateway, Ollama, systemd timers, auth/CSRF/origin policy, personality and existing recall switches remain unchanged.

This is private **unencrypted SQLite** on the trusted LAN host, backed up by the existing updater. Avoid storing secrets and sensitive real-person details. The user-facing dashboard should remain behind its existing private LAN/VPN authentication, never public Internet without separate TLS hardening.

## Single-update operator acceptance

1. On OpenClawLab run `bobctl update`. Verify `v0.7.3-pm23-recallfix1` → `v0.7.4-fm1-friends1` with three files and only an Activity Manager restart; type `UPDATE`.
2. Open **Moltbook → Friends**. Add your friend's new Moltbook agent handle manually with an interest and relationship label. Refresh and confirm persistence.
3. Edit its notes and relationship, supplying a reason. Open **Edit / history** and verify both versions are retained.
4. Use **Mute locally**, filter for Muted and **Reactivate**. Repeat Archive/Reactivate as desired. These are purely local.
5. If existing verified Scout records include an author in the **Agents seen in Scout** list, quick-add one and check its source run/post provenance appears on its card. Duplicate add is safely rejected.
6. Confirm previous **Memory / Recall / Personality** and **Scout & Review** pages still work. None of the friend actions should trigger Moltbook activity.

## Next separately gated stages

- **FM2:** read-only Moltbook public profile lookup, strictly grounded handle/post IDs, cache age, public-interest synopsis, display verified-versus-unverified. Use only documented/observed API endpoints; no invented follow relationships. Owner review for Bob-proposed additions.
- **FM3:** explicitly opt-in friend-focused Scout prioritization, bounded visits to posts by interesting agents, relationship context with trust labels, and distinct permissions for each outgoing interaction. No autonomous follows or messages without their own explicit authorization.

This is intentionally a small local release rather than introducing a full social automation system before friend identities can be verified.
