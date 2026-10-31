# R3.8 Inert Publisher Dispatch and Effective Unit Review

**Scope:** source-only development on `next`. The installed `v0.8.0-shadow4` and v0.7 credentialed Moltbook publisher are not changed. The R3.8 module **does not POST, read API keys, install units, or authorize any new automatic action**.

## Offline publisher lifecycle

`src/bob_v08/r38_dispatch_lab.py` exercises a production-shaped but strictly synthetic sequence in the existing marked private `r3-unified-lab.sqlite3` fixture:

1. R3.7 independently rechecks the saved Scout source, separate owner consent, exact Bob-authored text seal, friend protections, active pause marker, legacy budget/spacing and manual-first queue. An injected GET fixture must return the exact post and author, and the checks are repeated afterward.
2. Only a successful R3.7 gate commits `sending_simulated` and a durable `publish_jobs.attempted_at` in **the same simulated legacy queue**. There is no second posting allowance or separate credentialed publisher.
3. R3.8 checks owner flags, source/author/friend provenance, pause, exact queued payload, historical attempted targets and lowered limits again before invoking the only transport it accepts: `InertSink`. This is an in-memory receipt script, with no network method or credential access. The follow-on check cannot eliminate every real-world time-of-check/time-of-use race: true production finalization still requires a publisher-owned pre-POST gate and intentionally bounded delay.
4. A synthetic acknowledgment with a comment UUID records `acknowledged_simulated`, **not `published`**. A verification challenge records `awaiting_verification_simulated`, with **no automatic solving**. A timeout, malformed response or unsuccessful result is `uncertain_simulated`. All retain the attempted-at slot. No response text or API key is persisted in the fixture's audit.
5. Crash after intent/before sink and crash after sink/before receipt both leave `sending_simulated`. `recover_after_restart()` converts only valid synthetic in-flight records to locked uncertainty, without calling the sink or resetting `attempted_at`. A corrupt synthetic record stays un-retried and flagged. Preexisting legacy `sending`/`uncertain`/verification states are **never modified** by recovery and are counted for manual review. Re-running dispatch on any already-attempted target fails because the R3.7 gate requires a queued, unattempted job.

R3.8 offline tests cover double-worker claims, each possible fake response, owner/friend/pause/budget/source revocation after intent, SQL receipt-audit crash, process crash at either side of the fake sink, correct unknown recovery, legacy uncertain-history preservation, strict transport type, and no credential/HTTP clients.

## Installed effective publisher service: one read-only check

Once R3.8 is merged into `next`, the owner can run in **OpenClawLab WSL**:

```bash
cd ~/bob-next && git pull --ff-only && python3 scripts/report_r38_effective_units.py
```

The command updates **only the clean development checkout**, then calls **`systemctl --user cat` only for** `bob-moltbook-publisher.service` and `bob-moltbook-publisher.timer`. It parses the effective unit text and override order, including empty `ExecStart=` resets. It reports bounded classifications: one verified publisher executable, oneshot service type, unexpected extra process directives/restart policy, timer target and cadence, counts of drop-ins and environment declarations. Raw command lines, secret environment values, paths and drop-in contents are **never printed**. If the unit syntax is more elaborate than this conservative parser understands, it returns `unverified`, not a pass.

The output is **evidence**, not a permission grant. A reviewed-shape response does not prove WSL reboot continuity or complete credentialed publisher safety. A blocker should be investigated, not silenced by enabling/disabling a timer.

## Still blocked before a real cutover

- A real, hardened host-owned GET/author proof and pause consistency check must be integrated inside the **existing single credentialed publisher**.
- Actual R3 Bob-draft queue admission and final pre-POST compare-and-swap must be merged into that publisher. The v0.7 publisher currently only knows the original Scout draft contract.
- Effective unit output and reboot/drain behavior must be reviewed on the actual OMEN. R3.6's zero-blocker baseline covers unit activity and schema, **not** unit file overrides.
- A new explicit owner-approved v0.8 auto-comment setting, versioned release, recovery and rollback acceptance will be required. The old `auto_enabled=1` does **not** authorize Bob-generated comments.
- The naturally timer-driven source-linked Shadow4 OpenClaw decision remains an independent R2 evidence gate.

**R3.8 does not install, start, stop or migrate any live service. Cutover authorization remains NO.**
