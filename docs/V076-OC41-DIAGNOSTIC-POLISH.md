# OC4.1: Why No Activity? Diagnostic Polish

**Release candidate:** `v0.7.6-oc41-polish1` from last operator-accepted `v0.7.6-oc4-investigator1`.  
**Status:** offline CI and live operator acceptance required. Repo merge does not install on the OMEN.  
**Installed files:** `bob_inactivity.py`, `bob_operations_diagnostics.py`. Activity Manager restart only. **No new manager route, DB schema, new listener, automation, timer mutation, scheduler or publication permission.**

## Why this increment

User confirmed OC4 works on LAN but its screenshot exposed: "Time unavailable" on aggregate/policy findings; 11 approved and 9 rejected historical auto blocks shown as though currently actionable; and "Next systemd publisher trigger: Not reported" despite otherwise functioning publisher. Actual screenshot also contained a successfully API-acknowledged comment and a documented rate/budget skip, so none of these alone established a publisher outage.

## Improvements

- **History instead of today:** automatic-comment section explicitly says counts come from up to the **150 most recently updated jobs**, shows UTC earliest/latest update dates in that bounded sample, and reports last matching historical block time per approved/rejected/missing-decision classification. Unknown timestamps are labeled **Policy / historical summary**, not disguised as events.
- **Owner-approved does not mean ready:** still distinguishes approved/rejected/mismatched review blocks using saved decision digest, but additionally verifies a *bounded subset of up to 25 approved never-sent jobs* against the existing **exact** read-only Scout source validator (`manual_recovery_allowed`). Displays "N of M inspected verified" separately from the historical approved count; at most three canonical run-ID links open the existing Scout review card, not an immediate publication action. Old or missing source checks fail closed; release does **not** auto-queue any job. Note: an approved old run may still fail age/target/duplicate checks later. An owner must explicitly queue publishing via the existing protected handler.
- **Last activity snapshot:** one section for last Scout worker checkpoint (not a proof of completed session), last metadata-only publisher skip/evaluation, last recorded send attempt, latest API-acknowledged comment (not independent public-visibility proof), next actual systemd trigger and earliest policy-permitted time (not the same thing). Unknown fields remain labeled unknown.
- **Timer fallback:** the two fixed allowlisted systemd user timers first use `NextElapseUSecRealtime`; only if it is missing, read their matching `systemctl --user list-timers --all --no-pager --output=json <fixed unit>` metadata. Parse an exact matching timer entry and only a plausible systemd-reported time. No shell, arbitrary unit, user command, monotonic-to-clock prediction or timer writes. When both read paths are silent, show **Not reported by systemd; check Automation / timer state** rather than promise the next run.

## Safeguards

All evidence stays on authenticated LAN. SQLite is fixed and read-only with bounded rows; no prompts, raw post/comment text, session transcripts, tokens or error details displayed. Existing publisher queue and original-post owner approvals, friend-targeting exclusions, cooldowns, stale selection claims and no-retry-on-uncertainty stay unchanged. Verified handoff counts are **not** proof a publication will succeed.

Synthetic `tests/test_oc41_diagnostic_polish.py` covers valid/invalid systemd fallback, exact-unit selection, bad JSON/injection, bounded handoff verified vs unverified/unsafe job, real history date labels and UI source links. The entire old tests suite must remain green.

## Operator smoke acceptance

1. Run `bobctl update` in OpenClawLab; confirm `v0.7.6-oc4-investigator1` → `v0.7.6-oc41-polish1`, type `UPDATE`.
2. On LAN open **Why no activity?**. Look for the Last activity & timing block, historical UTC range on Automatic comments, dated blocked-review findings, and the separate **verified handoff subset**.
3. If available, check a verified manual-review link opens Scout; **do not click the actual manual Publish button** just to test.
4. Check that **Next systemd publisher trigger** reports a systemd-provided time or clearly reports unavailable; policy-eligible timestamp remains distinct.
5. Existing Overview, Automation, Console and normal queue protections should remain unchanged. No extra command marathon.

**Next:** After OC4.1 acceptance, Operations Center OC0–OC4.1 is closed as scoped. Separate pending MD1 **Moltbook Experience Digest** in TODO.md, future CH1 Direct Bob Chat, and paused FM4/FM5 remain independent operator choices.
