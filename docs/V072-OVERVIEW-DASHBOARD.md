# Bob Overview dashboard: v0.7.2-overview1

**Status (October 29, 2026):** [PR #10](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/10) passed offline CI and merged to `main`. The operator confirmed `v0.7.2-overview1` installed and the new dashboard looking good. Follow-up [PR #11](https://github.com/merberg-ai/bob-openclaw-moltbook/pull/11) passed CI and merged the one-file `v0.7.2-overview2` visual cleanup, which is **available but not yet confirmed installed**.

## Navigation

The dashboard landing page at `/` becomes **Overview** (mission control). The previous default review queue remains available as **Scout & Review** at `/scout`, with its search, status filtering, eight-item pagination and all existing individual approval/rejection/queue/verification controls. The complete legacy Scout report remains `/scout/full`; Manage Queues links continue to open that full report. Published Activity, Original Posts, Manage Queues, System Status and Settings keep their existing routes.

The installed desktop sidebar and mobile menu will show **Overview** and **Scout & Review** as separate destinations.

## Live overview visuals

The new landing page uses existing local, authenticated evidence:

- Three animated-by-refresh **daily budget gauges** for comment attempts, automatic comment attempts (subset of the total), and original post attempts. Percentages represent **used budget**, not task progress. Values and policy caps come from the private `publish_settings` and recorded attempted timestamps.
- Queue and outcome cards for queued manual/automatic comments, original drafts and queued original posts, generation requests, API-acknowledged comments, independently observed original-post visibility, uncertain results, and observed incoming replies.
- Live service/dependency indicators from the existing `bob_live_status.snapshot`: Gateway, Scout, Publisher, timers, Activity Manager, local Ollama and Gateway listener. A service's running state does **not** prove posting or model generation succeeded.
- Four worker checkpoint cards for Scout, comment publisher, original generation and original publication. An animated spinner appears **only** for a recent, explicitly active stage (fetching, validating, generating, preflight, sending or verifying). Stale checkpoints become `unknown` and **never keep spinning**.
- A bounded recent-job list (six records), seven newest event kinds and timestamps, and links into the detailed Activity and System Status pages.
- Read-only local next-eligible rate-slot timestamps. These are **not promised future publishing times**: automatic authorization, timer cadence, draft validity, human approvals, global pause and Moltbook’s rules still take precedence.

The HTML is server-rendered using the current snapshot, so it remains readable without JavaScript. A small separate, same-origin JavaScript asset refreshes from authenticated `GET /api/dashboard/overview` every 15 seconds **only while the tab is visible**. It validates response shape, uses `textContent` for dynamic data, never executes content, sets a request timeout, and clearly warns when the last-known values may be stale. No POSTs, background publication triggers or polling from a hidden tab.

The UI is responsive across phone and desktop layouts. CSS animations respect `prefers-reduced-motion`. Error, idle, waiting and unobserved are visually distinct. An unavailable SQLite database yields **unavailable metrics**, not invented zero counts.

## Overview2 presentation cleanup

The operator verified `v0.7.2-overview1` installed and working, then requested a shorter home page. The follow-up **`v0.7.2-overview2`** release removes the large Mission Control header card, the duplicate row of navigation shortcuts, and the optional gauge/rate-slot/worker explanatory paragraphs. The **daily budget rings, next possible rate slots, queue/outcome totals, service and worker states, recent jobs, events, and 15-second refresh button** stay intact.

All navigation remains in the existing sidebar/mobile menu. No worker policy, rate limits, approval routes, publication semantics, telemetry schema or database records change. Only `bob_overview.py` is replaced and the Activity Manager is restarted through the guarded updater. The updated module also removes browser-side references to the deleted header elements.

**Deployment status:** The cleanup has passed GitHub CI and is merged on `main` as `v0.7.2-overview2`. Operator installation is still pending.

## Privacy and publishing guarantees

Overview uses a bounded SQLite **read-only** connection. The new endpoint and JavaScript asset are served through the existing dashboard's Host and authentication checks. No credentials, tokens, post bodies, untrusted model replies or user content are returned by the endpoint. Event entries include only bounded kind and timestamps.

**No publisher/scout/original worker binaries are changed.** No changes to operator-configured Activity Limits, auto-post permission, drafts, manual priority, duplicate protection, no-blind-retry rules or SQLite schema. Existing backend POST methods are required by the focused tests to remain AST-identical.

## Release

Manifest `v0.7.2-overview1` installs exactly four files: `bob_overview.py`, `bob_dashboard_compact.py` (Scout route move), `navigation_shell.py` (sidebar/mobile destinations), and the rebuilt `bob-activity-manager`. Only Activity Manager restarts, through the existing verified backup/health/rollback update path.

An offline synthetic acceptance suite covers actual attempt counts and budget percentages, uncertainty semantics, missing DB behavior, UTC reset semantics, escaped event content, bounded polling and unchanged POST logic.

**Operator deployment:** after merge, `bobctl update`, review four files and confirm `UPDATE`. Then open the LAN dashboard root and the new `/scout` page. No manual publisher run is needed to verify the UI.
