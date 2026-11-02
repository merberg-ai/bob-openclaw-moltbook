# Dashboard queue-management polish (v0.7.2 UI batch 1)

**Status (October 29, 2026):** [PR #6](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/6) merged into `main` after GitHub's offline acceptance passed. The reviewed dashboard candidate was first offered as `v0.7.2-queues1`, but its first live update attempt **failed and was restored to baseline**. The incident is still recorded and the owner has not installed these changes. A guarded [incident reconciliation](V072-QUEUES1-INCIDENT-RECOVERY.md) and a distinct `v0.7.2-queues1-r1` retry manifest are prepared on `main`. Publisher behavior, credentials and rate limits are unchanged.

## What is new

A dedicated **Manage queues** sidebar/mobile navigation destination, `/manage`, with compact server-rendered tabs for:

- **Scout & review:** View validated incoming scout drafts and their review/publication status. Select up to ten on the current page to approve, reject, or explicitly queue **already approved** drafts for the existing publication worker.
- **Original posts:** View generated post drafts and their state, select up to ten to approve, reject, or explicitly queue **already approved** originals. Existing edit controls, verification challenges and individual publishing remain on the Original Posts page.
- **Comment activity:** Review queued, attempted, verified, canceled, uncertain and failed comment records. Batch archive/restore only. No republishing of history or automatic retries.

Every tab offers bounded search, status filter, active/archived/all visibility filter, ten-item pages, compact content previews, and a link to the full legacy item. The user must explicitly check each selected row; no hidden all-pages selection, blind select-all, or JavaScript is required.

## Reversible archive, no erasure

Archive/restore is a soft visibility flag in an additive `dashboard_hidden(kind,item_id,hidden_at)` table. A soft-archived item is still present in the original scout file, `decisions`, `publish_jobs`, `original_posts` or reply/event history, and remains retrievable using the **Archived** filter. This does **not cancel or pause** a queued publication; it never deletes Moltbook content, local API history, or approvals.

No permanent delete/Trash operation is part of this release. Permanent destructive cleanup requires a separate design that distinguishes draft-only data from immutable audit records.

## Batch safeguards

- The UI is behind existing dashboard authentication. Bulk POST requires Host, Origin, CSRF and strict body-size checks.
- At most **10 unique selected IDs** per batch; all are checked against current database state and original draft fingerprint before any mutation.
- Approve/reject works only on eligible pending scout or draft originals, and never changes an existing decision silently.
- Bulk **Queue** requires pre-existing approval, unchanged digest, no existing outgoing job for scout replies, and explicit typed **`QUEUE N`** matching the selected count. It records an intent and **does not invoke any network worker**.
- The autonomous comment setting, the two-attempts-per-UTC-day limit, one-hour interval, original-post approval boundary, and no-automatic-retry policy remain unchanged.
- A failed batch returns an error and its database context rolls back; no partial action or silent skip.

## Release strategy

This first batch adds:

- `src/lib/bob/bob_dashboard_manage.py`: new standalone queue UI and guarded batch actions
- `scripts/build_v072_dashboard_manage_candidate.py`: derives the exact current deployed manager/nav files and integrates the new authenticated route
- `tests/test_dashboard_manage.py`: **seven focused synthetic checks**, not a full project suite

The current release manifest lists precisely these three installed files: `bob-activity-manager`, `navigation_shell.py` and `bob_dashboard_manage.py`. The build script is only a source generator. Review and CI passed; PR #6 was merged to `main`. The operator can deploy it as the **first nonempty `bobctl update`** release. Installation will restart only the Activity Manager after the usual verified SQLite backup. The existing root Scout, Original Posts and Published Activity pages remain operational for one-item detail and recovery.

## Follow-up: pending review visibility fix (queues2)

The first deployed management screen incorrectly used the outgoing publication-job state as the **review** status for Scout drafts. A draft that was still pending manual review but had an automatic `queued` comment job disappeared from the **Pending** review filter. The mobile screenshots showed a Pending filter with no matches despite pending reviews visible on the legacy page. The separate 30 archived items remained in the UI archive table.

Release `v0.7.2-queues2` corrects this without altering historical data: Scout items retain their review status and show publication status as an independent badge. Pending now includes auto-queued drafts and archived pending items when Visibility is All; the counter distinguishes pending archived items. Original draft posts are also matched by Pending. Bulk review remains allowed on valid pending drafts, but bulk Queue is refused if any existing outgoing job exists. This is a **single-module replacement**, not a change to the publisher or its rate limits.

**Status:** Prepared on fix branch; installation not yet confirmed. The operator's already archived records will remain archived until explicitly restored. The default **Active** visibility omits archives; use **All** or **Archived** to inspect them.

## Follow-up work (not included)

Bulk deletion with retain/undo policy, grouping by discussion, saved filter presets, exact cross-page selection and a distinct Archive page are deliberately deferred. Those are separate decisions, not prerequisites to fixing the scrolling problem.
