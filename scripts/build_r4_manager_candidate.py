#!/usr/bin/env python3
"""One composed R4 Manager over accepted CH-HTTPS3/R3/R2/legacy routing.

Never patch the old pinned manager or its prior generated-builder chain.
R4 wraps the *existing* authenticated, TLS-only Handler as the outermost
route extension, delegating every unrecognized route unchanged.
"""
from __future__ import annotations
import build_ch_https3_manager_candidate as prior


def once(code: str, old: str, new: str) -> str:
    if code.count(old)!=1:
        raise ValueError("r4_generated_manager_baseline_drift")
    return code.replace(old,new,1)


def build() -> tuple[bytes,bytes]:
    manager,nav=prior.build()
    code=manager.decode("utf-8")
    menu=nav.decode("utf-8")
    extension=(
        "\nfrom bob_r4_web import R4HandlerMixin\n"
        "_R4PreviousHandler = Handler\n"
        "class Handler(R4HandlerMixin, _R4PreviousHandler):\n"
        "    R4_CSRF_TOKEN = TOKEN\n"
    )
    code=once(code,'\nif __name__ == "__main__":',
              extension+'\nif __name__ == "__main__":')
    # R4 appears as one clear high-level link, internal tabs own subnavigation.
    menu=once(menu,
        '    ("/r3", "Bob R3 Controls", '
        '"Independently sealed Bob drafts and owner-only manual approvals"),',
        '    ("/r3", "Bob R3 Controls", '
        '"Independently sealed Bob drafts and owner-only manual approvals"),\n'
        '    ("/r4/now", "Bob R4 · Autonomy", '
        '"Unified activity, Inbox, personality, relationships and owner policy"),')
    if (code.count('class Handler(R4HandlerMixin, _R4PreviousHandler):')!=1
            or "serve_tls(Handler, HOST, PORT)" not in code
            or 'class Handler(HTTPSOnlyHandlerMixin, _CH1Handler):' not in code
            or menu.count('("/r4/now", "Bob R4 · Autonomy"')!=1):
        raise ValueError("r4_manager_tls_or_routes_untrusted")
    compile(code,"bob-activity-manager","exec")
    compile(menu,"navigation_shell.py","exec")
    return code.encode("utf-8"),menu.encode("utf-8")


if __name__=="__main__":
    manager,nav=build()
    print("R4 CONSOLIDATED HTTPS MANAGER: BUILT")
    print("manager_bytes:",len(manager),"navigation_bytes:",len(nav))
    print("legacy route source or credentials changed: NO")
