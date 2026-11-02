# v0.7.1 real process-crash recovery acceptance (non-deployable)

This test **really kills a dedicated subprocess** with SIGKILL after a durable transaction checkpoint, then verifies the state from a surviving parent process. It uses only two temporary private directories, a synthetic SQLite file, a synthetic release pointer, and the pinned reviewed candidate code. No systemd, real service, credentials, publication or live database are accessed.

The two tested checkpoints:
- `prepared`: kill before switching, leaving the baseline active and journal phase prepared.
- `candidate_selected`: kill after switching, leaving candidate selected with an incomplete journal.

The parent checks the expected negative SIGKILL exit status, newly obtainable exclusive lock, surviving journal contents, release integrity, and unchanged synthetic database. It refuses to interpret an incomplete journal as deployment success or safely resumable. **Automatic recovery is intentionally not provided.**

## Windows PowerShell acceptance

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_process_crash.py --checkpoint prepared && python3 scripts/rehearse_v071_process_crash.py --checkpoint candidate_selected"
```

Expected regression count: **196** (previous 191 plus five); host verification required. Each standalone crash checkpoint should report `v0.7.1 PROCESS CRASH LAB: PASS`.

## Boundaries and outstanding gates

- This tests process death after two explicit checkpoints, not arbitrary power loss, disk write reordering or every byte boundary.
- The staged release pointer has no systemd integration. It does not start the real Activity Manager.
- The rollback decision for incomplete on-disk transactions remains **operator-directed**. Journal recovery has not yet been implemented for production.
- Never run with privileged permissions or copy these rehearsal scripts into the live service path.
- No production deployment permission has been requested or granted. The review archive remains `deployable: false`.
