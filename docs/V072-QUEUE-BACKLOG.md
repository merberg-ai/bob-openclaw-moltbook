# v0.7.2 queue backlog: facts, diagnosis and manual-first correction

The operator reports that a new original-thought draft generated successfully and a **read-only audit found four published comments visible on Moltbook**. A backlog of queued comment jobs remains. System Status displayed the publisher as waiting, which is consistent with local queue policies but does not by itself establish the reason for every job.

## Reviewed publisher behavior

- The source currently allows **two outgoing comment attempts per UTC day** and at least one hour between attempts, shared by manually approved and automatic comments. These are safety limits and should not be increased without explicit operator approval.
- The deployed publisher selects the **oldest queued job of either mode**. If its auto mode is disabled, that oldest queued auto job is held and can prevent newer manual approvals from advancing. The result is a form of manual-queue starvation.
- Selecting a queued job is not equivalent to a network attempt; a job only has `attempted_at` once its state reaches `sending`. A request may also remain queued because the shared daily or hourly limit was reached or Bob is paused.
- When automatic posting is explicitly disabled, the dashboard cancels *still queued* auto jobs. Those canceled comments were not sent. This behavior is different from cancellation of an already attempted publication.
- The original 3-hour auto-draft maximum age and 7-day manual maximum age still apply when jobs are evaluated. Never blindly repost historic uncertain/published items.

## One read-only diagnosis

From Windows PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 scripts/diagnose_comment_queue.py"
```

Prints: current UTC time, paused and auto-mode state, today’s attempt count against the two-attempt cap, last posting attempt, next rate-limit time (if known), queued manual versus auto counts, oldest records and whether the **installed** publisher is still FIFO or uses manual priority. Shows state counts only; no comment text, credentials, or API responses. Uses SQLite `mode=ro` and never invokes the publisher or Moltbook API. It does not trigger new attempts.

## Change prepared in GitHub, not installed

The publisher dispatch query has been changed to prioritize manually approved comments over automatic candidates while preserving first-in-first-out order within each mode. Existing integrity checks, age limits, per-day and per-hour limits, manual approvals and no-retry guarantees are unchanged. It cannot make another attempt until the relevant rate limit permits it.

Focused offline tests in `tests/test_manual_queue_priority.py` cover disabled-auto starvation, shared cap reporting and read-only diagnosis. **This patch is development-only, not live.** A separately authorized deployment must pin and verify the current installed publisher before updating it. Do not run `bobctl publisher-run` just to diagnose because that is an active publication attempt command and may post if the queue becomes eligible.

For now, evaluate the diagnostic output first. It distinguishes an exhausted shared posting allowance from a blocked head-of-queue or an actual worker error without increasing posting volume.
