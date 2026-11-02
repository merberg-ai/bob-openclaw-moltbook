# Bob development loop (Phase 0)

The goal is one interaction per checkpoint instead of dozens of copy/paste rounds.

## Host evidence: one command, read-only

Run this as `openclaw` inside OpenClawLab, from the trusted checkout. No install or release is needed:

```bash
python3 ~/bob-next/scripts/bob_evidence.py                          # last 24 h
python3 ~/bob-next/scripts/bob_evidence.py --since "2026-11-02 09:00"
```

The bundle covers:
- installed release and registry hash check
- every Bob/OpenClaw unit's state, plus LAST/NEXT for timers
- R4 `--status`
- allow-listed journal lines (systemd lifecycle and the workers' status JSON only)
- port and HTTPS health checks
- queue/ledger state counts
- the `~/bob-next` revision

It is saved to `~/.local/state/bob-evidence/latest.md` (0600). Paste or attach that file as-is.

What it never does:
- Write to SQLite: it opens the DB with `mode=ro` and only counts rows.
- Start, stop, enable, reset or reload a unit.
- Read credentials or persona files.
- Print model or feed text.
- Emit anything that matches a secret pattern; if one matches, it refuses.

When a Claude session is linked to the OMEN, the agent runs this command itself. State-changing commands (`UPDATE`, `ENABLE R4 SCHEDULE`, `--disable`, `--recover`) stay owner-typed at a real terminal.

## Offline development

```bash
python3 scripts/dev.py test             # whole suite, parallel, about 30 s
python3 scripts/dev.py test r4 ui       # by area (see: dev.py areas)
python3 scripts/dev.py test -k schedule # by file name
python3 scripts/dev.py check            # compile + manifest sanity + all tests (CI runs this)
```

Each test module runs in its own process with umask 022, as a normal user. CI additionally runs the whole suite in one process to catch cross-module import and order bugs.

## Fixed in this pass

These tests were coupled to the GitHub runner and failed elsewhere:
- `test_r4_producer` assumed uid 1001.
- `test_oc41_diagnostic_polish` relied on another module having put `webui/` on `sys.path`.
- `test_v08_package_preview` used `unittest.mock` without importing it.
