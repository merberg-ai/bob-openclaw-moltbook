# v0.7.1 Production Integration, gate 1: effective systemd preflight

The v0.7.1 operator has accepted 196 tests through real disposable subprocess SIGKILL checkpoints. This step adds `scripts/preflight_v071_effective_service.py`, a **read-only** user-systemd service inspection that never prints command lines, environment values, working directories, database records or credentials.

The check obtains effective `systemctl --user show` properties in one bounded call, refuses unknown/duplicate/missing properties, then classifies active/running state, original SHA-pinned manager, expected direct ExecStart, present working directory and inline environment, no EnvironmentFile or unexpected hooks, no dynamic-user or root/image redirect and backup freshness/integrity. Any drift is REFUSED. The unit source inventory tool is complementary and is not a replacement for effective systemd evaluation.

**This is not permission to deploy.** It does not stop/restart the live unit, write a drop-in, switch releases, access the live SQLite database or publish to Moltbook. The verified current direct ExecStart means a synthetic `current` symlink cannot redirect the real service.

## Operator acceptance

First run tests after pull:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q"
```

Expected regression count **205** (previous 196 plus nine); host confirmation required.

For optional read-only effective service inspection, supply the **exact absolute path** of a recently verified private backup file, with no spaces or shell metacharacters in that path:

```bash
python3 scripts/preflight_v071_effective_service.py --backup /exact/private/path/verified.sqlite3
```

The preflight fails closed when the backup is stale (older than 24 hours), the service has drifted, or rendered ExecStart differs from the conservative expected format. In that event, investigate rather than modifying systemd or loosening the gate. Its parser is deliberately conservative: the exact ExecStart rendering can differ between systemd versions and must be validated on the host.

## Next

After preflight acceptance: design an operator-approved release-path switch or safe in-place atomic replacement compatible with the actual effective ExecStart and drop-in precedence; re-check backup and authenticated LAN behavior before any live change. The candidate review ZIP remains `deployable: false`.
