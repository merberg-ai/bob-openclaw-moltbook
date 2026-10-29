#!/usr/bin/env python3
"""FM1: add privately curated Friends route without altering existing handlers."""
from __future__ import annotations
import build_v073_pm23_recall_candidate as prior


def once(src,old,new):
    if src.count(old)!=1:
        raise ValueError("FM1 baseline mismatch; refuse generated manager")
    return src.replace(old,new,1)


def build():
    manager,nav=prior.build()
    src=manager.decode("utf-8")
    menu=nav.decode("utf-8")
    src=once(
        src,
        "from bob_memory_recall import page as recall_page, change as recall_change, "
        "safe_error as recall_safe_error",
        "from bob_memory_recall import page as recall_page, change as recall_change, "
        "safe_error as recall_safe_error\n"
        "from bob_friends import page as friends_page, dispatch as friends_dispatch, "
        "safe_error as friends_safe_error")
    src=once(src,
        '        elif urlsplit(self.path).path == "/mind/recall":',
        '''        elif urlsplit(self.path).path == "/moltbook/friends":
            with publish_conn() as db:
                self._send(200, friends_page(db,TOKEN,wrap,
                    parse_qs(urlsplit(self.path).query,keep_blank_values=True),
                    load_records()),"text/html; charset=utf-8")
        elif urlsplit(self.path).path == "/mind/recall":''')
    src=once(src,
        '        if path == "/mind/recall":',
        '''        if path == "/moltbook/friends":
            self._save_friend()
            return
        if path == "/mind/recall":''')
    method='''    def _save_friend(self):
        if not self._valid_origin():
            self._error_page(403,"Request blocked","Origin check failed")
            return
        try:
            length=int(self.headers.get("Content-Length","-1"))
            if not 0<length<=10000:
                raise ValueError("Invalid friend form")
            values=parse_qs(self.rfile.read(length).decode("utf-8"),
                            keep_blank_values=True,max_num_fields=11)
            if any(len(v)!=1 for v in values.values()):
                raise ValueError("Invalid friend form")
            if not hmac.compare_digest(values.get("csrf",[""])[0],TOKEN):
                self._error_page(403,"Request blocked","Invalid CSRF token")
                return
            form={k:v[0] for k,v in values.items()}
            with publish_conn() as db:
                friend_id=friends_dispatch(db,form)
            self.send_response(303)
            self.send_header("Location","/moltbook/friends?edit="+friend_id)
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length","0")
            self.end_headers()
        except (ValueError,TypeError,UnicodeError,OSError,sqlite3.Error) as exc:
            self._error_page(409,"Friend record unchanged",friends_safe_error(exc))

'''
    src=once(src,'    def _save_recall(self):',
             method+'    def _save_recall(self):')
    # Preserve the exact old error path behavior for other sections.
    src=once(src,
        '"/mind/recall" if urlsplit(self.path).path == "/mind/recall"',
        '"/moltbook/friends" if urlsplit(self.path).path == "/moltbook/friends" '
        'else "/mind/recall" if urlsplit(self.path).path == "/mind/recall"')
    nav_anchor='    ("/mind/recall", "Bob\'s Mind · Recall", "Private contextual recall permissions and preview"),'
    menu=once(menu,nav_anchor,nav_anchor+'\n'
              '    ("/moltbook/friends", "Moltbook · Friends", '
              '"Private contacts, interests and relationship notes"),')
    compile(src,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return src.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    m,n=build()
    print("FM1 PRIVATE FRIENDS CANDIDATE: PASS")
    print("manager_bytes:",len(m),"navigation_bytes:",len(n))
    print("production_modified: NO")
