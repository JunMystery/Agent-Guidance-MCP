let pollTimer = null;
let pollBackoff = 1000;

function qs(s) { return document.querySelector(s); }
function qsa(s) { return document.querySelectorAll(s); }

function init() {
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

function safeText(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val;
}

function safeDisplay(id, val) {
  var el = document.getElementById(id);
  if (el) el.style.display = val;
}

async function fetchData() {
  let resp, data;
  try {
    resp = await fetch('/api/stats');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    data = await resp.json();
    render(data);
    pollBackoff = 1000;
    safeText('error-banner', '');
    safeDisplay('error-banner', 'none');
  } catch(e) {
    console.error('fetch error', e);
    pollBackoff = Math.min(pollBackoff * 2, 30000);
    safeText('error-banner', 'Failed to connect to stats: ' + (e.message || 'unknown'));
    safeDisplay('error-banner', 'block');
    safeText('actions-poll', e.message ? '(retry in ' + (pollBackoff/1000).toFixed(0) + 's)' : '');
  }
  try {
    const hresp = await fetch('/health');
    const hdata = await hresp.json();
    renderHealth(hdata, data?.totals?.embed_queries);
  } catch(e) {
    renderHealth({status: 'unknown'}, data?.totals?.embed_queries);
  }
  renderEmbedRecent(data);
  renderModelStatus();
}

function render(data) {
  const t = data.totals || {};

  // Populate $ mcp --status
  safeText('out-client-name', 'global');
  safeText('out-session-label', 'per-call tracking');

  // Populate $ mcp --totals
  safeText('out-tool-calls', t.tool_calls || 0);
  safeText('out-skills-loaded', t.skills_loaded || 0);
  safeText('out-embed-queries', t.embed_queries || 0);

  // Populate $ mcp --savings
  safeText('out-original-tokens', fmtTokens(t.tokens_original));
  safeText('out-optimized-tokens', fmtTokens(t.tokens_optimized));
  safeText('out-token-savings', fmtTokens(t.token_savings) + ' (' + fmtPct(t.savings_pct) + ' savings)');

  const skillsBody = document.getElementById('dash-skills');
  skillsBody.innerHTML = '';
  if (data.top_skills && data.top_skills.length) {
    data.top_skills.slice(0, 10).forEach(sk => {
      skillsBody.innerHTML += '<tr><td>' + sk.skill_id + '</td><td>' + sk.cnt + '</td></tr>';
    });
  } else {
    skillsBody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted)">No skills loaded yet</td></tr>';
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
    actionsBody.innerHTML = '<tr><td colspan="6" style="color:var(--text-muted)">No tool calls recorded yet</td></tr>';
  }

  const tokenBars = document.getElementById('token-bars');
  let barsHtml = '<h3 style="font-size:14px;margin-bottom:12px">Lifetime Summary</h3>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Original</span><div class="bar-track"><div class="bar-fill" style="width:100%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_original) + '</span></div>';
  const optW = t.tokens_original ? Math.round((t.tokens_optimized / t.tokens_original) * 100) : 0;
  barsHtml += '<div class="bar-row"><span class="bar-label">Optimized</span><div class="bar-track"><div class="bar-fill opt" style="width:' + optW + '%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_optimized) + '</span></div>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Saved</span><div class="bar-track"><div class="bar-fill" style="width:' + (100 - optW) + '%;background:var(--accent-secondary);opacity:0.6"></div></div><span class="bar-num" style="font-weight:700;color:var(--accent-secondary)">' + fmtTokens(t.token_savings) + '</span></div>';
  tokenBars.innerHTML = barsHtml;
}

function renderHealth(h, embedQueries) {
  const modelLoaded = h.model_loaded !== undefined ? h.model_loaded : null;
  const clients = h.clients !== undefined ? h.clients : null;

  safeText('sys-daemon', h.status === 'ok' ? 'running' : 'stopped');
  safeText('sys-model', modelLoaded === null ? 'unknown' : (modelLoaded ? 'loaded' : 'unloaded'));
  safeText('sys-clients', clients === null ? '0' : String(clients));

  const modelStatus = modelLoaded === null ? 'unknown' : (modelLoaded ? 'loaded' : 'unloaded');
  safeText('out-daemon-status', h.status === 'ok' ? 'running' : 'stopped');
  safeText('out-model-status', modelStatus);
  safeText('out-engine', h.engine || 'unknown');
  safeText('out-embed-queries', String(embedQueries || 0));
  safeText('out-uptime', h.uptime_seconds ? fmtDuration(h.uptime_seconds) : '--');
  safeText('out-clients', clients === null ? '0' : String(clients));
  safeText('out-last-embed', h.last_embed_time ? timeAgo(h.last_embed_time) : '--');

  safeText('sys-embed-model', modelStatus);
  safeText('sys-embed-daemon', h.status === 'ok' ? 'running' : 'stopped');
  safeText('sys-embed-clients', clients === null ? '0' : String(clients));
  safeText('sys-embed-backend', h.backend || 'unknown');

  const btn = document.getElementById('btn-embed-toggle');
  if (btn) {
    btn.textContent = modelLoaded ? 'Stop Model' : 'Start Model';
    btn.className = modelLoaded ? 'btn-secondary' : 'btn-accent';
  }
}

function renderModelStatus() {
  fetch('/api/model/status')
    .then(r => r.ok ? r.json() : null)
    .then(s => {
      if (!s) return;
      const btn = document.getElementById('btn-embed-toggle');
      if (!btn) return;
      // Pinned state is authoritative: Stop sticks until user Starts again.
      const started = s.pinned === true || (s.pinned === null && s.loaded);
      btn.textContent = started ? 'Stop Model' : 'Start Model';
      btn.className = started ? 'btn-secondary' : 'btn-accent';
      safeText('sys-embed-backend', s.backend || 'unknown');
    })
    .catch(() => {});
}

function renderEmbedRecent(data) {
  const body = document.getElementById('embed-recent-body');
  if (!body) return;
  const rows = (data && data.embed_recent) || [];
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="4" style="color:var(--text-muted)">No embed queries yet</td></tr>';
    return;
  }
  body.innerHTML = rows.map(r => {
    const status = r.status === 'fallback' ? 'fallback' : 'ok';
    const badge = status === 'fallback' ? 'badge red' : 'badge green';
    const dim = r.vector_dim || 0;
    return '<tr><td>' + timeAgo(r.queried_at) + '</td>' +
           '<td><span class="' + badge + '">' + status + '</span></td>' +
           '<td>' + dim + '</td>' +
           '<td>' + (r.result_count || 0) + '</td></tr>';
  }).join('');
}

function fmtDuration(sec) {
  if (sec < 60) return sec + 's';
  if (sec < 3600) return Math.floor(sec / 60) + 'm ' + (sec % 60) + 's';
  if (sec < 86400) return Math.floor(sec / 3600) + 'h ' + Math.floor((sec % 3600) / 60) + 'm';
  return Math.floor(sec / 86400) + 'd ' + Math.floor((sec % 86400) / 3600) + 'h';
}

function toggleModel() {
  const btn = document.getElementById('btn-embed-toggle');
  // The button label reflects the desired NEXT state (Stop if started).
  const started = btn && btn.textContent.trim() === 'Stop Model';
  const action = started ? 'unload' : 'load';
  fetch('/api/model/toggle?action=' + action, { method: 'POST' })
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      renderModelStatus();
      fetchData();
    })
    .catch(e => alert('Failed to toggle: ' + e.message));
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
