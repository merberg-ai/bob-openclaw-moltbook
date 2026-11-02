# OC2: Compact Automation Center

**Candidate release:** `v0.7.6-oc2-automation1` from operator-accepted `v0.7.6-oc01-activity1`. **Not installed on the OMEN until operator runs and accepts `bobctl update`.**

## What changes

- New authenticated **Automation** destination on the existing LAN Activity Manager (port 18790), using the same responsive navigation.
- A small, categorized registry (Posting, Discovery, System) of **actual** automation, one-shot workers, opt-in decisions and manual jobs. Rows show current effective state, whether scheduled or owner-triggered, with expandable last recorded job/checkpoint, next *actual systemd timer trigger* if available, and an evidence link. No page scroll full of repeated status prose.
- Two existing settings can be changed from this page using **their original, authenticated CSRF- and Origin-protected POST paths**, not newly invented side-effect handlers:
  - **Automatic comments**: `/autopost/enable` (typed `ENABLE AUTO`) / `/autopost/disable` (disabling cancels queued *automatic* comments only). Existing manual-priority, global-pause, auto-after-enable, friend exclusion, owner-decision and final publisher guards remain intact.
  - **Friend-focused Scout**: `/moltbook/friend-scout` with exact legacy four-field form, expected-state compare-and-swap and `ENABLE FRIEND SCOUTING` confirmation to enable; default-OFF and per-friend pause still apply.
- When either toggle is changed, the existing handler redirects to its usual relevant page. Reopening Automation reflects the exact shared SQLite setting; no duplicate toggle state or desynchronized settings table.
- Scout and Publisher systemd timers are **observed read-only**, not toggled by a LAN page. Reply polling shares the publisher timer. Original drafting, manual public friend inspection and local Ollama interest synthesis are accurately labeled **manual/on-demand**, not automated. Gateway/Ollama are status-only. No automatic original-post schedule has been added.

### Overview compactness (owner feedback)

The **Bob right now** card added in OC1 is shorter on mobile: brief headline, small four-lane status grid, smaller spacing/type, and collapsed **Why this status? / Why / evidence** sections for longer reasons and source links. It still displays all the original read-only reasons and source provenance, accessible on expansion and refreshed by the same 15-second Overview API polling. A pulse requires recent actual worker evidence, and reduced-motion accessibility remains intact.

## Security boundaries

The build derives from accepted FM3.2d Activity Manager using **one pinned manager-builder script**. Existing `Handler.do_POST`, `_handle_publication`, `_save_friend_scout`, authentication, CSRF, Origin and Host handling are AST-identical. Only a new authenticated GET branch for `/automation`, a pure UI module import, and one navigation link were added.

Automation reads bounded local SQLite rows (read-only mode) and existing OC0 service/worker observations. It shows only job states, timestamps, setting booleans, and sanitized next triggers; it does not show stored posts, prompts, notes, API keys, OpenClaw session text or raw journal output. All content is HTML escaped. No user-provided command/URL, shell, new host listener, systemd privilege, database schema migration, automatic publication or agent tool permission was added.

**Files installed by normal updater:** `bob_automation_center.py` (new), `bob_overview.py` (compact view), generated `bob-activity-manager`, generated `navigation_shell.py`. Restart Activity Manager only; prior `bobctl update` backup/rollback remains in place. No new systemd unit or timer.

## Acceptance

1. After green CI and merge: run **`bobctl update`** in OpenClawLab. Confirm `v0.7.6-oc01-activity1` → `v0.7.6-oc2-automation1`, and type `UPDATE`.
2. From your phone over the authenticated LAN, open **Overview**. The Bob right now card should be noticeably shorter, with expandable **Why** details that still work.
3. Open **Automation** in navigation. Check Posting / Discovery / System categories; expand Automatic comments and Friend-focused Scout. Confirm their states match those on the existing Scout pages, but **no need to toggle anything solely for acceptance**.
4. Check a scheduled timer's **Next systemd run** value (or *Not reported* if unavailable) and an original-post item labeled *Manual request*. Existing navigation, queued comments and manual review remain unchanged.
5. No separate command marathon: report whether the page looks right and whether status/current settings match.

## Tests and handoff

`tests/test_oc2_automation_center.py`: synthetic SQLite settings/status; missing/corrupt state suppresses controls; exact enable/disable actions and typed confirmation; no mutation; mode and timer truth; safety-compatible global pause; HTML escaping; mobile breakpoints; compact Overview collapsed details; and exact protected Handler POST/Host/Origin/CSRF AST equivalence to prior release.

**Next:** OC3 sanitized terminal-style read-only Console (reuse `/logs` classification, not raw shell) and OC4 “Why no activity?” investigator with recorded skip reasons. **FM4 and FM5 remain paused**.
