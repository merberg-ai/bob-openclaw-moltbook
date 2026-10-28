# v0.7.0 Phase 4: Private source review

The nine installed source files have been captured into a private SHA-verified archive, and the live SQLite backup passed its isolated restore rehearsal. Two original secret-shape matches in bob-lan-config were confirmed by the operator to be **runtime reads of a LAN password**, not hardcoded passwords. The helper still *prints* that secret and needs staged hardening (issue #3).

**Never publish the raw source archive.** This step reads the archive locally and prints redacted source findings only. It does not upload or import code, run Bob's code, restart services, access Moltbook, or change authentication.

## One PowerShell command from the remote Windows desktop

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git pull --ff-only && python3 scripts/review_staged_sources.py"
~~~

Expected output includes source count, script languages, prior scanner findings, possible non-stdlib Python imports, and file/line flags for credential output, literal assignments, IP addresses, machine paths and dynamic execution.

Example (illustrative only):

~~~text
Snapshot verified. Source files: 9
Script languages: python=9
Prior heuristic flags: 2 (already reviewed separately)
Possible non-stdlib modules: requests
Additional static review findings: 2
bin/bob-lan-config:39: possible credential-related stdout
bin/bob-lan-config:44: possible credential-related stdout
~~~

No source code lines, passwords, literal string contents, DB rows or tokens are printed. It does display import module names and relative source filenames; review before posting to public channels. Never upload the raw tarball or private SQLite database.

Static heuristics are not proof that a file is safe to publish. Dynamic imports, subprocess dependencies, Windows launch scripts, service file contents and additional installed code still require follow-up review.

After this review, prepare a manually sanitized source candidate, ensure the LAN password isn't echoed by default, add legacy regression tests, and import only vetted code to GitHub. Keep the running host unchanged until staging rollback is proven.
