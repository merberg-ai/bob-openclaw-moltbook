# OC4: Why No Activity? Evidence-Based Investigator

**Candidate:** `v0.7.6-oc4-investigator1` from `v0.7.6-pubfix-manual1`. The publication fix has been merged but has **not been operator-confirmed installed** in this conversation. The OC4 release chain requires it: ensure `bobctl update` installs the publication fix first before attempting OC4. GitHub merges do not update the OMEN. **OC4 itself remains a candidate until CI, merge and live owner acceptance.**

## Scope

New authenticated **Why no activity?** navigation route `/investigate`, also linked from the compact **Bob right now** Overview card. It builds a one-view, deterministic explanation of:

- **Queued manual comments:** how many jobs, recorded publisher skip reasons, whether paused, timer inactive, waiting for rate/budget eligibility, or simply a queued worker whose cause is unconfirmed.
- **Automatic comments:** enabled vs disabled; zero queued is NOT proof of Scout failure. Previously owner-reviewed automatic drafts are categorized by matching saved owner decision **approved**, **rejected**, or missing/mismatched. Approved drafts stranded in a prior never-sent automatic job may be recoverable only via the publication fix's **separate explicit manual queue action** on Scout; this page **never queues** anything.
- **Original posts:** actual attempts, requests/drafts/approvals, manual workflow and absence of autonomous original authoring. Zero out of a daily cap is normal until a draft/request is intentionally made.
- **Scout:** observed worker/timer state, last verified checkpoint vs missing evidence. An observed Scout run, idea, or comment draft does not establish a published interaction.

A compact **Publication timing** summary distinguishes last recorded send attempt, last API-acknowledged publication (not independent evidence of public visibility), next actual systemd trigger *if known* and earliest policy-eligible time (explicitly **not scheduled**). When data are missing, the page reports **unconfirmed**, not an invented cause or guessed schedule. Explanations link to the existing **Console, Logs, Scout, Original Posts, Automation, and Manage Queues** views.

## New safe skip telemetry

A small, metadata-only `publisher_skip` event is recorded inside the existing `publish_events` table for known classes: no queued work, automatic mode disabled, rate/budget hold, global pause, preflight failure, changed/manual review decision, friend-targeted auto block, integrity, expired draft, duplicate target, or an invalidated stale send claim.

- **No new table** and no content, credentials, model prompts, reply body or arbitrary exception string is written.
- Event details contain only `code=ALLOWLISTED_CODE` and, if valid, `run=YYYYMMDDTHHMMSSZ`. Code values are fixed constants, not sourced from third-party posts.
- Identical consecutive code/run events are **throttled for 30 minutes**, preventing a no-queue timer from logging the same state every minute. The investigator reads at most 80 such events; only validated allowlisted codes from the past week are considered. Display emphasizes recent (24h) skips.
- Existing publication decision logic, rate limits, network calls and retry policy **do not change**. Telemetry is written only in existing non-send branches. The full publisher test suite must remain green.

## Privacy and safety

The investigator uses bounded, **read-only** SQLite queries (up to 150 recent publication jobs, 80 recent skip events) with strict schema fields and checks against known decision states/digests. It does not display private comment text, post URLs, credentials, full draft or arbitrary errors. Stored raw `last_error` is used **only** for comparisons to specific known reason strings; it is never displayed or exported. Failed/missing database becomes a distinct unknown state. Output is escaped on the server and is a GET-only page, with no JavaScript, new API credentials, terminal commands, automated publishing, systemd mutations or new port.

The manager is generated from the exact accepted publication-fix manager builder; only an authenticated GET route and navigation link are added. All existing login/Host/Origin/CSRF and POST/publication handlers remain AST-equivalent. Activity Manager restarts through the existing guarded updater; no Gateway/Ollama/timer changes.

## Tests and release

Synthetic `tests/test_oc4_inactivity.py` covers approved/rejected/mismatched decision distinctions, safe attempts/unknown/sending behavior, lack of fabricated original-post schedules, rate vs systemd trigger, pause/timer uncertainty, sanitized event-code validation, XSS escaping, malformed/missing DB, 30-minute skip throttling, no private content and preserved authenticated POST handlers. Full repository CI must pass before merge.

Updater managed files: new `bob_inactivity.py`, updated `bob-moltbook-publisher` (non-send diagnostic events only), updated `bob_overview.py` (one extra link), pinned generated `bob-activity-manager`, and generated navigation.

## Short operator acceptance

1. **Version chain:** First confirm `v0.7.6-pubfix-manual1` is installed and working. If not, do **not** skip the publication-fix release; OC4's updater `from` requires it.
2. After CI and merge, in OpenClawLab run `bobctl update`. Confirm `v0.7.6-pubfix-manual1` → `v0.7.6-oc4-investigator1`, type `UPDATE`.
3. On the authenticated LAN dashboard, open Overview → **Why no activity?** (or the new navigation link). Inspect four explanations and publication timing. Validate they distinguish **actual queued** from **actually sending**, and **approved/rejected** review blocks rather than labeling all warnings as outstanding approvals.
4. Compare one explanation to Console/Automation. Missing evidence should say unconfirmed and no control on this page should send, queue or retry anything. No test publication necessary.

## Next roadmap

OC0–OC4 complete after owner acceptance. Future **Moltbook Experience Digest (MD1)** is separately tracked in root `TODO.md`: make *verified* Scout/posted/reply experience available to real OpenClaw Gateway conversations, without automatic model-authored memories or unexpected public context. **CH1 Direct Bob Chat and FM4/FM5 remain independently gated**, not part of OC4.
