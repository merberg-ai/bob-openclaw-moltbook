# v0.7.1 service entrypoint verification (read-only)

The operator confirmed 138 local tests, exact live manager hash, recent owner-private SQLite backup integrity, and a loaded/running Activity Manager. The browser UI was also visually accepted.

Before writing the actual versioned production updater, inspect how systemd launches the manager. The deployed manager may be invoked directly or through a wrapper, and the update/rollback design depends on this distinction.

From PowerShell on OMEN:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/inspect_v071_service_entrypoint.py"
```

The command reads `systemctl --user show` without changing units or their state. Its output contains **only boolean classifications**: loaded, running, direct reference to the known manager path, presence of unit fragment and drop-ins, and whether launch details remain ambiguous. It does not print potentially secret-bearing `ExecStart`, environment, or full path strings.

A direct reference is not proof of safe deployment: a wrapper, override, unexpected working directory, environment file, or module import path can still matter. A `NO` direct reference is not a reason to modify or restart the service. Do not paste raw `systemctl cat` or `ExecStart` into public chat; values may contain credentials.

Next: design and test a new versioned installer/recovery routine against synthetic services and private staging. **No production update is authorized by this inspection.**
