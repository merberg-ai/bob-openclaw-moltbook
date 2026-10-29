# v0.7.1 read-only directive inventory

Operator confirmed 150 tests and effective unit inspection. `EnvironmentFiles`, `ExecStartPre`, `ExecStartPost`, and `ExecCondition` were omitted by the installed systemd version. The previous inspection therefore correctly returned UNKNOWN rather than guessing.

Run from PowerShell:

```powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v071-preview && git pull --ff-only && python3 -m unittest discover -s tests -p 'test_*.py' -q && python3 scripts/inspect_v071_unit_directives.py"
```

This reads `systemctl --user cat bob-activity-manager.service` *locally only*. Its output is a fixed, redacted classification of whether the unit and drop-ins contain relevant directives. It never prints the contents, paths or secret-bearing values. It does not install, start, stop, reload or restart services.

A YES means the directive appears in source; a NO means the parser did not find it in that output. A blank/reset directive produces UNKNOWN because combined configuration precedence may matter. These are **source-presence classifications, not proof of final systemd effective values**; the service may also use wrappers, specifiers and generated/transient settings. On unexpected/malformed output, the tool refuses.

After this gate, design a versioned candidate updater with *separate, explicit production approval*. Continue preserving the working directory, inline environment, drop-ins and original executable/SQLite state. The existing review ZIP stays non-deployable.
