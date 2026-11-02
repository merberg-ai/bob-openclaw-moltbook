# R4 live OMEN GO/NO-GO, one read-only command

**Status:** PR #137 merged into `next`; the previously recorded 2026-11-01
OMEN read-only host inspection passed seven checks with zero blockers.
Source-only manifest promotion PR #138 advertises R4 to the owner updater,
but it does not install/migrate or authorize public social actions.

## Before and after manifest promotion

The historical pre-promotion source command below was used for the actual
owner host snapshot on 2026-11-01 PDT. Once PR #138 is merged to `next`, the
exact promoted source must be checked from the trusted, updated `~/bob-next`
checkout. Run this **read-only** source+OMEN report (no installation):

```bash
cd ~/bob-next && git pull --ff-only && PYTHONDONTWRITEBYTECODE=1 \\
  python3 scripts/report_r4_go_nogo.py --check
```

A PASS now means `promoted_manifest_verified:true`, the new current manifest
matches the reviewed candidate exactly, and seven host probes still pass
against the independently unchanged installed R3 canary. It is NOT the owner
installation prompt. See [R4 promotion and installation](R4-PROMOTION-AND-INSTALL.md).

## Run once in OpenClawLab as the normal openclaw account

This uses a dedicated **source-review checkout**, avoiding any modification
of the trusted `~/bob-next` updater checkout or the live installation:

```bash
if [ -d "$HOME/bob-r4-review/.git" ]; then
  git -C "$HOME/bob-r4-review" pull --ff-only
else
  git clone --quiet --depth 1 --single-branch --branch feature/r4-autonomy1-consolidated \
    https://github.com/merberg-ai/bob-openclaw-moltbook.git "$HOME/bob-r4-review"
fi && PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/bob-r4-review/scripts/report_r4_go_nogo.py" --check
```

This single paste is safe to repeat. The fetch/clone only changes
`~/bob-r4-review`. No `bobctl update`, no service restart, no database
backup, no R4 DDL, no new credentials, no timer changes and no Moltbook API
requests. **Do not use sudo/root**. No `UPDATE` or `ARM` prompt is issued.

### Read-only checks

The script combines the existing candidate-source audit (expected exact
23-file signed-release payload, HTTPS generated dashboard, four R4 send-Off
source markers) with the dedicated `report_r4_preinstall.py` host check:
exact signed installed R3 canary, owner identity, active original
publisher/Scout/R3 proposal timers, no competing publisher, inactive
credentialed publisher service, safe effective service/timer and drop-ins,
verified local CA-authenticated HTTPS, no incomplete updater transaction.

Results are a compact JSON object with named booleans, reason codes and
no secrets, private file paths, API keys, session text, raw unit
definitions or queue payloads. `ready_for_separate_release_review:true`
means all checks passed **at the moment of sampling**, not that the
owner has agreed to install or that systemd cannot change later.

If a timer briefly starts the publisher during inspection,
`host_publisher_inactive` may be false. Do not stop the timer just to
make the report pass; wait for the normal unit to become idle and
repeat the read-only check. Any other false field needs investigation,
not automatic repair. If Git refuses the fetch, the report never runs;
don't bypass remote/certificate verification.

## Evidence and next controlled gate

Paste the JSON result from the command into the project conversation.
Review it before making any deployment change. On PASS, separately
complete source PR review/merge into `next`, then a distinct release
promotion updating `releases/current.json`, re-run the real host
preflight and require a fresh typed `UPDATE` before **one** R4 installation.

The currently installed R3 updater does not recognize the R4 HTTPS
release identifier; the eventual installation must use the updated,
reviewed `next` checkout's `python3 scripts/bob_release_updater.py`,
never the older installed `bobctl update`. Installed acceptance is
a separately read-only `scripts/report_r4_installed.py --check`.

No public R4 upvote/follow/comment/post send is enabled by R4
installation. That requires a separate later signed source change
and separate explicit owner authorization.
