# FM4.1: Bob's Private Social Memory Timeline

**Candidate:** `v0.7.7-fm41-social1`, upgrading from operator-accepted `v0.7.6-oc41-polish1`. **Not installed until the owner runs `bobctl update` and accepts the result.**

## What ships

A new **Moltbook → Social Memory** page in the authenticated, private-LAN Activity Manager at `/moltbook/social-memory`. The dashboard uses the existing navigation and supports mobile screens. It has:

- A **12-per-page, searchable saved-agent directory** using existing integrity-checked FM1 records; muted and archived agents remain available for historical viewing. Selection stays private and is not a platform follow or mutual friendship.
- A **newest-first, 25-event maximum per-agent timeline** built on existing recorded sources; nothing is copied into a new authoritative memory table:
  - **Owner label:** sealed FM1 directory status and relationship, but **never** free-text private FM1 interests or notes.
  - **Observed selection:** existing saved Scout chosen public post + Bob's WHY, rechecked against the stored feed digest and matching original post ID and author. This is not proof of sending.
  - **Reviewed interest:** FM3.2a staged/reviewed WHY, labeled pending versus owner-reviewed with sealed row and original source validation.
  - **Tentative model interpretation:** FM3.2c local Ollama proposal, with uncertainty and owner-review status, never asserted as an actual fact or long-term PM2 memory.
  - **Manual focused observation:** FM3.2d sealed public profile/post snapshot and its optional source-tied tentative local reaction. Saved observation does not imply a live profile, mutual contact or external interaction.
  - **Confirmed publication state:** an API-acknowledged comment shown *only* when the original Scout source, chosen post ID, approval digest and the saved publisher's `published` plus comment-ID fields all match. This does **not** prove the other agent replied.
- Entries label **Observed evidence**, **Tentative**, **Owner reviewed**, or **Owner label**, plus UTC time and saved source type. Missing or altered original Scout sources cause interpretation text to be withheld, rather than claiming evidence still exists.
- The owner can view existing friend edits and existing Friend Scout evidence, but the timeline itself has **no forms to publish, memory-write, follow, DM, vote, or change settings**.

The page is intentionally a first **read-only foundation**. FM4.2 will propose revisable per-agent impressions and explicit owner corrections. FM4.3 can add bounded opted-in recall for Bob's later social choices and, with separately designed authorization, MD1/CH1 Gateway chat. No existing `SOUL.md`, PM2 curated memory, FM1 operator note, Moltbook credential, or Scout prioritization is changed.

## Privacy / integrity / boundaries

All data are read locally from a **read-only SQLite connection** and fixed, bounded saved Scout snapshot paths; no background task, HTTP fetch, Ollama model request, public write or DB schema migration. Per-agent history caps: last 80 Scout files inspected, 60 rows per related table, 20 manual-focus rows, 25 displayed events, 300 sealed directory entries with 12 visible per page.

Untrusted public post titles and Bob-generated interpretations are treated as *data*, HTML-escaped server-side, and never presented as instructions. The new route uses the Activity Manager's existing authentication, Host/Origin and content-security policy. The pinned builder adds only an authenticated GET branch and one navigation item: **all POST, CSRF, existing publication decisions and other auth/protection handlers remain AST-identical.**

There is no platform following here. **Actual Moltbook follows/unfollows remain planned in FM5.2**, with independently verified API, owner-selected permissions, per-agent constraints, quotas and audit. The personal label "friend" is not evidence of a mutual relation.

## Tests and installation

New `tests/test_fm41_social_memory.py` uses temporary SQLite and synthetic sealed source snapshots to check multi-type histories, source corruption/missing data, friend/proposal tampering, private-note leakage, search isolation and empty state, untrusted HTML escaping, no write route or new auth authority, and unchanged protected manager POST methods. The complete GitHub CI suite must pass before merge.

Installed files through standard backed-up `bobctl update`:
1. New `bob_social_memory.py`.
2. Pinned generated `bob-activity-manager` for authenticated route.
3. Pinned generated `navigation_shell.py` for the new menu item.

Only Activity Manager restarts. No new timers, network ports or Gateway exposure.

**Quick owner acceptance:** After green CI/merge, run `bobctl update`, confirm `v0.7.6-oc41-polish1` → `v0.7.7-fm41-social1` and type `UPDATE`. On the authenticated LAN, open **Moltbook → Social Memory**, choose a saved agent, and compare one observed Scout WHY or reviewed interest with the existing Friend Scout page. Verify timestamps and labels; check that an agent without saved observations shows only its local directory entry. No need to trigger Scout, make a new friend or publish a comment.

**Next when FM4.1 is accepted:** FM4.2 revisable social impressions/owner corrections, followed by FM4.3 explicitly opted-in social recall. Separately planned MD1 Moltbook Experience Digest remains unimplemented; FM5 independence and public follows are not authorized by this phase.
