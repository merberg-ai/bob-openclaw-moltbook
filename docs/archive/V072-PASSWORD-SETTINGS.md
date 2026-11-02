# v0.7.2 Password Settings, implementation status

First increment committed: `src/lib/bob/bob_dashboard_auth.py` and `tests/test_bob_dashboard_auth.py`.

The credential backend reads the existing private `~/.config/bob-system/lan-auth.json` on each request and implements a lock-protected fsynced atomic password replacement preserving other keys and the username. It rejects incorrect current credentials, weak or malformed replacements, symlinks and unsafe file permissions; any authentication read error denies rather than grants access.

This first increment **does not yet integrate** the new auth module into the Activity Manager, expose a Settings page, or change production credentials. Do not invoke its functions against the live auth file as a manual rotation shortcut.

Next: integrate the module into the currently deployed v0.7.1 candidate source, add GET /settings and CSRF-protected POST /settings/password (same-origin check, bounded request, verified current password, no-store), and extend the navigation. Test both the new browser flow and a staged service restart before a separate v0.7.2 release.

Basic authentication is cached by desktop and phone browsers. A password change can invalidate the old password server-side, but browsers may require a new private browsing session or clearing site credentials to prompt again. The LAN HTTP service transmits the Basic credential without TLS; restrict to a trusted LAN or VPN or use HTTPS.
