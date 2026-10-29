# v0.7.2 Scout action redirect fix

**Status (October 29, 2026):** [PR #12](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/12) passed GitHub offline CI and merged to canonical `main`. Release `v0.7.2-redirects1` is **ready for the operator to install** from verified `v0.7.2-overview2`; it has not yet been confirmed installed.

## Observed regression

After the `/` route became **Overview** and Scout moved to `/scout`, three old POST success redirects still pointed to `/`:

- Individual **Approve / Reject / Return to pending** pointed to `/#run-...`.
- **Queue approved comment / Submit verification once** pointed to `/`.
- **Enable / Disable autonomous comments** pointed to `/`.

This was a navigation defect, **not a failure of the review or publisher logic**. The operator observed it after a successful Overview update.

## Correction

The compact Scout page includes a hidden `return_to` built exclusively from its validated filter state, visibility, search and page number. On successful POST, the handler validates that this is an allowed local Scout route, carries forward the bounded query values, and returns HTTP 303 to **the same Scout page and filters**, adding a safe `#run-ID` anchor for single items.

The **full legacy Scout report** injects `/scout/full` into its own forms, so actions there return to the full report and selected run instead of Overview. If a form has no `return_to` (for example, an old browser tab), the server defaults to `/scout`, never Overview.

Server-side redirect validation allows only `/scout` and `/scout/full` and rejects absolute URLs, protocol-relative URLs, fragments, unrelated paths, unsafe/duplicated filter fields and invalid item IDs. Validation happens **before any action mutates the database**.

## Audit of other dashboard actions

| Section/action | Verified destination |
| --- | --- |
| Scout approve/reject/reset | Same Scout page with current filters; `#run-ID` |
| Scout queue/verification | Same Scout page with current filters; `#run-ID` |
| Scout autonomous enable/disable | Same Scout page with current filters |
| Full historical Scout actions | `/scout/full` (same section) |
| Original posts: requests, edits, approvals, publication/verification | `/originals` (already correct) |
| Manage Queues bulk changes | `/manage` with current filters/page (already correct) |
| Activity Limits save | `/settings/activity-limits` (already correct) |
| Password rotation | Existing explicit sign-in-again response, **not** an unrelated overview redirect |
| Error-page Return link | Scoped to Scout, Originals, Manage or Settings as appropriate |

This change does **not** modify worker code, posting limits, approval validation, original-post permissions, posting timers, database schema or saved records. It changes only Scout form navigation and the error-page link.

## Release

Manifest `v0.7.2-redirects1` lists three live files: `bob_dashboard_return.py`, `bob_dashboard_compact.py`, and the exact derived `bob-activity-manager`. The guarded `bobctl update` handles backup, atomic install, Activity Manager restart, health verification and rollback.

Focused offline tests cover each Scout route, malicious/open redirects, filter preservation, legacy history, section-scoped errors, and unchanged sensitive handlers. No live posting tests are required.

**Acceptance:** install the release normally, then use one normal Scout Approve/Reject/Reset, check that the browser remains on `/scout` with its filters, and check `/scout/full` actions return to that view. Avoid using a real Publish or Auto-enable action solely to test navigation, because those change actual publication behavior.
