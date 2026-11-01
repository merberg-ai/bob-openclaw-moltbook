# R3 cutover1 owner handoff: one code acceptance, no publishing

**STOP: prepared for a future OMEN acceptance, NOT authorized for installation now.** The current release manifest still advertises `v0.8.0-chhttps3`, and `releases/candidates/r3-cutover1-integration-off.json` is a **source candidate**, not promoted. An owner must approve any promotion, code installation and later systemd handoff. All four real R3 send gates remain hard Off.

## What the owner will eventually accept

Only ONE credentialed sender continues: the existing `bob-moltbook-publisher` service/timer; Scout continues. The R3 code package and HTTPS Activity Manager are signed by installed SHA registry, the old CA is trusted and the same private LAN URL works. Original SQLite history is retained, R3 owner controls remain Off and the proposal-only timer is initially uninstalled. A successful install does **not** cause Bob to post a new R3 comment.

## One guarded code update and one integrated check, AFTER release promotion

Use the normal `openclaw` WSL shell on OMEN, no sudo. The **checkout-source** updater is required for this first release because the currently installed updater does not recognize the new release ID during health verification.

```bash
cd ~/bob-next && git pull --ff-only
python3 scripts/bob_release_updater.py --check
```

Confirm `BOB UPDATE AVAILABLE: v0.8.0-cutover1`, exact chain from `v0.8.0-chhttps3`, the reviewed **12 files**, and a TLS manager restart. If something differs, STOP. The check does not install anything.

Once the owner explicitly approves the Off-first upgrade, execute:

```bash
python3 scripts/bob_release_updater.py
```

The updater reuses the read-only G2 host audit and demands the existing publisher oneshot be **inactive** before asking for typed `UPDATE`. It never stops the publisher to force the check. On approval, it backs up and verifies the private SQLite, replaces only allowlisted code files, stages signed registry hashes before manager restart, checks authenticated private-CA HTTPS, and restores **code and registry only** on failed health. It NEVER restores older SQLite after a possible send.

The one installed acceptance command is:

```bash
python3 scripts/report_r3_cutover_installed.py --postcheck
```

Expected: `acceptance: PASS`, installed signed cutover1 hard-Off verified, HTTPS health PASS, authenticated R3 controls PASS, R3 owner `default_off`, single legacy publisher PASS, R3 proposal timer OFF, no unresolved attempted send. This is metadata and local HTTPS GET only, with no external Moltbook calls or host changes.

## Optional *separate* proposal-only timer handoff

This **is a real systemd change** and must not be run merely because code acceptance passes. When the owner explicitly wants R3 proposal-only scheduled decisions to replace R2 Shadow decisions, first run read-only:

```bash
python3 scripts/r3_service_handoff.py --check
```

If every exact-name service and installed Off gate passes and the owner separately approves the decision-producer handoff:

```bash
python3 scripts/r3_service_handoff.py --apply
```

Type `ACTIVATE R3 PROPOSALS`. The guarded step installs/enables only `bob-r3-propose.service`/`bob-r3-propose.timer`, disables only the idle old `bob-v08-shadow.timer`, and **never** changes the actual publisher/Scout services or Moltbook. A private journal supports `python3 scripts/r3_service_handoff.py --recover`, requiring `RECOVER R3 SHADOW`, to restore the R2 schedule without rewinding SQLite. Do not run the recovery tool while a proposal worker is active.

## Never do these

No manual publisher service starts, no forced replay of attempted or uncertain jobs, no SQLite restore from an earlier point after publication, no added credentialed publisher/timer, no HTTP downgrade or bypassed certificate checks, and no public canary based only on code-upgrade consent.

**Public R3 publishing still requires separate source-review release and owner approval of the exact post, exact draft, and one attempted send.** These Off-first steps deliberately do not authorize it.
