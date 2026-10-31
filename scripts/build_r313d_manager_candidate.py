#!/usr/bin/env python3
"""Off-first R3 Controls manager: additive wrapper over pinned generated OC4 UI.

Never modify src/bin/bob-activity-manager (hash-pinned v0.6 baseline). The
whole historic generated-manager test chain must stay reproducible.
Old authentication, GET, POST, CSRF, publisher and timer code is unchanged:
a subclass intercepts only /r3 and delegates everything else to super().
This candidate additionally preserves R2 Shadow Now/Inbox routes.
"""
from __future__ import annotations
import build_v08_shadow_dashboard as prior


def once(code: str, old: str, new: str) -> str:
    if code.count(old) != 1:
        raise ValueError("r313d_generated_manager_baseline_drift")
    return code.replace(old,new,1)


def build() -> tuple[bytes,bytes]:
    mgr, nav = prior.build()
    code = mgr.decode("utf-8")
    menu = nav.decode("utf-8")
    # The pinned R2 bridge ALREADY builds FM4.1 on OC4 and preserves all
    # old dashboard handlers. Never add its GET routes twice.
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
