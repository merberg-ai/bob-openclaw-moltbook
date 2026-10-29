# v0.7.1 durable release controller: offline transaction gate

This increment adds `scripts/rehearse_v071_durable_release.py`: a durable, crash-recoverable, **disposable** release-pointer transaction. It uses validated two-file staging, an OS file lock, fsync of the journal and parent directory, an atomic release symlink replacement and a separately callable recovery action. Recovery restores the original release pointer while retaining later synthetic SQLite writes.

**Critical limit:** This is NOT a production installer or a real systemd restart/recovery controller. The recovery transaction validates only a disposable code pointer; it does not certify a restarted service or authenticated health. There is intentionally no production execution option.

To verify on OMEN:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m py_compile scripts/rehearse_v071_durable_release.py && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/rehearse_v071_durable_release.py --scenario crash-restart && python3 scripts/rehearse_v071_durable_release.py --scenario failed-health"
```

Expected: **252 tests** (244 previously verified + 8 new), and two `v0.7.1 DURABLE DISPOSABLE TRANSACTION: PASS` reports, pending OMEN verification.

Still required before live approval: a production-safe installation layout (the current installed executable is a regular file; a release symlink alone would not switch it), explicit checked service restart and recovery, bounded authenticated production health probing, backup revalidation, strict owner and permissions, power-loss and interrupted-deployment review, a remediation path for the preview-sync ValueError, and a separate live deployment approval. No real service is modified during this milestone.
