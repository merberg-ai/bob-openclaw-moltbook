#!/usr/bin/env python3
"""Build v0.7.2 Settings candidate, starting from reviewed v0.7.1 code.

No production install, credentials, database or network access.
"""
from pathlib import Path
import build_v071_manager_candidate as prior

HERE = Path(__file__).resolve().parents[1]

def build(*, styled=True):
    base, navigation = prior.build()
    source = base.decode("utf-8")
    source = source.replace(
        "from navigation_shell import integrate_existing_html",
        "from navigation_shell import integrate_existing_html, wrap\n"
        "from bob_dashboard_auth import authorized as dashboard_authorized, rotate as dashboard_rotate, CredentialError\n"
        "from bob_live_status import snapshot as status_snapshot",
        1)
    auth_start = source.index("    def _authenticated(self):")
    auth_end = source.index("    def _auth_required(self):", auth_start)
    source = source[:auth_start] + """    def _authenticated(self):
        if LAN_CREDS is None:
            return True
        return dashboard_authorized(LAN_AUTH_FILE, self.headers.get('Authorization', ''))

    def _settings_page(self):
        form = ('<section class="card"><h2>Change dashboard password</h2>'
                '<p>Enter your current password and a new password of at least 20 characters.</p>'
                '<form method="post" action="/settings/password">'
                '<input type="hidden" name="csrf" value="' + esc(TOKEN) + '">'
                '<p><label>Current password <input name="current" type="password" '
                'autocomplete="current-password" required></label></p>'
                '<p><label>New password <input name="new" type="password" '
                'autocomplete="new-password" minlength="20" maxlength="256" required></label></p>'
                '<p><label>Confirm new password <input name="confirm" type="password" '
                'autocomplete="new-password" minlength="20" maxlength="256" required></label></p>'
                '<button type="submit">Change password</button></form>'
                '<p>HTTP Basic authentication may be cached by your browser. '
                'Reopen the site in a private tab if it does not prompt again.</p></section>')
        return wrap("Settings", form, "/settings")

    def _change_password(self):
        if LAN_CREDS is None:
            self._error_page(403, "Unavailable", "LAN authentication is not configured")
            return
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= 2048:
                raise ValueError("Invalid form size")
            form = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            if any(len(form.get(key, [])) != 1 for key in ("csrf", "current", "new", "confirm")):
                raise ValueError("Invalid form")
            if not hmac.compare_digest(form["csrf"][0], TOKEN):
                self._error_page(403, "Request blocked", "Invalid CSRF token")
                return
            dashboard_rotate(LAN_AUTH_FILE, form["current"][0],
                             form["new"][0], form["confirm"][0])
        except (ValueError, UnicodeError, OSError, CredentialError):
            self._error_page(400, "Password unchanged", "Check current password and new password requirements")
            return
        self._send(200, "Password updated. Open a private browser tab to sign in again.")

""" + source[auth_end:]
    anchor = '        elif self.path == "/originals":\n'
    if source.count(anchor) != 1:
        raise ValueError("GET route changed")
    source = source.replace(anchor, '''        elif self.path == "/settings":
            self._send(200, self._settings_page(), "text/html; charset=utf-8")
''' + anchor, 1)
    anchor = '        path = urlsplit(self.path).path\n'
    if source.count(anchor) != 1:
        raise ValueError("POST route changed")
    source = source.replace(anchor, '''        path = urlsplit(self.path).path
        if path == "/settings/password":
            self._change_password()
            return
''', 1)
    anchor = '        elif self.path == "/settings":\n'
    if source.count(anchor) != 1:
        raise ValueError("settings route changed")
    source = source.replace(anchor, '''        elif self.path == "/api/system/status":
            self._send(200, json.dumps(status_snapshot()), "application/json")
        elif self.path == "/system/status":
            report = status_snapshot()
            content = '<section class="card"><h2>Live service status</h2><p>Updates every 10 seconds. Service active does not guarantee readiness.</p><ul>'
            for item in report["services"]:
                content += "<li><strong>" + esc(item["name"]) + "</strong>: " + esc(item["state"]) + "</li>"
            content += '</ul></section><section class="card"><h2>Recent recorded jobs</h2>'
            if not report["queue"]["available"]:
                content += "<p>Queue records unavailable. No state inferred.</p>"
            elif not report["queue"]["jobs"]:
                content += "<p>No recent queue records.</p>"
            else:
                content += "<ul>"
                for job in report["queue"]["jobs"]:
                    content += "<li>" + esc(job["kind"]) + ": <strong>" + esc(job["state"]) + "</strong> · " + esc(job["created"]) + "</li>"
                content += "</ul>"
            content += "</section>"
            page = wrap("System status", content, "/system/status")
            page = page.replace("</head>", '<meta http-equiv="refresh" content="10"></head>', 1)
            self._send(200, page, "text/html; charset=utf-8")
''' + anchor, 1)
    nav = navigation.decode("utf-8")
    anchor = '    ("/originals", "Original posts", "Original posts"),'
    if nav.count(anchor) != 1:
        raise ValueError("navigation changed")
    nav = nav.replace(anchor, anchor + '\n    ("/system/status", "System status", "System status"),\n    ("/settings", "Settings", "Settings"),', 1)
    # v0.7.1 was deployed with v0.6 labels inherited from the pinned source.
    # Replace every legacy version label for this v0.7.2 release.
    if source.count("v0.6") != 6:
        raise ValueError("legacy manager version markers drifted")
    source = source.replace("v0.6", "v0.7.2")
    if styled:
        # Only the Settings markup changes. styled=False reproduces the precise
        # v0.7.2 manager already installed on the operator's host.
        begin = source.index("    def _settings_page(self):")
        end = source.index("    def _change_password(self):", begin)
        fragment = source[begin:end]
        css = ('.bob-settings{max-width:690px;padding:clamp(18px,4vw,30px);'
               'margin:0 auto 24px;background:#142238;border:1px solid #304766;'
               'border-radius:16px;box-shadow:0 12px 36px #0003}'
               '.bob-settings h2{font-size:clamp(1.2rem,3.5vw,1.55rem);margin:0 0 10px}'
               '.bob-settings p{color:#b9cbe2;line-height:1.5}'
               '.bob-settings-form{display:grid;gap:18px;margin:22px 0}'
               '.bob-settings-field{display:grid;gap:8px;min-width:0}'
               '.bob-settings-field label{font-size:.94rem;font-weight:700;color:#e6efff}'
               '.bob-settings-field input{display:block;width:100%;min-width:0;'
               'max-width:100%;min-height:50px;padding:12px 14px;border-radius:10px;'
               'border:1px solid #54749a;background:#0b1727;color:#f0f6ff;'
               'font:inherit;box-sizing:border-box}'
               '.bob-settings-field input:focus-visible{outline:3px solid #86bdff;'
               'outline-offset:2px;border-color:#8cbfff}'
               '.bob-settings-form button{cursor:pointer;min-height:49px;'
               'padding:13px 20px;background:#295f9b;border:1px solid #7ab4f7;'
               'color:white;font-weight:700;font:inherit;border-radius:10px;'
               'max-width:100%;width:fit-content}'
               '.bob-settings-form button:hover{background:#3574b5}'
               '@media(max-width:600px){.bob-settings{padding:18px 14px;'
               'margin:0;border-radius:12px}.bob-settings-form button{width:100%}}')
        fragment = fragment.replace(
            '<section class="card"><h2>Change dashboard password</h2>',
            '<style>' + css + '</style><section class="card bob-settings"><h2>Change dashboard password</h2>', 1)
        fragment = fragment.replace(
            '<form method="post" action="/settings/password">',
            '<form class="bob-settings-form" method="post" action="/settings/password">', 1)
        for field, label in (("current", "Current password"), ("new", "New password"),
                             ("confirm", "Confirm new password")):
            expected = '<p><label>' + label + ' <input name="' + field + '"'
            desired = ('<div class="bob-settings-field"><label for="bob-' + field
                       + '">' + label + '</label><input id="bob-' + field + '" name="' + field + '"')
            if fragment.count(expected) != 1:
                raise ValueError("Settings form field changed: " + field)
            fragment = fragment.replace(expected, desired, 1)
        if fragment.count('required></label></p>') != 3:
            raise ValueError("Settings form close tags changed")
        fragment = fragment.replace('required></label></p>', 'required></div>', 3)
        source = source[:begin] + fragment + source[end:]
    compile(source, "bob-activity-manager", "exec")
    compile(nav, "navigation_shell.py", "exec")
    return source.encode("utf-8"), nav.encode("utf-8")

if __name__ == "__main__":
    manager, nav = build()
    print("v0.7.2 SETTINGS CANDIDATE: PASS")
    print("manager_bytes:", len(manager), "navigation_bytes:", len(nav))
    print("production_modified: NO")
