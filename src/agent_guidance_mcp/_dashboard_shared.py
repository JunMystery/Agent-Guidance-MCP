"""Shared constants and utilities for dashboard and embed daemon.

Pure stdlib — no fastapi dependency. Safe to import from anywhere.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DAEMON_DIR = Path.home() / ".agent-guidance"
DAEMON_PORT_FILE = DAEMON_DIR / "daemon.json"
DASHBOARD_DIR = DAEMON_DIR / "dashboard"


def write_default_dashboard(path: Path) -> None:
    """Write the default dashboard HTML if not present."""
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MCP Usage Dashboard</title>
<style>
:root{--bg:#f5f5f7;--surface:#fff;--text:#1d1d1f;--muted:#86868b;--border:#d2d2d7;--accent:#0066cc;--accent-hover:#0077ed;--bar:#0066cc;--bar-opt:#34c759;--danger:#ff3b30;--radius:12px;--shadow:0 2px 12px rgba(0,0,0,.08)}
@media(prefers-color-scheme:dark){
:root{--bg:#1c1c1e;--surface:#2c2c2e;--text:#f5f5f7;--muted:#98989f;--border:#48484a;--accent:#0a84ff;--accent-hover:#409cff;--bar:#0a84ff;--bar-opt:#30d158;--danger:#ff453a;--shadow:0 2px 12px rgba(0,0,0,.3)}
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh}
.hamburger{display:none;position:fixed;top:12px;left:12px;z-index:100;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:20px;cursor:pointer}
.sidebar{width:240px;background:var(--surface);border-right:1px solid var(--border);padding:24px 16px;display:flex;flex-direction:column;flex-shrink:0}
.sidebar h2{font-size:18px;font-weight:700;margin-bottom:24px;color:var(--accent)}
.sidebar nav{display:flex;flex-direction:column;gap:4px;flex:1}
.sidebar nav a{padding:10px 14px;border-radius:8px;text-decoration:none;color:var(--text);font-size:14px;font-weight:500;transition:.15s;cursor:pointer}
.sidebar nav a:hover{background:var(--bg)}
.sidebar nav a.active{background:var(--accent);color:#fff}
.sidebar-footer{font-size:11px;color:var(--muted);padding-top:16px;border-top:1px solid var(--border);margin-top:16px}
.sidebar-footer .proj{word-break:break-all}
.error-banner{background:var(--danger);color:#fff;padding:8px 16px;border-radius:8px;font-size:13px;margin-bottom:16px;display:none}
.main{flex:1;padding:32px 40px;overflow-y:auto;min-width:0}
.hidden{display:none!important}
.session-bar{margin-bottom:24px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.session-bar select{flex:1;min-width:200px;padding:8px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:14px}
.session-bar .status{font-size:12px;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}
.card{background:var(--surface);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow)}
.card .label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.card .value{font-size:28px;font-weight:700}
.card .sub{font-size:13px;color:var(--muted);margin-top:4px}
.bar-row{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.bar-row .bar-label{width:140px;font-size:13px;text-align:right;flex-shrink:0}
.bar-track{flex:1;height:24px;background:var(--bg);border-radius:6px;overflow:hidden;display:flex}
.bar-fill{height:100%;background:var(--bar);border-radius:6px;transition:width .3s}
.bar-fill.opt{background:var(--bar-opt)}
.bar-row .bar-num{width:60px;font-size:12px;color:var(--muted);flex-shrink:0}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;padding:10px 12px;border-bottom:2px solid var(--border);color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
td{padding:10px 12px;border-bottom:1px solid var(--border)}
tr:hover td{background:var(--bg)}
.badge{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.badge.green{background:#30d15833;color:var(--bar-opt)}
.badge.red{background:#ff453a33;color:var(--danger)}
.guide-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.guide-card{background:var(--surface);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow)}
.guide-card h3{font-size:16px;margin-bottom:8px}
.guide-card p{font-size:13px;color:var(--muted);margin-bottom:12px;line-height:1.5}
.guide-card code{display:block;background:var(--bg);padding:10px;border-radius:6px;font-size:12px;overflow-x:auto}
.section-title{font-size:20px;font-weight:700;margin-bottom:20px}
@media(max-width:768px){
.hamburger{display:block}
.sidebar{position:fixed;top:0;left:0;height:100vh;z-index:99;transform:translateX(-100%);transition:transform .25s}
.sidebar.open{transform:translateX(0)}
.sidebar.open~.main{margin-left:0}
.main{padding:20px 16px;margin-left:0}
.cards{grid-template-columns:1fr 1fr}
}
</style>
</head>
<body>

<button class="hamburger" onclick="toggleSidebar()" aria-label="Toggle sidebar">☰</button>

<aside class="sidebar" id="sidebar">
<h2>MCP Stats</h2>
<nav>
<a class="active" data-view="dashboard"><span>Dashboard</span></a>
<a data-view="actions"><span>Actions Log</span></a>
<a data-view="tokens"><span>Token Savings</span></a>
<a data-view="embed"><span>Embed Status</span></a>
<a data-view="guides"><span>Quick Guides</span></a>
<a data-view="tools"><span>MCP Tools</span></a>
</nav>
<div class="sidebar-footer">
<div class="proj" id="sidebar-proj" onclick="changeProjectPath()" title="Click to change project path" style="cursor:pointer">project: --</div>
<div id="sidebar-port">port: --</div>
</div>
</aside>

<main class="main">
<div class="error-banner" id="error-banner"></div>
<div class="session-bar" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
<input type="text" id="project-path-input" placeholder="Enter project path..." style="flex:2;min-width:160px;padding:8px 12px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:13px">
<button onclick="setProjectPath()" style="padding:8px 14px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer;font-size:13px">Set Path</button>
<select id="session-select" style="flex:1;min-width:120px;padding:8px 12px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:13px"><option value="">-- select session --</option></select>
<button onclick="fetchData()" style="padding:6px 14px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer;font-size:13px">Refresh</button>
</div>

<section id="view-dashboard">
<div class="section-title">Dashboard</div>
<div class="cards" id="dash-cards"></div>
<div style="margin-top:24px">
<h3 style="font-size:16px;margin-bottom:12px">Top Skills</h3>
<table><thead><tr><th>Skill</th><th>Loads</th></tr></thead><tbody id="dash-skills"></tbody></table>
</div>
</section>

<section id="view-actions" class="hidden">
<div class="section-title">Actions Log <span id="actions-poll" style="font-size:12px;font-weight:400;color:var(--muted)"></span></div>
<table><thead><tr><th>Tool</th><th>Operation</th><th>Calls</th><th>Orig Tokens</th><th>Opt Tokens</th><th>Savings</th></tr></thead><tbody id="actions-body"></tbody></table>
</section>

<section id="view-tokens" class="hidden">
<div class="section-title">Token Savings</div>
<div id="token-bars"></div>
<div class="cards" style="margin-top:20px" id="token-summary-cards"></div>
</section>

<section id="view-embed" class="hidden">
<div class="section-title">Embed Status</div>
<div class="cards" id="embed-cards"></div>
</section>

<section id="view-guides" class="hidden">
<div class="section-title">Quick Guides</div>
<div class="guide-cards">
<div class="guide-card"><h3>1. Start with task_pipeline</h3><p>Call first before any coding task. Returns project context, recommendations, code search in one call.</p><code>task_pipeline(task=&quot;Add JWT auth&quot;, focus=&quot;backend&quot;)</code></div>
<div class="guide-card"><h3>2. Find skills with guidance</h3><p>Search 168 on-demand skills. Auto-discovers relevant coding standards for your task.</p><code>guidance(operation=&quot;search&quot;, query=&quot;testing patterns&quot;)</code></div>
<div class="guide-card"><h3>3. Read code with project_context</h3><p>Read files, search codebase, extract symbols — all with built-in token budgets.</p><code>project_context(operation=&quot;read&quot;, relative_path=&quot;src/auth.js&quot;)</code></div>
<div class="guide-card"><h3>4. Track progress with session_continuity</h3><p>Save and resume task state across sessions and interruptions.</p><code>session_continuity(operation=&quot;save&quot;, task=&quot;...&quot;, checklist=[...])</code></div>
</div>
</section>

<section id="view-tools" class="hidden">
<div class="section-title">Available MCP Tools</div>
<table><thead><tr><th>Tool</th><th>Gate</th><th>Description</th><th>Operations</th></tr></thead><tbody>
<tr><td>task_pipeline</td><td><span class="badge green">Unlocks</span></td><td>Call first — context prep</td><td>run</td></tr>
<tr><td>guidance</td><td><span class="badge">Gated</span></td><td>Standards &amp; skill catalog</td><td>list, get, search, recommend, reason, docs</td></tr>
<tr><td>project_context</td><td><span class="badge">Gated</span></td><td>Project file ops + search</td><td>tree, search, read, symbols, references, structure, callers, callees, diff, snapshot</td></tr>
<tr><td>ui_ux</td><td><span class="badge">Gated</span></td><td>Design guidance</td><td>search, design_system, slides</td></tr>
<tr><td>session_continuity</td><td><span class="badge">Gated</span></td><td>Task state persistence</td><td>save, load, clear</td></tr>
<tr><td>usage_report</td><td><span class="badge">Gated</span></td><td>Usage statistics</td><td>session, all</td></tr>
<tr><td>workflow_prompt</td><td><span class="badge">Gated</span></td><td>Workflow prompts</td><td>plan, test, deploy, debug, etc.</td></tr>
<tr><td>health_check</td><td><span class="badge green">Always</span></td><td>Server status</td><td>—</td></tr>
<tr><td>diagnose</td><td><span class="badge green">Always</span></td><td>Self-diagnostics</td><td>—</td></tr>
<tr><td>token_stats</td><td><span class="badge green">Always</span></td><td>Token optimization stats</td><td>—</td></tr>
</tbody></table>
</section>

</main>

<script>
let currentSessionId = null;
let pollTimer = null;
let pollBackoff = 1000;
let projectPath = '';

function qs(s) { return document.querySelector(s); }
function qsa(s) { return document.querySelectorAll(s); }

function setProjectPath() {
  const input = document.getElementById('project-path-input');
  const val = input.value.trim();
  if (val) {
    projectPath = val;
    localStorage.setItem('mcp_project_path', projectPath);
    document.getElementById('sidebar-proj').textContent = 'project: ' + projectPath;
    fetchData();
  }
}

function changeProjectPath() {
  document.getElementById('project-path-input').value = projectPath || '';
  document.getElementById('project-path-input').focus();
  window.scrollTo({top: 0, behavior: 'smooth'});
}

function init() {
  const params = new URLSearchParams(location.search);
  projectPath = params.get('project_path') || localStorage.getItem('mcp_project_path') || '';
  if (projectPath) {
    document.getElementById('sidebar-proj').textContent = 'project: ' + projectPath;
    document.getElementById('project-path-input').value = projectPath;
  }
  // Enter key in input triggers set
  document.getElementById('project-path-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') setProjectPath();
  });

  qsa('.sidebar nav a').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      qsa('.sidebar nav a').forEach(x => x.classList.remove('active'));
      a.classList.add('active');
      qsa('main section').forEach(s => s.classList.add('hidden'));
      const view = document.getElementById('view-' + a.dataset.view);
      if (view) view.classList.remove('hidden');
      if (a.dataset.view === 'actions') startPoll();
      else stopPoll();
    });
  });

  fetchData();
}

function timeAgo(ts) {
  const sec = Math.floor((Date.now()/1000) - ts);
  if (sec < 60) return sec + 's ago';
  if (sec < 3600) return Math.floor(sec/60) + 'm ago';
  if (sec < 86400) return Math.floor(sec/3600) + 'h ago';
  return Math.floor(sec/86400) + 'd ago';
}

function fmtTokens(n) {
  if (!n) return '0';
  if (n >= 1000) return (n/1000).toFixed(1) + 'k';
  return String(n);
}

function fmtPct(n) {
  return (n || 0).toFixed(1) + '%';
}

async function fetchData() {
  if (!projectPath) return;
  const url = currentSessionId
    ? '/api/stats?project_path=' + encodeURIComponent(projectPath) + '&session_id=' + encodeURIComponent(currentSessionId)
    : '/api/stats?project_path=' + encodeURIComponent(projectPath);
  let resp;
  try {
    resp = await fetch(url);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    render(data);
    pollBackoff = 1000;
    document.getElementById('error-banner').style.display = 'none';
  } catch(e) {
    console.error('fetch error', e);
    pollBackoff = Math.min(pollBackoff * 2, 30000);
    document.getElementById('error-banner').textContent = 'Failed to connect to stats: ' + (e.message || 'unknown');
    document.getElementById('error-banner').style.display = 'block';
    document.getElementById('actions-poll').textContent = e.message ? '(retry in ' + (pollBackoff/1000).toFixed(0) + 's)' : '';
  }
  try {
    const hresp = await fetch('/health');
    const hdata = await hresp.json();
    renderHealth(hdata, data.totals?.embed_queries);
  } catch(e) {
    renderHealth({status: 'unknown'}, data.totals?.embed_queries);
  }
}

function render(data) {
  const sel = document.getElementById('session-select');
  if (data.sessions) {
    sel.innerHTML = '<option value="">-- all sessions --</option>';
    data.sessions.forEach(s => {
      const label = (s.client_name || 'unknown') + (s.session_label ? ' - "' + s.session_label + '"' : '') + ' (' + timeAgo(s.started_at) + ')' + (s.ended_at ? '' : ' [active]');
      const opt = document.createElement('option');
      opt.value = s.session_id;
      opt.textContent = label;
      if (s.session_id === currentSessionId) opt.selected = true;
      sel.appendChild(opt);
    });
  }
  sel.onchange = () => {
    currentSessionId = sel.value || null;
    fetchData();
  };

  const t = data.totals || {};
  document.getElementById('dash-cards').innerHTML = `
    <div class="card"><div class="label">Tool Calls</div><div class="value">${t.tool_calls || 0}</div></div>
    <div class="card"><div class="label">Skills Loaded</div><div class="value">${t.skills_loaded || 0}</div></div>
    <div class="card"><div class="label">Embed Queries</div><div class="value">${t.embed_queries || 0}</div></div>
    <div class="card"><div class="label">Tokens Saved</div><div class="value">${fmtTokens(t.token_savings)}</div><div class="sub">${fmtPct(t.savings_pct)} savings</div></div>
  `;

  const skillsBody = document.getElementById('dash-skills');
  skillsBody.innerHTML = '';
  if (data.top_skills && data.top_skills.length) {
    data.top_skills.slice(0, 10).forEach(s => {
      skillsBody.innerHTML += '<tr><td>' + s.skill_id + '</td><td>' + s.cnt + '</td></tr>';
    });
  } else {
    skillsBody.innerHTML = '<tr><td colspan="2" style="color:var(--muted)">No skills loaded yet</td></tr>';
  }

  const actionsBody = document.getElementById('actions-body');
  actionsBody.innerHTML = '';
  if (data.tool_breakdown && data.tool_breakdown.length) {
    data.tool_breakdown.forEach(r => {
      const saved = (r.tok_orig || 0) - (r.tok_opt || 0);
      const pct = r.tok_orig ? ((saved / r.tok_orig) * 100).toFixed(1) : '0.0';
      const pctNum = parseFloat(pct);
      const badgeClass = pctNum > 50 ? 'badge green' : (pctNum > 20 ? 'badge' : 'badge red');
      actionsBody.innerHTML += '<tr><td>' + r.tool_name + '</td><td>' + (r.operation || '--') + '</td><td>' + r.cnt + '</td><td>' + fmtTokens(r.tok_orig) + '</td><td>' + fmtTokens(r.tok_opt) + '</td><td><span class="' + badgeClass + '">' + pct + '%</span></td></tr>';
    });
  } else {
    actionsBody.innerHTML = '<tr><td colspan="6" style="color:var(--muted)">No tool calls recorded yet</td></tr>';
  }

  const tokenBars = document.getElementById('token-bars');
  let barsHtml = '<h3 style="font-size:16px;margin-bottom:12px">Per-Session Savings</h3>';
  if (data.sessions && data.sessions.length) {
    data.sessions.slice(0, 10).forEach(s => {
      const label = (s.client_name || '?') + (s.session_label ? ': ' + s.session_label : '') + ' (' + timeAgo(s.started_at) + ')';
      const sessOrig = s.total_tokens_original || 0;
      const sessOpt = s.total_tokens_optimized || 0;
      const saved = sessOrig - sessOpt;
      const pct = sessOrig ? ((saved / sessOrig) * 100).toFixed(1) : '0.0';
      const badgeClass = parseFloat(pct) > 50 ? 'badge green' : (parseFloat(pct) > 0 ? 'badge' : 'badge red');
      if (sessOrig > 0) {
        barsHtml += '<div class="bar-row"><span class="bar-label" title="' + label + '">' + label.substring(0, 30) + '</span><div class="bar-track"><div class="bar-fill" style="width:100%"></div></div><span class="bar-num"><span class="' + badgeClass + '">' + pct + '%</span></span></div>';
      }
    });
  }
  barsHtml += '<h3 style="font-size:16px;margin:20px 0 12px">Lifetime</h3>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Original</span><div class="bar-track"><div class="bar-fill" style="width:100%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_original) + '</span></div>';
  const optW = t.tokens_original ? Math.round((t.tokens_optimized / t.tokens_original) * 100) : 0;
  barsHtml += '<div class="bar-row"><span class="bar-label">Optimized</span><div class="bar-track"><div class="bar-fill opt" style="width:' + optW + '%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_optimized) + '</span></div>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Saved</span><div class="bar-track"><div class="bar-fill" style="width:' + (100 - optW) + '%;background:var(--bar-opt);opacity:0.5"></div></div><span class="bar-num" style="font-weight:700;color:var(--bar-opt)">' + fmtTokens(t.token_savings) + '</span></div>';
  tokenBars.innerHTML = barsHtml;

  document.getElementById('session-status').textContent = data.session && data.session.session_id ? 'Session: ' + (data.session.client_name || '?') + ' ' + timeAgo(data.session.started_at) : '';
}

function renderHealth(h, embedQueries) {
  const modelLoaded = h.model_loaded !== undefined ? h.model_loaded : null;
  const clients = h.clients !== undefined ? h.clients : null;
  let cardsHtml = '<div class="card"><div class="label">Status</div><div class="value"><span class="badge ' + (h.status === 'ok' ? 'green' : 'red') + '">' + (h.status || 'unknown') + '</span></div></div>';
  if (modelLoaded !== null) {
    cardsHtml += '<div class="card"><div class="label">Model Loaded</div><div class="value"><span class="badge ' + (modelLoaded ? 'green' : 'red') + '">' + (modelLoaded ? 'Yes' : 'No') + '</span></div></div>';
  }
  if (clients !== null) {
    cardsHtml += '<div class="card"><div class="label">Active Clients</div><div class="value">' + clients + '</div></div>';
  }
  cardsHtml += '<div class="card"><div class="label">Embed Queries</div><div class="value">' + (embedQueries || 0) + '</div><div class="sub">Total across all sessions</div></div>';
  document.getElementById('embed-cards').innerHTML = cardsHtml;
}

function startPoll() {
  stopPoll();
  document.getElementById('actions-poll').textContent = '(polling 5s)';
  if (!document.hidden) pollTimer = setInterval(fetchData, 5000);
  pollBackoff = 1000;
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  document.getElementById('actions-poll').textContent = '';
}

document.addEventListener('visibilitychange', () => {
  const onActions = document.querySelector('.sidebar nav a.active')?.dataset?.view === 'actions';
  if (document.hidden) { stopPoll(); }
  else if (onActions) { startPoll(); }
});

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}
document.addEventListener('DOMContentLoaded', () => {
  init();
  document.querySelectorAll('.sidebar nav a').forEach(a => {
    a.addEventListener('click', () => {
      if (window.innerWidth <= 768) document.getElementById('sidebar').classList.remove('open');
    });
  });
});
</script>

</body>
</html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
