# v0.7.2 Settings candidate integration

This development-only increment composes the pinned v0.7.1 manager and navigation with a fourth navigation destination, `/settings`, and POST `/settings/password`. It uses `bob_dashboard_auth.py` to dynamically verify LAN credentials from the existing private auth file and rotate them with an atomic rename. The change form requires current/new/confirm, bounded body and CSRF/origin checks. Passwords never appear in GET URLs, logs or response bodies.

The candidate builder `scripts/build_v072_settings_candidate.py` only returns source bytes. It does not install them, read production passwords, restart systemd or modify SQLite.

First-run validation:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/build_v072_settings_candidate.py"
```

The Settings page is not yet deployed. Before shipping, exercise real local HTTP GET and POST in a synthetic HOME with a private fake `lan-auth.json`, proving that old browser credentials fail immediately after successful rotation and incorrect CSRF/current password do not mutate the file. Then deliver status indicators and a versioned release. Existing production v0.7.1 stays unchanged.
