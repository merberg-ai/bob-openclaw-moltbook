"""Status page presentation: HTML escaped, read-only, separately loaded same-origin JS."""
from __future__ import annotations
from html import escape
from navigation_shell import wrap

STYLE = """<style>
.bob-status{display:grid;gap:18px}
.bob-status-intro{color:#b9cce7;line-height:1.5}
.bob-status-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:12px}
.bob-status-card{border:1px solid #334b6a;border-radius:12px;background:#16253a;padding:16px;min-width:0}
.bob-status-card strong{display:block;font-size:1rem;margin-bottom:9px}
.bob-status-state{display:inline-flex;align-items:center;gap:7px;border-radius:999px;
 background:#28374a;color:#d7e6f7;padding:6px 11px;font-weight:700;font-size:.85rem}
.bob-status-state[data-tone="good"]{background:#173f37;color:#a3f5d3}
.bob-status-state[data-tone="warn"]{background:#4a3519;color:#f8d99b}
.bob-status-state[data-tone="bad"]{background:#4a2530;color:#ffb5c1}
.bob-status-state[data-tone="idle"]{background:#2a3547;color:#c6d4e8}
.bob-status-state[data-tone="busy"]{background:#17334c;color:#b6e1ff}
.bob-status-state[data-tone="busy"]::before{content:"";width:9px;height:9px;
 border:2px solid #8ccfff;border-top-color:transparent;border-radius:50%;
 animation:bob-status-spin .85s linear infinite}
@keyframes bob-status-spin{to{transform:rotate(360deg)}}
.bob-status-table{list-style:none;padding:0;display:grid;gap:9px}
.bob-status-worker small{display:block;color:#aabed6;margin-top:8px;overflow-wrap:anywhere}
.bob-status-warning{color:#f8d99b;font-size:.82rem;font-weight:650}
.bob-status-job{display:flex;justify-content:space-between;gap:10px;align-items:center;
 background:#122035;border:1px solid #2e425f;border-radius:10px;padding:12px}
.bob-status-job>div{min-width:0;overflow-wrap:anywhere}
.bob-status-job small{display:block;color:#aabed6}
.bob-status-panel{padding:18px;border-radius:14px;border:1px solid #334b6a;background:#101d30}
.bob-status-panel h2{margin:0 0 14px}
.bob-status-last{color:#b8cbe3;font-size:.9rem}
.bob-status-controls{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.bob-status-controls button{background:#255b95;color:#fff;padding:9px 16px;border:1px solid #8abaff;
 border-radius:9px;font:inherit;cursor:pointer}
.bob-status-controls button:focus-visible{outline:3px solid #f6cb76}
@media(max-width:500px){.bob-status-panel{padding:14px}.bob-status-job{align-items:flex-start;flex-direction:column}}
@media(prefers-reduced-motion:reduce){.bob-status *{transition:none!important;animation:none!important}}
</style>"""

JS = r"""'use strict';
(() => {
  const root = document.getElementById('bob-live-status');
  if (!root) return;
  const grid = document.getElementById('bob-service-grid');
  const jobs = document.getElementById('bob-job-list');
  const workers = document.getElementById('bob-worker-grid');
  const stamp = document.getElementById('bob-status-updated');
  const notice = document.getElementById('bob-status-notice');
  const reload = document.getElementById('bob-status-refresh');
  let running = false;
  let timer = null;
  const tone = (s) => {
    if (['fetching', 'validating', 'generating', 'preflight', 'sending', 'verifying'].includes(s)) return 'busy';
    if (['running', 'ready', 'listening', 'completed'].includes(s)) return 'good';
    if (['unavailable', 'failed', 'error'].includes(s)) return 'bad';
    if (['inactive', 'idle', 'queued', 'awaiting_verification'].includes(s)) return 'idle';
    if (s === 'waiting' || s === 'model_missing') return 'warn';
    return 'warn';
  };
  const pill = (state) => {
    const el = document.createElement('span');
    el.className = 'bob-status-state';
    el.dataset.tone = tone(String(state));
    el.textContent = String(state);
    return el;
  };
  const draw = (data) => {
    if (!data || !Array.isArray(data.services) || !data.queue || !Array.isArray(data.queue.jobs)) {
      throw new Error('Invalid status response');
    }
    const cards = data.services.slice(0, 12).map((item) => {
      const el = document.createElement('div');
      el.className = 'bob-status-card';
      const title = document.createElement('strong');
      title.textContent = String(item.name || 'Service');
      el.append(title, pill(item.state || 'unknown'));
      return el;
    });
    grid.replaceChildren(...cards);
    const stages = (Array.isArray(data.workers) ? data.workers : []).slice(0, 3).map((item) => {
      const card = document.createElement('div');
      card.className = 'bob-status-card bob-status-worker';
      const name = document.createElement('strong');
      name.textContent = String(item.worker || 'worker');
      const msg = document.createElement('small');
      msg.textContent = String(item.message || 'No additional details');
      const seen = document.createElement('small');
      seen.textContent = 'Last checkpoint: ' + String(item.updated_at || 'unknown');
      card.append(name, pill(item.stage || 'unknown'), msg, seen);
      return card;
    });
    if (!stages.length) {
      const empty = document.createElement('p');
      empty.textContent = 'Waiting for worker checkpoints. Existing jobs are shown below.';
      stages.push(empty);
    }
    workers.replaceChildren(...stages);
    const entries = data.queue.jobs.slice(0, 30).map((job) => {
      const el = document.createElement('li');
      el.className = 'bob-status-job';
      const info = document.createElement('div');
      const kind = document.createElement('strong');
      kind.textContent = String(job.kind || 'job');
      const created = document.createElement('small');
      created.textContent = 'Created: ' + String(job.created || 'unknown') + ' · Updated: ' + String(job.updated || 'not recorded');
      info.append(kind, created);
      if (job.has_error) {
        const marker = document.createElement('small');
        marker.className = 'bob-status-warning';
        marker.textContent = 'Error recorded. Check job details/logs; no automatic retry.';
        info.append(marker);
      }
      el.append(info, pill(job.state || 'unknown'));
      return el;
    });
    if (!data.queue.available || !entries.length) {
      const item = document.createElement('li');
      item.textContent = data.queue.available ? 'No recent recorded jobs.' : 'Queue records currently unavailable.';
      entries.push(item);
    }
    jobs.replaceChildren(...entries);
    stamp.textContent = 'Last checked: ' + (new Date()).toLocaleTimeString();
    notice.textContent = 'Read-only snapshot. Process activity is not proof that a job is complete.';
  };
  async function refresh() {
    if (running || document.hidden) return;
    running = true;
    reload.disabled = true;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 12500);
    try {
      const response = await fetch('/api/system/status', {
        method: 'GET', credentials: 'same-origin', cache: 'no-store',
        headers: {'Accept': 'application/json'}, signal: ctrl.signal
      });
      if (!response.ok) throw new Error('Status request unavailable');
      const data = await response.json();
      draw(data);
    } catch (_) {
      notice.textContent = 'Unable to refresh. Showing last successful snapshot; check Bob connectivity or login.';
    } finally {
      clearTimeout(timeout);
      reload.disabled = false;
      running = false;
    }
  }
  reload.addEventListener('click', refresh);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  timer = setInterval(refresh, 15000);
  refresh();
})();
"""

