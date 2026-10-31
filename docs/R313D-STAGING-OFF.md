# R3.13d staging checkpoint: versioned schema + safe rollback, still Off

**Status: SOURCE-ONLY STAGING. Not a cutover, not installable, and not owner authorization for real Bob comments.** This phase prepares the final production migration and activation without touching the installed `v0.8.0-shadow4` release, the legacy credentialed publisher, its user-systemd units, the real activity queue or Moltbook credentials.

The owner's request to proceed with R3.13d authorizes development and offline rehearsal. It does **not** implicitly approve a new public comment or automatic posting. The real publisher stays protected by three source-level Off gates. No environment variable, old `auto_enabled` setting, test result or active Shadow4 timer enables R3 sends.

## Owner-operated OMEN acceptance: PASS (2026-10-31)

Both recommended commands were run on the owner's OMEN/OpenClawLab WSL host after merging the source-only R3.13d stage. The first, read-only check reported: trusted queue `yes`; legacy schema `match`; installed R3 owner consent `absent_off`; effective publisher unit `reviewed_shape`; executable `owner_controlled_regular`; private updater registry `verified_registry_hash`; three source-level hard-Off gates `verified_three`; staging eligible `yes`; no source/boundary blockers.

The explicit `--private-copy` rehearsal reported a successful disposable schema upgrade with action-envelope schema `match`, default-Off R3 controls, passing crash rollback, idempotence, unchanged legacy history and a synthetic uncertain attempt preserved under code-only rollback. Historical snapshot: **22 attempted sends, 0 uncertain states**. Private copy was deleted. The operator output confirms no changes to installed services/files, live database, R3 permissions or publication dispatch.

**Scope:** sanitized *operator-reported point-in-time private-stage acceptance*. These results do not imply a live SQLite migration, a new installed publisher, permission to publish Bob's comments, confirmation of public visibility for the 22 historical attempts, or completed production R3.13d acceptance. No `bobctl update` or systemd mutation is required for this staging checkpoint.

## What's implemented

- `src/bob_v08/r313d_staging.py` implements the reviewed additive migration **only for the exact marked R3.13b disposable SQLite fixture**. It validates the existing legacy schema and explicit Off R3 settings, adds `r313c_action_envelopes` and `r313c_schema_meta` (version `r313c-action-v1`) in one `BEGIN IMMEDIATE` transaction, checks schema and all preexisting history, and fails closed on partial, corrupted, future-version or already-enabled R3 owner state. A synthetic pre-commit crash leaves neither new table. Reapplication is idempotent.
- A separate **private-fixture-only** proposal producer validates a saved Scout source, recomputes Bob's independent draft seal and fingerprint, and atomically saves the bounded canonical action envelope with its R3 proposal. It does **not** insert into `publish_jobs`, approve manual decisions, enable owner settings, or dispatch. This is contract rehearsal for the future authenticated owner/producer path, **not an installed producer**.
- The source gate checks three exact source-level values (publisher lazy-import guard Off, R3.12 real dispatch False, R3.13c real dispatch False) without importing or running the publisher. It is a source-shape check, **not cryptographic code signing or installed binary attestation**.
- `scripts/report_r313d_host.py` performs the existing R3.13b trusted queue boundary and installed executable/registry checks plus the source Off gate **read-only**. Only with an explicit `--private-copy` argument, and only if the installed publisher hash and boundary are reviewed, does it use SQLite online backup to a private 0600 disposable file and upgrade that copy through R3.13b and R3.13d. It verifies crash rollback, idempotence, Off settings, legacy attempts and replies, preservation of a newly simulated uncertain attempt under code-only rollback, and deletion of the copy. Committed SQLite WAL is included.
- The tests only use offline private fixtures; no Moltbook GET/POST, OpenClaw agent, credentials, systemd installation, release activation or actual owner approval is performed.

## OMEN operator checkpoint after source merge

First run the **read-only** report as the regular OpenClawLab user, with no `sudo`:

```bash
cd ~/bob-next && git pull --ff-only && python3 scripts/report_r313d_host.py
```

If it says `staging eligible: yes`, run the separately requested disposable-copy rehearsal:

```bash
python3 scripts/report_r313d_host.py --private-copy
```

The command only returns sanitized labels and counts: no hashes, source filenames, personal drafts, credentials or raw SQL rows. `--json` is optional.

No `bobctl update` is required or appropriate. No unit is started, stopped, disabled, enabled, or restarted. No production DDL or changed owner permissions are applied. In particular, the synthetic uncertain attempt is **only in the disposable copy** and cannot be confused with a real outgoing post. If source integrity or host boundaries are not reviewed, the rehearsal refuses to proceed.

## Next actual production rollout work (remaining within R3.13d)

These are independent explicit acceptance gates, **not completed by passing this source-stage rehearsal**:

1. Review a versioned `v0.8.0-cutover1` release manifest / staged source set, verified updater path, installed publisher version and dependencies, and controlled publisher drain. **Do not let two senders share credentials or a queue.**
2. Add authenticated Activity Manager Controls pages for separate R3 manual and automatic settings with exact per-draft approval, CSRF/Origin/Host checks and explicit typed consent, and a trusted source-linked proposal writer. Default Off must survive migration and software rollback. Preserve v0.7 permission/budget parity.
3. Perform a separately **owner-authorized** real SQLite migration using verified private backup, service maintenance window and durable journal; publish no R3 drafts before owner approval.
4. Perform a tightly bounded **owner-authorized** canary, validate exact post+author GET, verification challenge, API ACK versus public visibility, uncertain-send no-retry behavior and one credentialed publisher.
5. Validate stop/restart, Windows/WSL reboot, source/owner revocation and **code-only rollback without reverting newer SQLite attempts**. Record G2 evidence. R2 G1 remains separately pending.

**Cutover authorized: NO. New R3 publication rights: NONE.**
