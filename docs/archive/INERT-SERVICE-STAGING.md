# v0.7.0: Inert service-graph staging acceptance

**Status: developer-only, OFFLINE simulation. Not an installable systemd release.**

The sanitized operator ZIP (15 systemd files/drop-ins) was reviewed as non-deployable. Its contents supported the conceptual service topology and timer cadences, but **not** original command arguments, actual environment files, drop-in precedence, Gateway's withheld directives, real service isolation, or Windows unattended boot behavior. This phase deliberately does not invent those missing details.

## What is generated

`scripts/stage_service_graph.py` creates a **temporary, private sandbox** automatically, never writing units into `/etc/systemd`, `~/.config/systemd` or Bob's live `~/.local` installation. It models exactly **six mock services**: Gateway and Activity Manager as long-running service shapes, and scout, publisher, original worker and startup reconcile as one-shot service shapes. Four mock timers reference only staging-prefixed services; the disabled legacy system scout is deliberately excluded.

All names begin with `bob-v070-stage-` and have no relation to installed production unit names. The mock Gateway is only an inert process model, not OpenClaw. The mock manager does not start a web server. Workers do not import Bob modules or contact Moltbook, Ollama, Docker, or the network.

A sandbox contains two mocked release copies (`baseline` and `candidate`), an atomic local `current` symlink, a `STAGING-MARKER.json`, a private `MOCK-CONFIG.json` requiring `network_access=false`, `allow_publish=false` and a nonfunctional dummy credential, 10 static service/timer unit definitions, and a new synthetic SQLite database with **no live schema, rows or credentials**. All are deleted automatically when the acceptance command ends.

The mock units model reported schedules: publisher OnBootSec 2min + OnUnitActiveSec 1min; original worker 3min + 2min; scout 1h; startup reconcile OnStartupSec 30s + OnUnitInactiveSec 2min. These values come from the sanitized candidate review. Actual startup timing remains unproven. In the `/tmp` staging graph `PrivateTmp=no` intentionally differs from production, since the fixture itself lives under `/tmp`; never treat these generated files as deployable replacements.

## One PowerShell acceptance command

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "set -euo pipefail; cd ~/bob-v070-inventory; GIT_TERMINAL_PROMPT=0 git pull --ff-only; python3 -m unittest discover -s tests -p 'test_*.py' -q; python3 scripts/rehearse_release_rollout.py; python3 scripts/stage_service_graph.py"
if ($LASTEXITCODE -ne 0) { throw 'v0.7.0 inert staging acceptance failed' }
~~~

Expected console signature on passing implementation:

~~~text
Ran 84 tests
OK
ISOLATED RELEASE REHEARSAL: PASS
INERT STAGING SERVICE GRAPH: PASS
  services: 6
  timers: 4
  mock_runs: 14
  independent_sqlite: True
  health_failure_rollback: True
  post_swap_writes_preserved: True
  live_install_modified: False
All temporary staging files removed. NOT DEPLOYABLE.
~~~

Service-graph acceptance is a **static reference-graph check and isolated Python mock execution**, not a claim that systemd actually started or verified the units. It intentionally does not invoke `systemctl`, `systemd-run`, network APIs, Windows Task Scheduler, or the installed Bob executables.

## Remaining release gates

1. Read-only audit of **allowlisted missing directive names** for the eight unclassified Gateway directives and other omitted unit keys. Do not collect original values or full `ExecStart` commands in public artifacts.
2. Independently verify exact user/system unit selection and order of original drop-ins, then build complete sanitized staging templates without inventing missing live settings.
3. Optionally run `systemd-analyze verify` on a controlled staging-only unit bundle. This has **not** yet been performed and is not the same as installing, enabling or restarting anything.
4. Separately rehearse stage-only service manager execution with isolated names, dummy credentials and explicit fail-closed networking restrictions. Only then consider actual full upgrade/rollback and worker drain checks.
5. Verify Windows interactive-logon recovery and unattended cold-boot behavior without assuming `Linger=yes` launches WSL.

**No staging units are registered with systemd. No actual Moltbook publishing, status changes, live database access, service restarts or Windows startup changes occur.**
