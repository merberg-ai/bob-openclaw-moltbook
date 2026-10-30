# Bob Operations Center: Why Is Bob Quiet? (OC0–OC4)

**Planning checkpoint:** October 30, 2026 (America/Los_Angeles).  
**Priority:** Owner-requested visibility, unified automation control, and safe diagnostic console **before** resuming Friends Manager FM4.1 / FM5.  
**Last operator-tested release:** `v0.7.5-fm32d-focus1`, final FM3 acceptance PASS.  
**Implementation status:** **ROADMAP ONLY.** No live host, service, code, configuration, database, timer, permissions, current release manifest or dashboard page changed by this planning document.  
**Principle:** First explain existing inactivity accurately; do not increase autonomous posting merely to move a gauge.

## 1. User problem and what is known

The owner shared a phone screenshot of Activity Manager **Overview**: 2/10 comment attempts today, 0/6 automatic comments, 0/4 original-post attempts, six comments queued (all manual), zero auto queue and zero original drafts/approved. The display says auto-comments enabled. Counters have seemed static for an extended period and the cause is difficult to find through different tabs. This is a **snapshot**, not a live diagnostic result.

Current source-backed facts:
- `src/lib/bob/bob_overview.py` and `bob_activity_limits.py`: gauges count *attempted sends per UTC day*, not completed actions, guaranteed public posts, or work targets. The “earliest possible next” rate-limit timestamp is **not a scheduler's next execution time**.
- `src/bin/bob-moltbook-publisher`: owner-approved manual comment queue takes priority. Auto-posting requires an eligible recent saved Scout selection and excludes friend-related, already human-reviewed, expired, duplicate or otherwise disallowed targets; auto enabled does not promise an auto candidate. A nonempty manual queue can remain pending due to timer, limits, pause, dependency, integrity or publication conditions. **Cannot identify the actual blocker from screenshot alone.**
- `src/lib/bob/bob_originals.py` and `src/bin/bob-original-worker`: original drafts are currently explicitly requested by owner and publishing requires separate explicit approval/authorization. A 0/4 attempt gauge may be entirely normal. No automatic original-post authoring schedule should be invented.
- `src/lib/bob/bob_live_status.py` / `bob_job_tracking.py`: status already has authenticated read-only service observations, recent queued jobs and four worker stage checkpoints, including stale checkpoint handling. A listening port is not proof an AI response completed.
- `src/lib/bob/bob_diagnostic_logs.py`: existing `/logs` page already collects sanitized bounded journal, SQLite jobs, event records and checkpoint evidence. Reuse as a common backend rather than creating a second unbounded log stream.
- `TODO.md`: separate CH1 Direct Bob Chat is planned but not implemented, and is **not** an assumption about this Operations Center request.

## 2. Shared observability contract (OC0): answer before control

Create one small **read-only consolidated diagnostics snapshot**, reusing existing bounded collectors and no new network ports. It should be independent from the publication permission path.

Per subsystem use a common envelope:

```json
{
  "subsystem": "publisher",
  "state": "waiting",
  "activity": "Awaiting next eligible attempt",
  "reason_code": "RATE_GAP",
  "reason_detail": "Minimum interval has not elapsed",
  "evidence_kind": "stored_job_and_policy",
  "evidence_at_utc": "source-supplied time, not guessed",
  "last_attempt_at_utc": null,
  "last_success_at_utc": null,
  "next_scheduled_at_utc": null,
  "next_policy_eligible_at_utc": null,
  "stale": false,
  "inspect_href": "/logs?service=publisher"
}
```

This is a **schema example, not real Bob state**. Only populate values supported by verified DB data, explicit configured settings, trusted checkpoint state or systemd timer observations. Omit or mark unknown where absent. Map raw failures to **allowlisted codes**; never use a model to speculate about causality.

Suggested distinct UI states:
- `active`: recent bounded verified checkpoint that is still live and matches a running process/task; label stages **reading public posts**, **thinking**, **validating**, **preflight**, **sending**, **verifying** only if directly observed.
- `waiting`: a known future dependency, timer, cooldown, worker, verification or limit gate with evidence.
- `blocked`: known policy/safety hold, paused worker, failed integrity, unavailable dependency, or required owner decision.
- `idle`: healthy, no eligible queued work, with observed timer/service health, **not** inferred from an empty budget.
- `unknown`: telemetry missing/stale, source disagreeing, or inability to prove the cause.
- `offline`: confirmed service/timer failure or dependency outage, distinct from an intentionally stopped one-shot service.

**Never conflate** “enabled”, “running”, “eligible now”, “next scheduled”, “budget remaining”, “queued”, “successful API response” and “publicly visible”. The builder should display evidence age and make status stale after a bounded period.

### Concrete diagnostic rules to implement and test

