#!/usr/bin/env python3
"""PM2.3 guarded recall controls atop PM2.2b; no old handler replacements."""
from __future__ import annotations
import build_v073_pm22b_ai_candidate as prior


def once(src,old,new):
    if src.count(old)!=1:
        raise ValueError("PM2.3 manager baseline drift")
    return src.replace(old,new,1)


def build():
    manager,nav=prior.build()
    source=manager.decode("utf-8")
    menu=nav.decode("utf-8")
    source=once(
        source,
        "from bob_memory_ai import page as ai_memory_page, dispatch as ai_memory_dispatch, "
        "worker as ai_memory_worker, safe_error as ai_memory_safe_error",
        "from bob_memory_ai import page as ai_memory_page, dispatch as ai_memory_dispatch, "
        "worker as ai_memory_worker, safe_error as ai_memory_safe_error\n"
        "from bob_memory_recall import page as recall_page, change as recall_change, "
        "safe_error as recall_safe_error")
    source=once(
        source,
        '        elif urlsplit(self.path).path == "/mind/memory/ai":',
        '''        elif urlsplit(self.path).path == "/mind/recall":
            with publish_conn() as db:
                self._send(200, recall_page(db, TOKEN, wrap,
                    parse_qs(urlsplit(self.path).query,keep_blank_values=True)),
                    "text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/mind/memory/ai":''')
    source=once(
        source,
        '        if path == "/mind/memory/ai":',
        '''        if path == "/mind/recall":
            self._save_recall()
            return
        if path == "/mind/memory/ai":''')
    method='''    def _save_recall(self):
        if not self._valid_origin():
            self._error_page(403,"Request blocked","Origin check failed")
            return
        try:
            size=int(self.headers.get("Content-Length","-1"))
            if not 0<size<=2048:
                raise ValueError("Invalid recall settings form")
            values=parse_qs(self.rfile.read(size).decode("utf-8"),
                            keep_blank_values=True,max_num_fields=6)
            if any(len(v)!=1 for v in values.values()):
                raise ValueError("Invalid recall settings form")
            if not hmac.compare_digest(values.get("csrf",[""])[0],TOKEN):
                self._error_page(403,"Request blocked","Invalid CSRF token")
                return
            form={k:v[0] for k,v in values.items()}
            with publish_conn() as db:
                recall_change(db,form)
            self.send_response(303)
            self.send_header("Location","/mind/recall")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
            self._error_page(409,"Recall setting unchanged",recall_safe_error(exc))

'''
    source=once(source,'    def _save_ai_memory(self):',
                method+'    def _save_ai_memory(self):')
    source=once(
        source,
        '"/mind/memory/ai" if urlsplit(self.path).path == "/mind/memory/ai"',
        '"/mind/recall" if urlsplit(self.path).path == "/mind/recall" '
        'else "/mind/memory/ai" if urlsplit(self.path).path == "/mind/memory/ai"')
    nav_anchor='    ("/mind/memory/ai", "Bob\'s Mind · AI ideas", "Review locally generated memory proposals"),'
    menu=once(menu,nav_anchor,nav_anchor+'\n'
              '    ("/mind/recall", "Bob\'s Mind · Recall", "Private contextual recall permissions and preview"),')
    compile(source,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return source.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    manager,nav=build()
    print("PM2.3 OPT-IN RECALL CANDIDATE: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("production_modified: NO")
