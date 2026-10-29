# v0.7.1 isolated runtime acceptance

This milestone combines the existing installed-layout rehearsal with an actual HTTP startup of the generated Activity Manager under the read-only synthetic browser preview. The preview validates GET /, /activity, /originals, /healthz, representative fictional data, disabled POST and rejected untrusted Host. Its child process binds only to loopback in a temporary synthetic HOME and exits after the self-test.

Run from PowerShell on OMEN:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/accept_v071_isolated_runtime.py"
```

Expected: 163 tests and `v0.7.1 ISOLATED RUNTIME GATE: PASS` when both stages pass. This adds no systemd changes, production database access, live authentication or Moltbook publishing. The generated candidate is imported and exercised as a real loopback HTTP server by the existing preview self-test.

**Limitations:** this does not validate the live service's actual launch path, Basic auth under the real configuration, or a production restart. The direct live ExecStart still needs an explicitly approved update mechanism that can recover if service health fails. Review ZIPs remain non-deployable; do not copy them over the live manager.