def javascript():
    return JS


def _pill(state):
    value = str(state)
    tone = ("busy" if value in ("fetching", "validating", "generating", "preflight", "sending", "verifying") else
            "good" if value in ("running", "ready", "listening", "completed") else
            "bad" if value in ("unavailable", "failed", "error") else
            "idle" if value in ("inactive", "idle", "queued", "awaiting_verification") else "warn")
    return '<span class="bob-status-state" data-tone="' + tone + '">' + escape(value) + '</span>'


def page(data):
    cards = []
    for item in data.get("services", [])[:12]:
        cards.append('<div class="bob-status-card"><strong>' + escape(str(item.get("name", ""))) +
                     '</strong>' + _pill(item.get("state", "unknown")) + '</div>')
    workers = []
    for item in data.get("workers", [])[:3]:
        workers.append('<div class="bob-status-card bob-status-worker"><strong>' +
                       escape(str(item.get("worker", ""))) + '</strong>' +
                       _pill(item.get("stage", "unknown")) +
                       '<small>' + escape(str(item.get("message", ""))) + '</small>' +
                       '<small>Last checkpoint: ' +
                       escape(str(item.get("updated_at", ""))) + '</small></div>')
    if not workers:
        workers.append('<p>Waiting for worker checkpoints. Existing jobs are shown below.</p>')
    jobs = []
    queue = data.get("queue", {})
    for job in queue.get("jobs", [])[:30]:
        warning = ('<small class="bob-status-warning">Error recorded; no automatic retry</small>'
                   if job.get("has_error") else '')
        jobs.append('<li class="bob-status-job"><div><strong>' +
                    escape(str(job.get("kind", ""))) + '</strong><small>Created: ' +
                    escape(str(job.get("created", ""))) + ' · Updated: ' +
                    escape(str(job.get("updated", ""))) + '</small>' + warning +
                    '</div>' + _pill(job.get("state", "unknown")) + '</li>')
    if not jobs:
        jobs.append('<li>' + ('No recent recorded jobs.' if queue.get("available") else
                              'Queue records currently unavailable.') + '</li>')
    body = (STYLE + '<div id="bob-live-status" class="bob-status">'
            '<p class="bob-status-intro">Actual local service and publication records. '
            'One-shot workers may be inactive between jobs. No invented progress percentages.</p>'
            '<div class="bob-status-controls"><button type="button" id="bob-status-refresh">Refresh now</button>'
            '<span id="bob-status-updated" class="bob-status-last">Initial snapshot</span></div>'
            '<p id="bob-status-notice" role="status" aria-live="polite" class="bob-status-last">'
            'Automatic updates every 15 seconds while this tab is visible.</p>'
            '<section class="bob-status-panel" aria-label="Local services"><h2>Services & dependencies</h2>'
            '<div id="bob-service-grid" class="bob-status-grid">' + "".join(cards) + '</div></section>'
            '<section class="bob-status-panel" aria-label="Worker stages"><h2>Recent worker stages</h2>'
            '<div id="bob-worker-grid" class="bob-status-grid">' + "".join(workers) + '</div></section>'
            '<section class="bob-status-panel" aria-label="Recorded jobs"><h2>Recent recorded jobs</h2>'
            '<ul id="bob-job-list" class="bob-status-table">' + "".join(jobs) + '</ul></section>'
            '<noscript><p>JavaScript is disabled. Reload this page to refresh its read-only snapshot.</p></noscript>'
            '</div>')
    rendered = wrap("System status", body, "/system/status")
    return rendered.replace('</head>', '<script src="/assets/bob-status.js" defer></script></head>', 1)
