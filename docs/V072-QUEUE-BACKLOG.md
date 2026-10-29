# v0.7.2 queue backlog: facts, diagnosis and manual-first correction

The operator reports that a new original-thought draft generated successfully and a **read-only audit found four published comments visible on Moltbook**. A backlog of queued comment jobs remains. System Status displayed the publisher as waiting, which is consistent with local queue policies but does not by itself establish the reason for every job.

## Reviewed publisher behavior

- The source currently allows **two outgoing comment attempts per UTC day** and at least one hour between attempts, shared by manually approved and automatic comments. These are safety limits and should not be increased without explicit operator approval.
- Before October 29's one-file hotfix, the publisher selected the **oldest queued job of either mode**, which could allow automatic jobs to starve newer manual approvals. The now-deployed publisher selects **manual first**, FIFO within each mode. All previous posting safeguards remain.
- Selecting a queued job is not equivalent to a network attempt; a job only has `attempted_at` once its state reaches `sending`. A request may also remain queued because the shared daily or hourly limit was reached or Bob is paused.
- When automatic posting is explicitly disabled, the dashboard cancels *still queued* auto jobs. Those canceled comments were not sent. This behavior is different from cancellation of an already attempted publication.
- The original 3-hour auto-draft maximum age and 7-day manual maximum age still apply when jobs are evaluated. Never blindly repost historic uncertain/published items.

## Operator's actual queue reading (October 29, 2026, 12:23 UTC)

- Paused: **no**; automatic posting: **enabled**
- Outgoing comment attempts today: **2 of 2**. Daily cap is the current blocker, independently of manual/auto queue ordering.
- Local allowance resets at **2026-10-30T00:00:00Z**, which is **October 29, 5:00 PM Pacific Daylight Time**. The normal one-hour gap still applies to consecutive attempts.
- Waiting: **4 manually approved**, **10 automatic**. Another **24 automatic** were previously canceled and one auto job failed.
- The oldest queued item is **manual**, so disabled-auto queue starvation is **not** currently active; the manual-first patch remains valuable to prevent later automatic entries from using the next eligible slots ahead of approved replies.
- Previously observed successful public visibility checks and original-thought generation establish that core publishing and drafting work; they do not remove the local daily cap.

No need to run `bobctl publisher-run` while the daily limit is exhausted; it cannot create an allowed attempt and is not a diagnostic command. Do not disable or cancel the auto queue solely to clear the dashboard without deciding how those approved policies should behave.

## One read-only diagnosis

From Windows PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 scripts/diagnose_comment_queue.py"
```

Prints: current UTC time, paused and auto-mode state, today’s attempt count against the two-attempt cap, last posting attempt, next rate-limit time (if known), queued manual versus auto counts, oldest records and whether the **installed** publisher is still FIFO or uses manual priority. Shows state counts only; no comment text, credentials, or API responses. Uses SQLite `mode=ro` and never invokes the publisher or Moltbook API. It does not trigger new attempts.

## Change installed successfully (October 29, 2026, 12:29 UTC)

The publisher dispatch query now prioritizes manually approved comments over automatic candidates while preserving FIFO order within each mode. The operator applied the guarded single-file updater `scripts/patch_manual_comment_priority.py` with automatic SQLite backup and code verification. The publisher service was not restarted or manually invoked. Existing integrity checks, age limits, per-day and per-hour limits, manual approvals and no-retry guarantees are unchanged. It cannot make another attempt until the relevant rate limit permits it.

Focused offline tests in `tests/test_manual_queue_priority.py` cover disabled-auto starvation, shared cap reporting and read-only diagnosis. **The operator reports this patch is live.** Four focused tests passed; `MANUAL-PRIORITY UPDATE: manual_priority_installed`, and a following read-only diagnosis confirmed `manual_first_installed: True`. Today's actual blocker remains the two-attempt daily safety cap. No additional post was triggered by the update. A separately authorized deployment must pin and verify the current installed publisher before updating it. Do not run `bobctl publisher-run` just to diagnose because that is an active publication attempt command and may post if the queue becomes eligible.

For now, evaluate the diagnostic output first. It distinguishes an exhausted shared posting allowance from a blocked head-of-queue or an actual worker error without increasing posting volume.
