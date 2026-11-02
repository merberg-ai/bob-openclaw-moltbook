# Publication-workflow repair: approved automatic draft → explicit manual queue

**Candidate release:** `v0.7.6-pubfix-manual1` from operator-accepted `v0.7.6-oc3-console1`. **Not installed until the operator runs `bobctl update`.**

## What went wrong

The Console revealed several recorded automatic comment jobs blocked with `Human decision already exists`. This message applies to either approved or rejected drafts; it is not evidence of an owner approval waiting to complete. The publisher correctly refuses to send a draft *automatically* when an owner has made a review decision. However, a blocked/queued automatic job occupied the unique `run_id` in `publish_jobs`, and the owner-visible page hid its manual publication button. The existing manual `queue_manual` refused **any** previous job, even one that demonstrably never attempted to send. Approving therefore could leave a draft stranded.

## The repair

An operator who has **approved a verified, unchanged Scout draft** can now use an explicitly displayed **Queue approved draft manually** button for an existing auto job which is (a) still queued with no previous error or (b) failed solely because an owner decision already existed or because friend-targeted automatic posting was intentionally blocked. The existing `/publish/<run_id>` handler, CSRF/digest check, manual approval and database backup are unchanged.

This action atomically converts the one *existing* `publish_jobs` row from `auto` to `manual` with `state='queued'`, clears the historic no-send error and records `publish_manual_handoff`. It does not immediately call Moltbook or bypass rate limits, safety guards, post preflight or verification. The normal publisher timer later prioritizes this approved manual job.

### Critical fail-closed rules

A handoff is forbidden unless all of the following hold:
- A current owner `decisions` record explicitly says **approved** for the exact saved `approval_sha256`. Reject/changed digest remains blocked.
- The entire original `scout-result` and saved feed revalidate, and the stored job has the exact same post ID, approval digest and unchanged draft text.
- The job is `mode=auto`, has no `attempted_at`, no recorded `comment_id`, and no challenge/verification data. Only `queued` with no error or one of two known **never-sent** review-block reasons is recoverable. No arbitrary failed, expired, sending, uncertain, verified, rejected, manual, already published or previously attempted jobs may be retried.
- The database `UPDATE` has a full compare-and-swap predicate, including current approval, job mode/state, original post/draft/digest, all no-send fields and exact past review-block reason.
- The publisher's review/friend auto-block writes are constrained to *still-queued automatic jobs*. Its final send-intent claim atomically rechecks the exact current mode, original data, approval status for manual mode or *absence of an owner review* for auto mode. If the job changed during preflight, the publisher **does not send** under stale permission. Its persisted `sending` state still precedes any irreversible network POST.

There is **no automatic retry**, no database migration and no reopening of ambiguous network attempts. An explicit review approval does **not** by itself publish; the owner must still click the queue action.

## Release content and rollback

Normal `bobctl update` installs three reviewed files: `bob_publish_common.py`, `bob-moltbook-publisher`, and a pinned generated `bob-activity-manager`. Activity Manager restart only, with existing private DB backup and code rollback. Existing credentials are not touched or displayed. Existing auth, Host, Origin, CSRF, review, publisher rate/budget, global pause, friend-targeted and duplicate-post safeguards remain unchanged.

Synthetic `tests/test_publication_manual_handoff.py` covers fresh approved automatic queue, historic review-blocked failed queue, previously blocked friend auto job, exact source/digest/decision checks, no-action cases for all sent/uncertain/challenge/expired/tampered states, prevention of duplicate manual clicks, a stale publisher selection raced by owner handoff, normal manually authorized publishing and AST identity of all generated HTTP handler methods.

## Short operator acceptance

1. In OpenClawLab run `bobctl update`, confirm `v0.7.6-oc3-console1` → `v0.7.6-pubfix-manual1`, type **UPDATE**.
2. On the authenticated LAN **Scout & review** page, find an existing **approved** draft corresponding to a blocked automatic job. If it was blocked *before* a send, the page now offers **Queue approved draft manually**. It should not offer it for rejected/uncertain/published jobs.
3. **Do not click the button merely to test the release.** It schedules a real Moltbook comment. If you actually want that comment, click it once and confirm it appears as `manual, queued`. Normal publisher limits and timers then apply.
4. Existing Console, Overview, Automation and existing review actions should continue to load.

**Next, after operator verification:** OC4, the one-view **Why no activity?** investigation panel with evidence-backed skip reasons and explicit approved-vs-rejected automatic block categorization. FM4/FM5 remain on hold.
