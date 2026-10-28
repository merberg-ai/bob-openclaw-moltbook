"""Bob v0.7.1 responsive navigation shell (development-only).

No API calls, JavaScript, executable controls, authentication or state changes.
Three destinations intentionally preserve the existing Activity Manager routes.
This module is not yet installed or connected to the running v0.6 server.
"""
from __future__ import annotations

from html import escape

NAV_ITEMS = (
    ("/", "Scout & review", "Scout and review"),
    ("/activity", "Published activity", "Published activity"),
    ("/originals", "Original posts", "Original posts"),
)

CSS = """<style>
:root{color-scheme:dark;--ink:#eaf2ff;--muted:#a3b4cd;--bg:#090f1b;--nav:#101c2e;--border:#2b3e5c;--accent:#9dc9ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,Segoe UI,sans-serif}
a{color:var(--accent)}a:focus-visible,summary:focus-visible{outline:3px solid #f9c96f;outline-offset:3px}
.bob-layout{display:grid;grid-template-columns:240px minmax(0,1fr);min-height:100vh}
.bob-sidebar{background:var(--nav);border-right:1px solid var(--border);padding:25px 17px}
.bob-brand{font-weight:800;font-size:1.3rem;margin-bottom:25px}
.bob-brand small{display:block;margin:4px 0;color:var(--muted);font-size:.65rem;letter-spacing:.1em}
.bob-sidebar nav{display:grid;gap:7px}
.bob-sidebar nav a,.bob-mobile nav a{display:block;padding:12px 13px;border-radius:9px;color:var(--ink);text-decoration:none;font-weight:600;font-size:.94rem}
.bob-sidebar nav a:hover,.bob-mobile nav a:hover{background:#253950}
.bob-sidebar nav a[aria-current="page"],.bob-mobile nav a[aria-current="page"]{background:#234263;color:#fff;box-shadow:inset 3px 0 #8dbcf6}
.bob-content{width:100%;max-width:1200px;margin:0 auto;padding:28px 28px 72px;min-width:0}
.bob-mobile{display:none}
.bob-content pre,.bob-content .card{max-width:100%;overflow-wrap:anywhere}
@media(max-width:760px){
 .bob-layout{display:block}
 .bob-sidebar{display:none}
 .bob-mobile{display:block;position:relative;background:var(--nav);border-bottom:1px solid var(--border)}
 .bob-mobile summary{list-style:none;cursor:pointer;font-weight:800;padding:16px 20px;min-height:50px}
 .bob-mobile summary::-webkit-details-marker{display:none}
 .bob-mobile summary::after{content:"Menu";float:right;font-weight:600;color:var(--muted)}
 .bob-mobile[open] summary::after{content:"Close"}
 .bob-mobile nav{display:grid;gap:5px;padding:0 12px 14px}
 .bob-content{padding:20px 14px 58px}
}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style>"""


def navigation(current_path: str) -> str:
    if current_path not in {url for url, _, _ in NAV_ITEMS}:
        raise ValueError("Unknown Bob page route")
    links = []
    for url, label, _ in NAV_ITEMS:
        active = ' aria-current="page"' if url == current_path else ""
        links.append(f'<a href="{url}"{active}>{escape(label)}</a>')
    return "".join(links)


def wrap(title: str, content: str, current_path: str) -> str:
    """Wrap already-escaped, trusted internal page markup in accessible layout.

    Title is untrusted text and escaped; content must be produced by the
    authenticated server's existing escaping/render logic, never user HTML.
    """
    links = navigation(current_path)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>' + escape(title) + ' | Bob Activity Manager</title>'
        + CSS + '</head><body>'
        '<div class="bob-layout">'
        '<aside class="bob-sidebar" aria-label="Primary navigation">'
        '<div class="bob-brand">💀 Bob<small>ACTIVITY MANAGER</small></div>'
        '<nav aria-label="Main">' + links + '</nav></aside>'
        '<div class="bob-mobile"><details><summary>💀 Bob · Activity Manager</summary>'
        '<nav aria-label="Mobile navigation">' + links + '</nav></details></div>'
        '<main class="bob-content" id="main-content">'
        '<h1>' + escape(title) + '</h1>' + content
        + '</main></div></body></html>'
    )
