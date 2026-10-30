# OC0 + OC1: source-grounded "Bob right now" Overview

**Release:** `v0.7.6-oc01-activity1` from operator-accepted `v0.7.5-fm32d-focus1`.  
**Status:** CI/release candidate; **not installed until operator runs `bobctl update` and confirms**.  
**Files installed:** `bob_operations_diagnostics.py` (new, read-only) and `bob_overview.py` (existing). **No manager/router, auth, publication, systemd service/timer, Gateway, Ollama or DB schema changes.** Existing Activity Manager restart only.

## What it does

A responsive **Bob right now** card appears directly **under Daily activity budgets** on Overview. Four compact lanes describe:
- Scout: confirmed recent reading/thinking, recent failed checkpoint, paused/disabled timer or waiting/unknown.
- Publisher: six queued manual comments, earliest policy-permitted slot, timer state and last confirmed worker checkpoint. If no queued auto comments, that means no auto job is queued; it does not prove why Scout did not choose one.
- Original posts: *manual* request/draft/approval/publication workflow, generation requests, owner-action waits, and pending original-publication queue. A daily cap of 4 does **not** schedule four original posts.
- Gateway/Ollama: basic readiness from existing local service/port/model probe, never inferred actual agent thought.

One stable read-only `/api/dashboard/overview` snapshot includes a deterministic `operations` object with evidence categories, sanitized reason codes, source timestamp, actual systemd next trigger only when available, and links to existing `/logs`, `/system/status`, `/originals` or queue management. Existing auto-refresh every 15s updates text safely without DOM HTML injection.

**Telemetry truth:** a "thinking/reading" pulse needs a fresh worker checkpoint no more than six minutes old; an old active checkpoint becomes unknown/waiting, not permanent activity. A listening Gateway port or Ollama model list never proves that Bob is currently using the model. “Earliest policy-permitted” remains separate from **next systemd timer trigger** and explicitly says **not scheduled**. A known inactive/failed timer is treated as blocked; an unobserved timer never becomes an invented schedule. If DB or service evidence is missing, show unknown.

## Security and operational limits

`bob_operations_diagnostics.py` reads the existing snapshot and only two known systemd user timers through exact argument lists:
- `systemctl --user show bob-moltbook-scout.timer --property=NextElapseUSecRealtime --value`
- `systemctl --user show bob-moltbook-publisher.timer --property=NextElapseUSecRealtime --value`

Bounded timeout (1.5s per query), strict sanitized timestamp text, no shell, credentials, private prompts, raw logs, provider calls, author-controlled paths or command input. If systemd does not report a valid trigger, show no next-run claim. The diagnostic engine never mutates settings or queues, starts workers, retriggers jobs or sends network posts. All existing manual queue prioritization, per-friend rules, CSRF/auth, publishing safety checks, and PM/FM features remain in place.

## Test/acceptance

Synthetic `tests/test_oc01_operations.py` covers exact user screenshot context (**2/10 comments, 0/6 auto, 0/4 originals, six manual queued**), verified vs stale active checkpoints, inactive timers, global pause, no auto candidates inferred, manual original workflow, missing queue data, dependency readiness, strict systemd allowlist, HTML injection prevention and safe 15-second refresh. Full repository test suite must pass before merge.

After candidate CI is green and PR merged:
1. Run **`bobctl update`** inside OpenClawLab. Confirm `v0.7.5-fm32d-focus1` → `v0.7.6-oc01-activity1`, two changed modules and Activity Manager restart; type `UPDATE`.
2. On your phone/laptop, open the existing LAN **Overview**. Check the new **Bob right now** card immediately below gauges and its Scout, Comment publisher, Original posts and Gateway + Ollama lanes. Refresh once; page still auto-refreshes.
3. Check that inactive/pending items say **waiting**, **paused**, **blocked**, **idle**, or **unknown** with a reason, rather than a fake active spinner. Confirm the “Earliest policy-permitted” label is **not scheduled**, and click one **Inspect evidence** link.
4. Report actual status values from the new card if you want a precise root-cause investigation of the six queued manual comments. The earlier screenshot alone cannot establish the live blocker.

**Next:** OC2 Automation page (read-only complete registry first, then strict controls reusing existing guarded backend); OC3 sanitized Console; OC4 why-no-activity investigator with durable skip reasons. **FM4 and FM5 remain paused.**
