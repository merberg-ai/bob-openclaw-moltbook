# PM2.1 — Private Memory Manager foundation

**Release candidate:** `v0.7.3-pm2-memory1` from operator-tested `v0.7.3-pm1-uiqueue1`.

## What ships

A new authenticated **Bob's Mind → Memory** page at `/mind/memory`:

- Operator can **add**, **search**, **edit**, explicitly **correct**, **archive**, **exclude** and **restore** memory notes. Paging and status filters keep the UI usable on mobile and desktop.
- Each memory records category, operator-assessed confidence, optional source description, optional ordinary public HTTPS URL, UTC create/update dates, current state, revision number and tamper/stale-edit digest. All entries in this first release are explicitly **operator-entered and unverified**. No external source is fetched or treated as verified.
- Each successful operation creates a versioned private SQLite snapshot with action and reason; edit/correction requires a reason. History is visible from the entry's edit link.
- An **excluded** memory cannot be edited until restored and is not eligible for any future recall pipeline. Archived is also excluded from future recall. Both are reversible via explicit owner action; neither state silently deletes history.
- Maximum 500 memories, max 2400 characters per note, 12 results per page. All rendered text is escaped. Source links require public-looking HTTPS hostnames, reject credentials, nonstandard ports and obvious internal/numeric hosts; all clicks are ordinary user browser navigation, never server-side fetches.
- Source data never enters `SOUL.md`, `IDENTITY.md`, `AGENTS.md`, model prompts, public posts, sandbox permissions or publisher/worker logic.

## Security and data location

The module adds two idempotent tables, `bob_memories` and `bob_memory_revisions`, to the **existing private SQLite queue database** used by the Activity Manager, not to Git. It uses the existing authenticated page protection, same-origin form checks, CSRF, bounded POST parser, escaped server-rendered HTML and database transaction context. Memory operations record only record ID/action in the existing event log. The `bobctl update` updater takes its normal private SQLite backup before installing and restarts only Activity Manager.

This is **private local data, not encrypted-at-rest memory**. The existing HTTP LAN dashboard must stay on a trusted LAN/VPN or be placed behind properly configured HTTPS. Never put confidential credentials, access tokens or secrets into memory entries.

All GUI actions are manual. No agent auto-writing, external ingestion, suggested-memory acceptance, memory-based drafting or scheduled recall is authorized by this release.

## Operator acceptance

1. In OpenClawLab, run `bobctl update --check` and then `bobctl update`. Inspect that the release moves from `v0.7.3-pm1-uiqueue1` to `v0.7.3-pm2-memory1` with three application files; type `UPDATE` only after reviewing the manifest.
2. Open **Bob's Mind → Memory** from the dashboard. Add a harmless test note with category and confidence. Check that it persists after refresh and appears in the search.
3. Edit the note with a reason, then use **Correct** with a reason. Verify the history shows separate versions.
4. Exclude the note, filter for excluded items, verify editing is not offered, then restore to active. Repeat archive/restore if desired.
5. Check **Bob's Mind → Personality**, **Manage queues**, and **System status** still work. No agent restart, Moltbook publication or existing publishing setting change should occur.

## Next gated PM2 steps

- **PM2.2:** Separate **Bob-suggested memory inbox**, validated provenance linked to existing real source IDs, owner review/approve/reject/correct, deduplication and retention/export options. No writing directly to accepted memories without review.
- **PM2.3:** Bounded *read-only* agent recall using approved active entries only, marked low-trust context and never system/tool instructions; explicit owner opt-in, prompt-injection defenses and full regression tests.
- **PM2 completion gate:** Install and verify memory operations, revision/search/review and policy isolation on the real host **before** FM1 Friends Manager.

A GitHub merge does not install a release or migrate the live SQLite database. The additive tables first appear when the new Memory page is visited or the first entry is saved.
