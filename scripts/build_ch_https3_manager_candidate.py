#!/usr/bin/env python3
"""CH-HTTPS3 source-only TLS Manager candidate over reviewed R3.13d build.

The installed pinned manager and prior R2/R3 generated chain are unchanged.
Only the newly generated candidate introduces TLS-only transport/origins.
Not promoted to releases/current.json until explicit Windows CA trust gate.
"""
from __future__ import annotations
import build_r313d_manager_candidate as prior


def replace_once(code: str, old: str, new: str) -> str:
    if code.count(old)!=1:
        raise ValueError("ch_https3_manager_baseline_drift")
    return code.replace(old,new,1)


def build() -> tuple[bytes,bytes]:
    old, nav=prior.build()
    code=old.decode("utf-8")
    entry='\nif __name__ == "__main__":'
    tls_mixin=(
        '\nfrom bob_manager_tls import HTTPSOnlyHandlerMixin, serve_tls\n'
        '_CH1Handler = Handler\n'
        'class Handler(HTTPSOnlyHandlerMixin, _CH1Handler):\n'
        '    pass\n'
    )
    code=replace_once(code,entry,tls_mixin+entry)
    code=replace_once(
        code,
        '    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()',
        '    serve_tls(Handler, HOST, PORT)')
    if (code.count("class Handler(HTTPSOnlyHandlerMixin, _CH1Handler):")!=1
            or code.count("    serve_tls(Handler, HOST, PORT)")!=1
            or "ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()" in code):
        raise ValueError("ch_https3_tls_only_wiring_refused")
    compile(code,"bob-activity-manager","exec")
    return code.encode("utf-8"),nav


if __name__=="__main__":
    manager,nav=build()
    print("CH-HTTPS3 SOURCE-ONLY TLS MANAGER CANDIDATE: BUILT")
    print("generated manager bytes:",len(manager))
    print("unchanged navigation bytes:",len(nav))
    print("installed manager/release files changed: NONE")
    print("TLS switch authorized: NO")
