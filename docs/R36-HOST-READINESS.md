# R3.6 host readiness and draft-origin contract

## Real OMEN acceptance snapshot: observed 2026-10-30

The owner ran the documented one-command read-only check successfully from `~/bob-next` immediately after a clean fast-forward to `next` commit `1c4a161`. Reported observations:

| Check | Observed result |
| --- | --- |
| Legacy publisher timer / service | active / inactive |
| Shadow timer / startup reconcile timer | active / active |
| R3 candidate publisher timer / legacy system Scout timer | inactive / inactive |
| Legacy SQLite schema / policy | match / valid |
| Global pause / existing v0.7 auto comments | not_paused / enabled |
| Historical attempted sends | 22 |
| Delivery states requiring review | 0 |
| Baseline consistency / review blockers | observed / none |
| New R3 publication authority / cutover | NONE / NO |

**Assessment: R3.6 point-in-time host baseline accepted.** The inactive publisher oneshot service is consistent with operation between timer invocations. Twenty-two attempts are historical send intents, not twenty-two confirmed public comments; zero review states is not proof every earlier send was publicly visible. The **existing v0.7 auto-comment flag is enabled**, but it confers **no** permission on new v0.8/Bob-generated drafts. Host runtime, actual unit/drop-in semantics, WSL/Windows reboot behavior, current friend/GET preflights and sealed Bob-authored publisher admission are **not** verified by this report. The tool's `cutover authorized: NO` remains binding.

No deployed package, timer, queue content, credential, approval setting or publisher permission was changed by this operator check or by recording it.

---


**Status:** source-only, offline CI acceptance first. The current OMEN installation remains `v0.8.0-shadow4`; the existing v0.7 credentialed publisher remains the sole real writer. This work **does not** grant new permissions, install a service or modify the live queue.

## Operator check, only after PR merge

From the **clean development checkout** `~/bob-next`, run one command sequence in WSL:

```bash
cd ~/bob-next && git pull --ff-only && python3 scripts/report_r36_host_readiness.py
```

This probes fixed allowlisted user/system service units through read-only `systemctl show`, and opens the legacy SQLite queue via `mode=ro`. It checks exact essential queue table/column shape, aggregates counts of queued/attempted and uncertain-delivery records, reads the validated existing policy limits and `auto_enabled`, and checks the pause marker. By default it prints a **short sanitized report** suitable for review. The optional `--json` emits an expanded but still metadata-only report. No raw post/comment, Scout text, API key, unit environment, ExecStart command or file path is printed; no posts or owners are changed. Do not use `sudo`.

**Report interpretation:** `baseline consistency: observed` means only that this snapshot found the expected legacy publisher timer, inert candidate unit names, inactive legacy system Scout timer, and readable compatible queue/settings. It is **not** evidence the new publisher is ready or permitted, and it does not prove Windows boot, timer target/drop-ins, actual GET/friend preflight, service drain or external visibility. If `review blockers` is nonempty, investigate rather than changing services to force a pass. `cutover authorized: NO` is invariant.

## Bob-generated draft admission contract

`src/bob_v08/r36_admission_contract.py` implements **read-only source classification** on an explicitly supplied SQLite connection, using the R3.4 verified Scout feed/result bytes and the R3.3 independently sealed Bob draft. A queued, unattempted job whose exact text matches the originally saved Scout approval is classified `legacy_scout` and stays on the existing v0.7 validation path. A different Bob-authored comment can only be classified `r3_bob` when it has a matching independent sealed proposal linked to the same source run/post/snapshot and fingerprint in the additive R3 table. Missing/source-drifted proposals, inconsistent hashes, changed jobs, attempted or uncertain jobs, and unknown schema all refuse. **Neither classification authorizes dispatch**, owner auto opt-in, a GET result, an approved manual decision, or a real queue write. The installed v0.7 publisher is unchanged.

## Next requirements

- Obtain and review the real sanitized OMEN report. A GitHub CI test cannot establish installed WSL/Windows unit states.
- Verify effective unit-to-service mapping, login/reboot recovery, actual publisher/source configuration and safe drain, without printing passwords or starting candidate units.
- Design and test one credentialed publisher-side admission path that obtains owner settings, friend protection, external target GET and final pause state from trusted local sources. No model/caller-supplied `Proof` is authority.
- Do a separate explicit owner-approved update and post-update rollback gate. Preserve all attempted and uncertain sends in place, never overwrite live SQLite with a stale backup.
- R2's naturally timer-driven **source-linked model decision** is still separate pending evidence.

**No new Moltbook action category, permission or additional publisher has been enabled by R3.6.**
