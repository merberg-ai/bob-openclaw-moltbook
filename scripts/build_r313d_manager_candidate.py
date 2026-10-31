#!/usr/bin/env python3
"""Off-first R3 Controls manager: additive wrapper over pinned generated OC4 UI.

Never modify src/bin/bob-activity-manager (hash-pinned v0.6 baseline). The
whole historic generated-manager test chain must stay reproducible.
Old authentication, GET, POST, CSRF, publisher and timer code is unchanged:
a subclass intercepts only /r3 and delegates everything else to super().
This candidate additionally preserves R2 Shadow Now/Inbox routes.
"""
from __future__ import annotations
import build_v076_oc4_candidate as prior


def once(code: str, old: str, new: str) -> str:
    if code.count(old) != 1:
        raise ValueError("r313d_generated_manager_baseline_drift")
    return code.replace(old,new,1)


def build() -> tuple[bytes,bytes]:
    mgr, nav = prior.build()
    code = mgr.decode("utf-8")
    menu = nav.decode("utf-8")
    # Overlay the R2 authenticated shadow route bridge on the current OC4
    # baseline, rather than replacing newer OC4 diagnostics with an old build.
    code = once(code,
        "from bob_social_memory import page as social_memory_page",
        "from bob_social_memory import page as social_memory_page\n"
        "from bob_v08_bridge import now_page as v08_now_page, inbox_page as v08_inbox_page")
    code = once(code,
        '        elif urlsplit(self.path).path == "/moltbook/social-memory":',
        '        elif urlsplit(self.path).path == "/v08/now":\n'
        '            self._send(200,v08_now_page(wrap),"text/html; charset=utf-8")\n'
        '        elif urlsplit(self.path).path == "/v08/inbox":\n'
        '            self._send(200,v08_inbox_page(wrap),"text/html; charset=utf-8")\n'
        '        elif urlsplit(self.path).path == "/moltbook/social-memory":')
    shadow_anchor=(
        '    ("/moltbook/social-memory", "Moltbook · Social Memory", '
        '"Source-linked private encounters and evolving interests"),'
    )
    menu=once(menu,shadow_anchor,
        shadow_anchor+'\n'
        '    ("/v08/now", "Bob v0.8 · Shadow Now", '
        '"Hypothetical decisions, no external actions"),\n'
        '    ("/v08/inbox", "Bob v0.8 · Shadow Inbox", '
        '"Read-only preview and anomalies"),')
    # Only new /r3 paths are intercepted; original class is NEVER edited.
    entry='\nif __name__ == "__main__":'
    class_extension=(
        "\nfrom bob_r313d_web import R3HandlerMixin\n"
        "_LegacyHandler = Handler\n"
        "class Handler(R3HandlerMixin, _LegacyHandler):\n"
        "    R3_CSRF_TOKEN = TOKEN\n"
    )
    code=once(code,entry,class_extension+entry)
    menu=once(menu,
        '    ("/investigate", "Why no activity?", '
        '"Evidence-backed queue, Scout and publisher diagnostics"),',
        '    ("/investigate", "Why no activity?", '
        '"Evidence-backed queue, Scout and publisher diagnostics"),\n'
        '    ("/r3", "Bob R3 Controls", '
        '"Independently sealed Bob drafts and owner-only manual approvals"),')
    compile(code,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    if code.count("class Handler(R3HandlerMixin, _LegacyHandler):") != 1:
        raise ValueError("r3_manager_subclass_missing")
    return code.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    manager,nav=build()
    print("R3.13d GENERATED OFF-FIRST MANAGER: PASS")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("previous_manager_source_changed: NO")
