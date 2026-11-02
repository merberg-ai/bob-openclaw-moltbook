# v0.7.1 isolated HTTP service adapter

After the operator accepted 177 offline tests and the journal/locking simulations, this increment adds an actual loopback HTTP fixture to exercise bounded start/health/stop behavior. This **does not launch Bob's Activity Manager** and does not touch systemd, the production database, credentials, or Moltbook.

## Run on OMEN

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_http_adapter.py --scenario healthy && python3 scripts/rehearse_v071_http_adapter.py --scenario failed-health && python3 scripts/rehearse_v071_http_adapter.py --scenario failed-recovery"
```

Expected 184 tests, subject to host verification, and three `v0.7.1 HTTP SERVICE ADAPTER: PASS` results.

The fixture starts a local `127.0.0.1` server on an ephemeral port, responds to `/healthz`, and verifies status **and** response body. A failure ends that server and starts a separate synthetic recovery server. Start attempts are capped at two; health polls are capped at two per phase; the server is stopped after each scenario. No external ports are exposed.

**Limit:** this validates the adapter shape, not the real two-file Activity Manager's boot under a service manager. The stage adapter is not connected to the journal, and there is no production restart or rollback action. The UI review ZIP remains non-deployable. The real systemd ExecStart, environment, working directory and drop-ins require a separately approved deployment path.
