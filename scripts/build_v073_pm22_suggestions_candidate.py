#!/usr/bin/env python3
"""PM2.2 review inbox over current installed PM2.1, source-only guarded builder."""
from __future__ import annotations
import build_v073_pm2_memory_candidate as prior


def once(text,old,new):
    if text.count(old)!=1:
        raise ValueError("PM2.2 dashboard baseline drift")
    return text.replace(old,new,1)


def build():
    manager,nav=prior.build()
    source=manager.decode("utf-8")
    navigation=nav.decode("utf-8")
    source=once(
        source,
        "from bob_memory import page as memory_page, dispatch as memory_dispatch, safe_error as memory_safe_error",
        "from bob_memory import page as memory_page, dispatch as memory_dispatch, safe_error as memory_safe_error\n"
        "from bob_memory_suggestions import page as suggestion_page, dispatch as suggestion_dispatch, "
        "safe_error as suggestion_safe_error")
    source=once(
        source,
        '        elif urlsplit(self.path).path == "/mind/memory":',
        '''        elif urlsplit(self.path).path == "/mind/memory/suggestions":
            with publish_conn() as db:
                self._send(200, suggestion_page(db, TOKEN, wrap, load_records()),
                           "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/mind/memory":''')
    source=once(
        source,
        '        if path == "/mind/memory":',
        '''        if path == "/mind/memory/suggestions":
            self._save_memory_suggestion()
            return
        if path == "/mind/memory":''')
    handler='''    def _save_memory_suggestion(self):
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            size=int(self.headers.get("Content-Length","-1"))
            if not 0<size<=8192:
                raise ValueError("Invalid suggestion form")
            values=parse_qs(self.rfile.read(size).decode("utf-8"),
                            keep_blank_values=True,max_num_fields=11)
            if any(len(v)!=1 for v in values.values()):
                raise ValueError("Invalid suggestion form")
            if not hmac.compare_digest(values.get("csrf",[""])[0],TOKEN):
                self._error_page(403,"Request blocked","Invalid CSRF token")
                return
            form={k:v[0] for k,v in values.items()}
            with publish_conn() as db:
                suggestion_dispatch(db,form)
            self.send_response(303)
            self.send_header("Location","/mind/memory/suggestions")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
            self._error_page(409,"Suggestion unchanged",suggestion_safe_error(exc))

'''
    source=once(source,'    def _save_memory(self):',
                handler+'    def _save_memory(self):')
    # Extend only the Memory-specific return navigation and footer.
    source=once(
        source,
        'urlsplit(self.path).path == "/mind/memory" else "No review decision was changed."',
        'urlsplit(self.path).path.startswith("/mind/memory") else "No review decision was changed."')
    source=once(
        source,
        '"/mind/memory" if urlsplit(self.path).path == "/mind/memory"',
        '"/mind/memory/suggestions" if urlsplit(self.path).path == "/mind/memory/suggestions" '
        'else "/mind/memory" if urlsplit(self.path).path == "/mind/memory"')
    nav_anchor='    ("/mind/memory", "Bob\'s Mind · Memory", "Private curated memory manager"),'
    navigation=once(navigation,nav_anchor,nav_anchor+'\n'
                    '    ("/mind/memory/suggestions", "Bob\'s Mind · Suggestions", '
                    '"Review proposed memories from verified Scout work"),')
    # Inline link from Memory UI? No patching of the existing audited memory
    # module; navigation is shared with desktop and mobile.
    compile(source,"bob-activity-manager","exec")
    compile(navigation,"navigation_shell.py","exec")
    return source.encode("utf-8"),navigation.encode("utf-8")


if __name__=="__main__":
    m,n=build()
    print("PM2.2 SCOUT SUGGESTIONS CANDIDATE: PASS")
    print("manager_bytes:",len(m),"navigation_bytes:",len(n))
    print("production_modified: NO")