- **No automatic comments:** distinguish auto OFF; no Scout result; last Scout failed/was empty; no eligible candidate due to human review, friend protection, age or duplicate rules; auto queue empty; manual jobs prioritized; rate gap/daily cap; timer inactive; cause unobserved. Use exact safe reason codes and link the relevant evidence (no raw private drafts).
- **Manual backlog:** show oldest pending age, source-verified queued count, effective worker timer state and last recorded worker run, current policy gate, and whether oldest job was blocked. Do **not** automatically requeue or retry uncertain publications.
- **Original posts zero:** show “owner-requested only” plus outstanding draft requests / drafts / approvals / queued originals, next policy eligibility (only relevant if queued), last generation result, separate original worker/timer readiness; distinguish “not requested” from “failed”.
- **Timer vs rate eligibility:** show **next actual systemd trigger** only when reported by systemd and separately show **earliest policy-permitted attempt**; no “scheduled for” when no scheduled job exists.
- **Dependency errors:** sanitized Ollama model readiness, Gateway port/service and *actual* agent-job checkpoint; no “Bob is thinking” inferred solely from port 18789 listening or model installed.
- Retain timestamp from underlying source and its provenance. If evidence is incomplete, say “Cause not confirmed” and provide a direct filtered Logs/Status link.

## 3. Implementation roadmap (small releases, single update per phase)

### OC0: Diagnostic evidence and reason-code engine (FIRST)

- Introduce a pure, testable `bob_operations_diagnostics.py` **read-only** collector for publication and Scout states, timer/unit health, policy constraints, last attempted/completed events and evidence freshness.
- Reuse `bob_overview`, `bob_live_status`, `bob_job_tracking`, `bob_activity_limits`, and `bob_diagnostic_logs`; avoid duplicate queries and unbounded journal/SQLite scans. Check existing schema before designing new tables.
- Focus acceptance fixture on exact screenshot scenario: **2/10 comments, 0/6 auto, 0/4 originals, 6 queued manual**. All permissible explanations must be conditional and grounded; unknown when actual live blocker is absent. Test policy prioritization and empty/failed Scout.
- Preserve last known good read-only view with a conspicuous **stale** indicator if a collector fails. No new systemd mutations, auto posting or AI inference.

**Gate:** fixture says why output is *insufficient* rather than pretending a schedule or failure, and shows separate rate-limit and timer timestamps.

### OC1: Compact “Bob right now” Overview card

- Insert directly **below the daily gauges card**, matching cyber-glass dark blue palette and responsive Android sizes.
- Hero strip: current verified action/condition, colored semantic state and subtle animation **only while actually active**; status source age and “Updated” time. Avoid fake animated spinner for stale statuses.
- Short 4-stage service strip: Scout, Comment Publisher, Original Posts, Ollama/Gateway. Show one explicit human-readable reason per item, next real run if known, and direct “Why?” jump to detailed Operations/Logs filters.
- Highlight owner-blocking actions **only when applicable**: “6 comments awaiting next publisher opportunity”; “No eligible automatic draft”; “Original posts: awaiting owner draft request”. These are examples, **not claims about running Bob**.
- Auto-refresh at existing dashboard 15-second interval while visible; no continuous hammering or server-side LLM call.
- Existing budget gauges remain, but “Earliest possible next” text must explicitly say “policy eligibility, not scheduled execution.”

**Gate:** user can tell active/waiting/blocked/idle/unknown at a glance and see what evidence supports it.

### OC2: New “Automation” unified control center

- One registry of **real** automation capabilities, with service/process/timer, user toggle, last action/outcome, last run time, next *scheduled* run if the timer exposes it, last policy-block reason, and jump to detailed source page.
- Proposed initially **read-only inventory**, then gated controls added only after proving exact backend authority. Reuse the existing auto-comment switch and FM3 friend Scout global switch; their state must be synchronized across every page and any updates must call the existing protected domain validation/event handlers.
- Show Scout timer, Publisher timer, reply polling (as part of Publisher), original draft request/worker, verified public focus/interest generation, and other jobs **honestly** as automated, scheduled, manually triggered, or disabled/not implemented. A row does not imply a toggle exists or should exist.
- Optional timer enable/disable requires separate explicit permission review, a **strict allowlist** of known user-systemd unit names, minimal capability and ownership constraints, confirmation for disruptive changes, existing auth + Origin/CSRF, audit, rollback and negative tests. Never expose `systemctl` arguments, command input, gateway admin scopes or a generic task scheduler through the browser.
- Do NOT introduce an automatic original-post creation toggle without its own independent consented policy and human-review gates. The “Originals” section stays manual until explicitly designed otherwise.
- Compact mobile-first rows, category filters (“Posting”, “Discovery”, “Health”), effective configuration vs operational state, and “Run now” **not** default. Global pause must never be bypassed by an individual toggle.

