# R3 diagnostic-only update: v0.8.0-r3diag1

## Observed first natural R3 proposal attempt (2026-10-31)

The owner's OMEN successfully fired `bob-r3-propose.service` at 18:50:34 PDT. At 18:50:39 the worker exited in the **safe refused** state with `openclaw_decision_invalid_or_unavailable`. No job was queued, attempted or granted dispatch. The timer automatically scheduled its next natural execution approximately 35 minutes later. This proves the first-tick timer fix and reveals a missing diagnostic distinction, not a source/owner/Moltbook send failure.

## Repair implemented

R3 now reports a **fixed, allowlisted** failure code, never the raw CLI stderr, prompt or model response. Two distinct error families:

- `openclaw_shadow_agent_unavailable`, `openclaw_shadow_agent_cli_failed`, `openclaw_shadow_agent_envelope_invalid`, `openclaw_shadow_agent_payload_invalid`, or `openclaw_invalid_or_unavailable_model_output`: the OpenClaw main-agent invocation or response envelope failed.
- `decision_invalid_model_json`, `decision_invalid_model_shape`, `decision_unverified_model_target`, `decision_model_reason_empty`, `decision_model_reason_too_long`, `decision_skip_must_not_contain_text`, `decision_invalid_comment_length`, `decision_unsafe_comment_text`, `decision_copied_untrusted_text`, or `decision_invalid_or_unavailable_model_output`: a returned decision was rejected by the exact JSON/target/format validator.

Both retain only the **validated saved source run ID** as a stable, nonsecret identifier. No new network access, no direct Moltbook API call, no model/CLI output logged, no new publisher, no retry of attempted posts. Successful `skipped`, `none`, or `proposed` semantics remain unchanged. An unknown error is deliberately grouped into the safe general category for its stage.

The reviewed release manifest `releases/current.json` advances from installed `v0.8.0-cutover1` to `v0.8.0-r3diag1` and declares only THREE managed code files: `bob-release-updater`, `bobctl`, and rebuilt `bob_r3_package.pyz`. The old private-CA HTTPS mode is explicitly preserved in both CLI mappings. No manager binary update, manager restart, database migration, systemd unit or timer change. All four real R3 public dispatch/auto gates remain hard Off. The on-host guarded updater makes a verified SQLite backup as usual and restores **code and signed registry only** if health fails, never rewinds actual publication history.

## Owner verification (after PR CI passes and merge)

The source checkout must remain clean on `next`; run these as the normal `openclaw` user, without `sudo`. The installed updater from cutover1 does not know the new release identifier, so use the source updater for this first update:

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/bob_release_updater.py --check
```

Expected `BOB UPDATE AVAILABLE: v0.8.0-r3diag1`, exact chain `v0.8.0-cutover1`, THREE files listed, `Restart Activity Manager: False`, no installation yet. The guarded update preflight demands an active original publisher timer, active Scout, active R3 proposal timer, disabled Shadow timer, idle legacy publisher, and an idle or failed R3 oneshot. It verifies the original signed hard-Off release and rejects any competitor or unexpected unit state.

After reviewing the check, explicitly authorize the code-only install by running:

```bash
python3 scripts/bob_release_updater.py
```

Enter exactly `UPDATE` when prompted. No timer is stopped, restarted, manually fired or reseeded; the earlier first-tick drop-in and its original handoff journal remain in place.

Then run ONE read-only installed verification:

```bash
python3 scripts/report_r3_diagnostic_installed.py --check
```

Expected `acceptance: PASS`, signed diagnostic archive PASS, authenticated HTTPS and R3 Controls PASS, existing R3 proposal-only timer ACTIVE and original publisher/Scout topology preserved. This acceptance proves the diagnostic patch is *installed*, not that a model decision has succeeded. On the next **natural timer-fired** service run, use:

```bash
journalctl --user -u bob-r3-propose.service --since '2 hours ago' --no-pager -n 35
```

New `reason` categories distinguish the actual agent failure. Do **not** start the service manually, run a manual publisher, enable the R3 manual/auto dial, restart WSL or modify networking to perform this diagnostic acceptance. If the update preflight or installed acceptance refuses, preserve its sanitized output and stop; do not force an install. The other existing legacy publisher/Scout and all real R3 public send authorization are deliberately unchanged.

## Scope and owner boundary

The timer remains active and will keep producing safe refused/skipped/proposed decisions according to the existing schedule. A draft proposal is **not** a queued comment or permission to send. Any real Moltbook R3 canary requires a separate reviewed release and exact owner consent; this diagnostic patch deliberately provides neither.
