#!/usr/bin/env python3
"""Add an explicit, bounded local-only Ollama proposal pipeline to PM2.2a."""
from __future__ import annotations
import build_v073_pm22_suggestions_candidate as prior


def once(src,old,new):
    if src.count(old)!=1:
        raise ValueError("PM2.2b baseline mismatch; refusing generated manager")
    return src.replace(old,new,1)


def build():
    manager,nav=prior.build()
    src=manager.decode("utf-8")
    menu=nav.decode("utf-8")
    src=once(src,
        "from bob_memory_suggestions import page as suggestion_page, dispatch as suggestion_dispatch, safe_error as suggestion_safe_error",
        "from bob_memory_suggestions import page as suggestion_page, dispatch as suggestion_dispatch, safe_error as suggestion_safe_error\n"
        "from bob_memory_ai import page as ai_memory_page, dispatch as ai_memory_dispatch, "
        "worker as ai_memory_worker, safe_error as ai_memory_safe_error")
    src=once(src,
        "from bob_memory_ai import page as ai_memory_page, dispatch as ai_memory_dispatch, "
        "worker as ai_memory_worker, safe_error as ai_memory_safe_error",
        "from bob_memory_ai import page as ai_memory_page, dispatch as ai_memory_dispatch, "
        "worker as ai_memory_worker, safe_error as ai_memory_safe_error\n"
        "import threading")
    src=once(src,
        '        elif urlsplit(self.path).path == "/mind/memory/suggestions":',
        '''        elif urlsplit(self.path).path == "/mind/memory/ai":
            with publish_conn() as db:
                self._send(200, ai_memory_page(db, TOKEN, wrap, load_records()),
                           "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/mind/memory/suggestions":''')
    src=once(src,
        '        if path == "/mind/memory/suggestions":',
        '''        if path == "/mind/memory/ai":
            self._save_ai_memory()
            return
        if path == "/mind/memory/suggestions":''')
    method='''    def _save_ai_memory(self):
        if not self._valid_origin():
            self._error_page(403, "Request blocked", "Origin check failed")
            return
        try:
            size=int(self.headers.get("Content-Length","-1"))
            if not 0<size<=8192:
                raise ValueError("Invalid AI review form")
            values=parse_qs(self.rfile.read(size).decode("utf-8"),
                            keep_blank_values=True,max_num_fields=12)
            if any(len(v)!=1 for v in values.values()):
                raise ValueError("Invalid AI review form")
            if not hmac.compare_digest(values.get("csrf",[""])[0],TOKEN):
                self._error_page(403,"Request blocked","Invalid CSRF token")
                return
            form={k:v[0] for k,v in values.items()}
            with publish_conn() as db:
                outcome,is_job=ai_memory_dispatch(db,form)
            # New worker runs only after the guarded database transaction has
            # committed; it opens its own connection and has no publish tools.
            if is_job:
                threading.Thread(target=ai_memory_worker,
                    args=(outcome,publish_conn),daemon=True,
                    name="bob-memory-ai").start()
            self.send_response(303)
            self.send_header("Location","/mind/memory/ai")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
            self._error_page(409,"AI proposal unchanged",ai_memory_safe_error(exc))

'''
    src=once(src,'    def _save_memory_suggestion(self):',
             method+'    def _save_memory_suggestion(self):')
    # All the inherited authentication and publication handlers stay intact.
    src=once(src,
        '"/mind/memory/suggestions" if urlsplit(self.path).path == "/mind/memory/suggestions"',
        '"/mind/memory/ai" if urlsplit(self.path).path == "/mind/memory/ai" '
        'else "/mind/memory/suggestions" if urlsplit(self.path).path == "/mind/memory/suggestions"')
    anchor='    ("/mind/memory/suggestions", "Bob\'s Mind · Suggestions", "Review proposed memories from verified Scout work"),'
    menu=once(menu,anchor,anchor+'\n'
        '    ("/mind/memory/ai", "Bob\'s Mind · AI ideas", "Review locally generated memory proposals"),')
    compile(src,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return src.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    manager,navigation=build()
    print("PM2.2b LOCAL AI MEMORY CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(navigation))
    print("production_modified: NO")
