# v0.7.0: Review source staging warnings safely

The private snapshot of installed Bob source was successfully created on October 28, 2026: **9 files**, **118,661 bytes**, all matching the original inventory fingerprints. The scanner reported **two potential secret indicators**. These are unverified heuristic findings, not proof that credentials were embedded.

Do not upload the tarball, copy its contents into a public issue, or import any of it into GitHub yet.

## Run redacted audit from Windows PowerShell

~~~powershell
wsl -d OpenClawLab -u openclaw -- bash -lc "cd ~/bob-v070-inventory && git pull --ff-only && python3 scripts/audit_staged_sources.py"
~~~

The audit reads the newest locally staged Bob archive. It verifies archive members against the embedded SHA-256 manifest. It outputs **only** relative filenames, line numbers and a broad indicator type, for example:

~~~text
Source files checked: 9
Potential secret indicators: 2
bin/bobctl:123: credential-like literal assignment (direct Python string literal)
lib/bob/bob_moltbook_api.py:45: credential-shaped token or private-key marker (embedded in Python string text)
No matched strings, source text, or credentials were printed.
DO NOT publish the raw source archive. Manual review still required.
~~~

Those locations are **examples**, not actual findings. The tool also labels each finding by basic Python syntax context: a **direct string literal**, **string embedded in text**, **comment**, or **other source expression**. This is only a lexical hint and does not establish that any value is safe or unsafe. It does not print the flagged values, source lines, system configuration, credentials, or absolute host paths. It does not change the live host or contact any external service.

The location-only output is appropriate to paste in the project chat for review. The archive itself **must remain private** until the flagged lines and surrounding code have been reviewed by the operator, and any secrets have been rotated and removed from the *sanitized* public source. A match can be harmless test data or a false positive. A clean audit is not proof that code contains no sensitive information.

If the audit fails, do not force it or upload the archive. The snapshot may have changed or may not match its manifest.

## After locating the findings

1. Determine if flagged lines are actual credential values, placeholders, or harmless test examples through a local review without pasting the values.
2. If a real credential has ever been embedded, plan to rotate that credential and replace its usage with safe runtime configuration. **Do not edit the running host during the baseline phase.**
3. Check for any unflagged sensitive material before public source import.
4. Document source-vs-v0.6 differences and coverage of other installed files, separately from private credentials.
5. Prepare sanitized code and tests on a development branch. Never commit this raw private archive.
