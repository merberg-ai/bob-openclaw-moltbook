# v0.7.2 compact Scout and Activity (first UI polish)

**Status (October 29, 2026):** [PR #8](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/8) passed GitHub offline checks and merged to `main`. Version `v0.7.2-compact1` is available to `bobctl update` but **not yet verified installed on the operator's host**. It follows operator-verified `v0.7.2-queues2`.

## Scout & review

The default `/` page now shows a **short, eight-item review queue**, initially filtered to **Pending** and **Active**. The count chips display pending, approved, rejected, validation/repair and archived totals. Simple server-side status, visibility and search filters and previous/next pagination avoid mobile endless scrolling.

Each card shows title, author, brief selection reason, **two distinct review and publication states**, and a collapsed draft. Eligible cards retain the same per-item Approve/Reject/Reset controls and original hidden CSRF and approval digest values. An already approved and **not already queued** comment retains its separate Queue action, which only creates the existing rate-limited publishing intent. Outstanding verification challenges retain their existing POST route. Controls to opt in/out of autonomous comments remain under a collapsible setting with the same explicit enable phrase and existing safety limits.

**Full unabridged reports** are still available on `/scout/full`, including the external excerpt and legacy report section. All existing Scout approvals and earlier historical links remain on disk. The Manage Queues **Open full item** link is updated to `/scout/full#run-...` so pagination does not break deep links.

## Published Activity

The default `/activity` page now displays one area at a time, with tabs/counts for **Comments, Original Posts, Incoming Replies and Event Log**. Each category shows up to eight records per page, a compact summary, collapsed content and section-scoped search/status/visibility filters where meaningful. Recent incoming replies are read with an explicit bounded limit, and events also have a bounded viewing window. **The database retains all records**. Complete historical rendering is still available on `/activity/full`.

Publication labeling remains cautious: a comment's API acknowledgement is **not** evidence of independent public visibility; uncertain/ID-unconfirmed states are not silently retried. Neither the new activity renderer nor any tab triggers a network post.

## Release and safety

`v0.7.2-compact1` installs exactly three files:

- `bob_dashboard_compact.py`: new GET-only pages.
- `bob_dashboard_manage.py`: full-report deep link correction only.
- `bob-activity-manager`: precise GET route integration built from the current pinned v0.7.2 manager.

The updater performs its normal backup and authenticated health checks, restarting **only Activity Manager** after approved installation. The response body and all draft content remain escaped. POST methods for reviews, approvals, challenge answers, auto settings, original posts and bulk actions remain **byte-for-byte AST-equivalent** to the currently reviewed manager.

One targeted synthetic test file covers pagination, pending auto-queued reviews, archive visibility, unsafe text escaping, and unchanged POST control logic. No live database, credential or Moltbook calls are involved in CI.

## Not included

No delete/Trash operation, saved filter presets, scheduled posting changes, expanded original-post authoring, or changes to Moltbook workers. Those remain possible later enhancements, not prerequisites for replacing the endless-scroll layout.
