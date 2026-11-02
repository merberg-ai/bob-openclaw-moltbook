# v0.7.5-logs2: Correlated failures and accurate safety-block diagnostics

From operator-tested `v0.7.5-logs1` to `v0.7.5-logs2`; **one installed module** (`bob_diagnostic_logs.py`), Activity Manager restart only. No publisher, Scout, systemd, shared helper, database schema or memory changes.

## Operator report

The new Logs page is functional but displays redundant “Worker step failed; inspect logs” checkpoints without interpreting the available records. It also shows multiple Comment jobs with **“An owner review decision already exists”**, which is not a failed network submission.

## Explanation of the observed failure

In the managed `bob-moltbook-publisher`, for `mode=='auto'`, the worker checks whether `decisions` already contains a row for that Scout run. If it does, the worker sets `publish_jobs.state='failed'`, stores `last_error='Human decision already exists'`, and stops **before** any Moltbook comment POST. This is a deliberate safeguard to prevent an automatic reply overriding a human approve/reject decision.

An auto job may have been queued while there was no decision and then encountered a decision before the publisher ran. That timing is not independently proved for the reported run, but is consistent with the code and the stored error. This status **does not prove any manual comment was published**. Search for that run separately in Published activity or the existing decision/queue screens.

## Change

- For every failed worker checkpoint, correlate first by **exact service + immutable run/job ID** against the bounded read-only SQLite job results. This turns the publisher’s generic checkpoint into a direct link to its stored sanitized cause.
- If no job record matches, inspect bounded, safely classified systemd journal entries for that worker within **±5 minutes** of the checkpoint. Show a matched entry explicitly as a *nearby observation, not proof of causation*. Application errors are preferred over a generic systemd exit.
- If there is no safe matching entry or systemd journal access is unavailable, say so clearly. The viewer should never send the operator back to “inspect logs” without explaining the missing evidence.
- Classify known pre-send automatic **policy blocks** as **Warnings**, while retaining their factual database state in the message: “intentionally blocked (database state: failed)”. A human review decision or existing friend guard is not a Moltbook HTTP outage. These warnings still appear when severity is **All** or **Warning**, not when limited to **Error**.
- Continue the exact previous redaction, bounded result counts, source provenance and immutable timestamps. No arbitrary journal/error body text is exposed.

## Deployment and acceptance

1. In OpenClawLab, `bobctl update`, verify `v0.7.5-logs1` → `v0.7.5-logs2` and type `UPDATE`. Only one file replaces `bob_diagnostic_logs.py`; Activity Manager restarts.
2. Open **Logs**, choose **Publisher**, **All severity**, **All sources**, **7 days**, and enter run ID `20261029T224411Z` from the operator screenshot. The stored job should say **intentionally blocked** and include the reason **owner review decision already exists**. Its checkpoint should display the same correlated cause rather than the generic inspect-logs placeholder.
3. Select **Severity: Warning, Source: Jobs** for other intentional policy blocks. Genuine failed jobs such as authentication errors remain under **Error**.
4. Set **Scout**, **All severity**, **All sources**, **7 days**. A recent failed Scout checkpoint now attempts a time-adjacent sanitized journal correlation. If none exists, the UI explicitly states the missing cause. This change cannot recover old journal lines that were never retained or made accessible.
5. Ensure the Friends, Memory, Recall, Scout and prior Logs filters behave normally. No page action sends a Moltbook request or retries a job.

No new automatic publication permission or force-retry command exists. Uncertain sends must still never be retried blindly.