**Gate:** the same controlled setting changed in either UI is reflected in both; all gating and publication safety checks survive. No conflicting hidden states.

### OC3: New “Console” with a safe diagnostic stream

- Terminal-inspired, monospace **read-only** diagnostic UI. Filters by subsystem, severity, source, time window, search/job ID; short bounded chronological view, pause scrolling, auto-scroll, copy/export **sanitized output only**. Auto refresh/polling at a modest rate; use existing collector output.
- Evidence sources: sanitized queue/event history and checkpoint states, allowlisted `journalctl --user` summaries for known units, OpenClaw Gateway service/loopback readiness, status of existing local Ollama API model availability and optional bounded model-loaded metadata. No raw tokens, prompts, reply bodies, private friend notes, OpenClaw session text, unfiltered HTTP responses, exception strings or arbitrary journal lines.
- The “console” is **not an interactive shell**; no user-entered commands, terminal interpreter, generic system API, privilege escalation, OpenClaw tool proxy or extra LAN port.
- Clearly label **information missing** and **cause not verified**. A model-response failure should not be collapsed into Gateway-down if only connection status is known.

**Gate:** operator can trace a queue entry or last Scout attempt through trusted event IDs and see enough safe context to troubleshoot, including outage conditions, without opening SSH.

### OC4: “Why no activity?” single-view investigator

- Add per-lane **Explain inactivity** action in Overview and Automation, backed by deterministic OC0 reason engine (not a new LLM reasoning prompt).
- Show ranked *verified* blockers, the last successful action and time, last attempted action and time, last skipped/blocked evaluation, next real worker trigger, next rate eligibility, human action needed if any, and direct links to filtered Logs/Manage/Originals.
- “No explanation recorded yet” is a valid, visible result; this should trigger a targeted later instrumentation improvement, not invented explanations.
- When a timer-run finds no eligible work, log a **bounded, sanitized skip-reason event** to the existing private audit store so idle days can be explained. Do this without storing full external content, model output, secrets or private prompt data.
- Optional one-click **Copy diagnostics report** with sanitized statuses, reason codes and time windows. Never include credentials, private content or a full session transcript.

**Gate:** owner can answer “Why were automatic comments 0/6?” and “Why are six manual comments queued?” from one screen with evidence and no shell, under both healthy idle and real failure fixtures.

## 4. Improvements that should NOT get mixed into first release

- **Explicitly separate project idea:** owner-approved automatic original-post **draft creation cadence**, if desired later. It must *not* automatically publish; require opt-in, generation budgets, safety screening, content quality, source limits and manual approval. Existing 0 original attempts is not a failure.
- Optional stale/quiet alerts with thresholds only after the evidence engine can distinguish healthy quiet hours from real failures; avoid notification spam.
- Additional model-performance telemetry is useful only with bounded, privacy-safe metrics; no exposure of prompts, session memory, private friend notes or untrusted raw logs.

## 5. Safety, acceptance and deployment contract

- Work on `merberg-ai/bob-openclaw-moltbook` via small feature branches, offline synthetic tests, audited GitHub PR, passing CI, then **one `bobctl update` per accepted code phase** from the latest operator-accepted installed version (currently `v0.7.5-fm32d-focus1`, unless superseded).
- **Documentation planning now creates no release.** Do not change `releases/current.json` or deploy code until an implementation phase is explicitly chosen.
- Keep existing authenticated LAN Activity Manager on port 18790; Gateway remains loopback-only; no new listener. Preserve existing Basic auth, Host/Origin/CSRF, fixed-host public reads, per-friend opt-in/pauses, owner approvals and final publisher guards.
- Avoid 14-hour manual test sequences. Synthetic comprehensive CI plus a **single short owner smoke test** for each release, with exact pass/fail and rollback.
- Real operator screenshot is the problem statement, **not proof** that current services have failed. To confirm a live cause, use existing `/system/status`, `/logs` (publisher/scout) and `/originals` without mutation.

## 6. Resume note / next chat entrypoint

> Start the **Bob Operations Center** improvements, **OC0 then OC1**. Read `docs/OPERATIONS-CENTER-ROADMAP.md`, root `TODO.md`, and `docs/FRIENDS-ROADMAP-AND-HANDOFF.md` in current `main`. Last known operator-accepted application release is `v0.7.5-fm32d-focus1`, though check any intervening release. User wants a “Bob right now” card below gauges, unified Automation section, sanitized read-only Console, and a source-grounded “Why no activity?” investigator, first addressing 2/10 comments, 0/6 automatic, 0/4 original and six manual jobs queued. Implement a small evidence-only phase with real status/skip reasons, distinguish next scheduled worker from earliest policy eligibility, preserve all publication/auth/security controls and `bobctl update`; **FM4/FM5 remain paused**.
