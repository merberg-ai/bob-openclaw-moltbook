# R3 strict decision JSON format repair: v0.8.0-r3format1

## What the real OMEN showed

At 19:26:02 PDT on October 31, the second natural R3 proposal cycle began. At 19:26:09, the verified R3 diagnostic package returned a safe `decision_invalid_model_shape` for verified Scout run `20261101T014755Z`; queued=false, attempted=false, dispatch_authorized=false. The timer scheduled the next natural cycle around 20:01 PDT. This means the OpenClaw main agent returned parsable JSON, but the five-field decision shape was rejected. It **does not reveal whether keys were missing, extra or typed incorrectly**. No raw model reply was captured or reported, and we cannot attribute a precise model mistake beyond that category.

## Fixed source, unchanged safety boundary

The new R3-only prompt still includes a delimited, integrity-checked untrusted Scout observation. **After the end-of-data marker**, it now gives Bob a concrete JSON **skip** example containing the exact trusted `source_run` and `target_id`, with five and only five string fields: `type`, `source_run`, `target_id`, `reason`, `text`. For comment, Bob must change only the action, reason and original comment text. No tools, external fetches or publication requests are enabled.

The original strict validator is still authoritative. The new `_shape_reason` classifier only maps a *failed* exact-shape validation to these safe, fixed categories: `decision_shape_not_object`, `decision_shape_missing_fields`, `decision_shape_extra_fields`, `decision_shape_missing_and_extra_fields`, `decision_shape_invalid_field_values`. It never logs model keys or values, remote content, API keys, raw JSON or stderr. Existing source/target mismatches, reason safeguards, copy/link controls and no-send rules remain intact. A model-generated or wrapped object is NOT silently normalized, unwrapped, repaired, queued or posted.

## Source update and acceptance

The explicit `releases/current.json` chain moves from the accepted signed installed `v0.8.0-r3diag1` to `v0.8.0-r3format1`. Exactly three reviewed outputs change: `bob-release-updater`, `bobctl` and `bob_r3_package.pyz`. Both CLI binaries retain strict HTTPS via the trusted private CA. No manager binary or restart, no database migration, no new publisher, no systemd timer changes and no real R3 public dispatch switch are included.

After this source PR has passed CI and merged into `next`, the OMEN operator can, as the ordinary `openclaw` user, execute:

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/bob_release_updater.py --check
```

The expected release is `v0.8.0-r3format1` FROM `v0.8.0-r3diag1`, with three files and `Restart Activity Manager: False`. If the signed installation or timer/pub/Scout topology differs, **STOP**.

After separately reading and approving the update, invoke:

```bash
python3 scripts/bob_release_updater.py
```

Type exactly `UPDATE` only when prompted and only after the automatic read-only ownership preflight passes. The updater backs up and verifies SQLite as existing safety practice, stages signed file hashes, and uses code-only rollback if HTTPS health fails. It never restores older SQLite after possible publisher actions. The existing R3 first-run timer drop-in and service handoff journal are not changed.

Finally, run **one read-only installed verification**:

```bash
python3 scripts/report_r3_format_installed.py --check
```

Expected signed format package, authenticated HTTPS health, authenticated R3 owner controls, existing proposal-only timer and original Scout/publisher ownership PASS, plus overall `acceptance: PASS`. That verifies code deployment, NOT model decision correctness. On the next natural (not manually forced) timer tick:

```bash
journalctl --user -u bob-r3-propose.service --since "2 hours ago" --no-pager -n 35
```

Expected either a valid `proposed`/`skipped`/`none` outcome, or a newly classified safe `decision_shape_*` issue for further investigation. We cannot promise that an LLM obeys an example. Any R3 public comment canary remains a separate exact-owner-approved, source-reviewed release; public publication is still hard Off.
