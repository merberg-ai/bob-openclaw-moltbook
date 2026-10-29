#!/usr/bin/env python3
"""Integrate PM1 guarded SOUL.md apply/rollback into existing dashboard.

Reviewed builder layering: only one page renderer substitution, two POST
routes, and one protected method. Other publishing and approval methods intact.
"""
from __future__ import annotations
import build_v073_pm1_csp_candidate as prior


def once(source,old,new):
    if source.count(old)!=1:
        raise ValueError("PM1 apply integration baseline drift")
    return source.replace(old,new,1)


def build():
    manager,nav=prior.build()
    source=manager.decode("utf-8")
    source=once(source,
        "store_profile as personality_store, KEYS as personality_keys",
        "store_profile as personality_store, KEYS as personality_keys\n"
        "from bob_personality_apply import page as personality_apply_page, "
        "apply as personality_apply, rollback as personality_rollback")
    source=once(source,
        "self._send(200, personality_page(db, TOKEN, wrap), \"text/html; charset=utf-8\")",
        "self._send(200, personality_apply_page(db, TOKEN, wrap), \"text/html; charset=utf-8\")")
    source=once(source,
        '''        if path == "/mind/personality":
            self._save_personality()
            return''',
        '''        if path in ("/mind/personality/apply", "/mind/personality/rollback"):
            self._apply_personality(path)
            return
        if path == "/mind/personality":
            self._save_personality()
            return''')
    extra = '''    def _apply_personality(self, path):
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            length=int(self.headers.get("Content-Length","-1"))
            if not 0 < length <= 4096:
                raise ValueError("Invalid personality form size")
            form=parse_qs(self.rfile.read(length).decode("utf-8"),
                          keep_blank_values=True,max_num_fields=5)
            if any(len(values)!=1 for values in form.values()):
                raise ValueError("Duplicate personality form field")
            if not hmac.compare_digest(form.get("csrf",[""])[0],TOKEN):
                self._error_page(403,"Request blocked","Invalid CSRF token")
                return
            if path == "/mind/personality/apply":
                if set(form)!={"csrf","expected_before","expected_profile","confirmation"}:
                    raise ValueError("Unexpected Apply fields")
                with publish_conn() as db:
                    personality_apply(db,form["expected_before"][0],
                        form["expected_profile"][0],form["confirmation"][0])
            else:
                if set(form)!={"csrf","expected_sha","confirmation"}:
                    raise ValueError("Unexpected rollback fields")
                personality_rollback(form["confirmation"][0],form["expected_sha"][0])
            self.send_response(303)
            self.send_header("Location","/mind/personality")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
            # Error messages reveal no file contents, credentials or backup paths.
            self._error_page(409,"Personality not applied",str(exc)[:240])

'''
    source=once(source,'    def _save_personality(self):',
                extra+'    def _save_personality(self):')
    compile(source,"bob-activity-manager","exec")
    compile(nav,"navigation_shell.py","exec")
    return source.encode("utf-8"),nav


if __name__=="__main__":
    a,b=build()
    print("PM1 GUARDED APPLY CANDIDATE: PASS")
    print("manager_bytes:",len(a),"navigation_bytes:",len(b))
    print("production_modified: NO")
