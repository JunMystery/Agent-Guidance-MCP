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
      if (a.dataset.view === 'actions' || a.dataset.view === 'recent-calls') startPoll();
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
    const view = document.querySelector('.sidebar nav a.active')?.dataset?.view;
    const pollSpanId = view === 'actions' ? 'actions-poll' : (view === 'recent-calls' ? 'recent-calls-poll' : null);
    if (pollSpanId) {
      safeText(pollSpanId, e.message ? '(retry in ' + (pollBackoff/1000).toFixed(0) + 's)' : '');
    }
  }
  try {
    const hresp = await fetch('/health');
    const hdata = await hresp.json();
    renderHealth(hdata, data?.totals?.embed_queries);
  } catch(e) {
    renderHealth({status: 'unknown'}, data?.totals?.embed_queries);
  }
  renderEmbedRecent(data);
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

  const recentCallsBody = document.getElementById('recent-calls-body');
  if (recentCallsBody) {
    recentCallsBody.innerHTML = '';
    if (data.recent_actions && data.recent_actions.length) {
      data.recent_actions.forEach(r => {
        const saved = (r.tokens_original || 0) - (r.tokens_optimized || 0);
        const pct = r.tokens_original ? ((saved / r.tokens_original) * 100).toFixed(1) : '0.0';
        const pctNum = parseFloat(pct);
        const badgeClass = pctNum > 50 ? 'badge green' : (pctNum > 20 ? 'badge' : 'badge red');
        const duration = r.duration_ms ? r.duration_ms + 'ms' : '--';
        const statusClass = r.error_message ? 'badge red' : 'badge green';
        const statusText = r.error_message ? 'error' : 'ok';
        const statusTitle = r.error_message ? ' title="' + r.error_message.replace(/"/g, '&quot;') + '"' : '';
        recentCallsBody.innerHTML += '<tr>' +
          '<td>' + timeAgo(r.started_at) + '</td>' +
          '<td>' + r.tool_name + '</td>' +
          '<td>' + (r.operation || '--') + '</td>' +
          '<td>' + duration + '</td>' +
          '<td>' + fmtTokens(r.tokens_original) + '</td>' +
          '<td>' + fmtTokens(r.tokens_optimized) + '</td>' +
          '<td><span class="' + badgeClass + '">' + pct + '%</span></td>' +
          '<td><span class="' + statusClass + '"' + statusTitle + '>' + statusText + '</span></td>' +
          '</tr>';
      });
    } else {
      recentCallsBody.innerHTML = '<tr><td colspan="8" style="color:var(--text-muted)">No recent calls recorded yet</td></tr>';
    }
  }

  const tokenBars = document.getElementById('token-bars');
  let barsHtml = '<h3 style="font-size:14px;margin-bottom:12px">Lifetime Summary</h3>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Original</span><div class="bar-track"><div class="bar-fill" style="width:100%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_original) + '</span></div>';
  const optW = t.tokens_original ? Math.round((t.tokens_optimized / t.tokens_original) * 100) : 0;
  barsHtml += '<div class="bar-row"><span class="bar-label">Optimized</span><div class="bar-track"><div class="bar-fill opt" style="width:' + optW + '%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_optimized) + '</span></div>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Saved</span><div class="bar-track"><div class="bar-fill" style="width:' + (100 - optW) + '%;background:var(--accent-secondary);opacity:0.6"></div></div><span class="bar-num" style="font-weight:700;color:var(--accent-secondary)">' + fmtTokens(t.token_savings) + '</span></div>';
  tokenBars.innerHTML = barsHtml;

  const chart = document.getElementById('hourly-chart');
  if (chart) {
    const hours = (data.hourly_savings || []);
    const maxSaved = hours.reduce((m, h) => Math.max(m, h.saved || 0), 0);
    const maxLine = hours.reduce((m, h) => Math.max(m, h.original || 0, h.optimized || 0), 0);
    if (!hours.length || (maxSaved === 0 && maxLine === 0)) {
      chart.innerHTML = '<div class="chart-empty">No token data in the last 24h — make a tool call to start saving tokens.</div>';
    } else {
      const kpi = '<div class="savings-kpi">' +
        '<div class="kpi"><span class="kpi-label">Original</span><span class="kpi-val">' + fmtTokens(t.tokens_original) + '</span></div>' +
        '<div class="kpi"><span class="kpi-label">Optimized</span><span class="kpi-val">' + fmtTokens(t.tokens_optimized) + '</span></div>' +
        '<div class="kpi"><span class="kpi-label">Saved</span><span class="kpi-val kpi-saved">' + fmtTokens(t.token_savings) + '</span></div>' +
        '<div class="kpi"><span class="kpi-label">Savings</span><span class="kpi-val kpi-saved">' + fmtPct(t.savings_pct) + '</span></div>' +
      '</div>';

      const legend = '<div class="chart-legend">' +
        '<span class="lg-item"><span class="lg-swatch lg-line-orig"></span>Original (right)</span>' +
        '<span class="lg-item"><span class="lg-swatch lg-line-opt"></span>Optimized (right)</span>' +
        '<span class="lg-item"><span class="lg-swatch lg-col-saved"></span>Saved (left)</span>' +
      '</div>';

      const W = 720, H = 210, padL = 38, padR = 42, padT = 16, padB = 24;
      const plotW = W - padL - padR;
      const plotH = H - padT - padB;
      const n = hours.length;
      const slot = plotW / n;
      const colW = Math.max(4, slot * 0.5);
      const ySaved = (v) => padT + plotH - (maxSaved ? (v / maxSaved) * plotH : 0);
      const yLine = (v) => padT + plotH - (maxLine ? (v / maxLine) * plotH : 0);
      const cx = (i) => padL + slot * i + slot / 2;
      const yMax = padT + plotH;

      let grid = '';
      for (let g = 0; g <= 4; g++) {
        const gy = padT + (plotH / 4) * g;
        grid += '<line x1="' + padL + '" y1="' + gy.toFixed(1) + '" x2="' + (W - padR) + '" y2="' + gy.toFixed(1) + '" class="chart-grid" />';
      }

      let seps = '';
      let lastDate = null;
      hours.forEach((h, i) => {
        if (lastDate !== null && h.date !== lastDate) {
          const x = padL + slot * i;
          seps += '<line x1="' + x + '" y1="' + padT + '" x2="' + x + '" y2="' + yMax + '" class="chart-sep" />';
        }
        lastDate = h.date;
      });

      let axes = '';
      axes += '<line x1="' + padL + '" y1="' + padT + '" x2="' + padL + '" y2="' + yMax + '" class="axis" />';
      axes += '<line x1="' + (W - padR) + '" y1="' + padT + '" x2="' + (W - padR) + '" y2="' + yMax + '" class="axis" />';
      axes += '<text x="' + (padL - 5) + '" y="' + (padT + 3) + '" class="axis-label axis-left">tokens</text>';
      axes += '<text x="' + (padL - 4) + '" y="' + (padT + 12) + '" class="axis-label axis-left">' + fmtTokens(maxSaved) + '</text>';
      axes += '<text x="' + (W - padR + 5) + '" y="' + (padT + 3) + '" class="axis-label axis-right">tokens</text>';
      axes += '<text x="' + (W - padR + 4) + '" y="' + (padT + 12) + '" class="axis-label axis-right">' + fmtTokens(maxLine) + '</text>';
      axes += '<text x="' + (padL - 4) + '" y="' + (yMax) + '" class="axis-label axis-left">0</text>';
      axes += '<text x="' + (W - padR + 4) + '" y="' + (yMax) + '" class="axis-label axis-right">0</text>';

      let nowPill = '';
      let cols = '';
      hours.forEach((h, i) => {
        const sH = Math.max(((h.saved || 0) / (maxSaved || 1)) * plotH, maxSaved ? 1 : 0);
        const x = cx(i) - colW / 2;
        const cls = h.is_current ? 'chart-col is-current' : 'chart-col';
        const tip = h.hour + ':00 — orig ' + fmtTokens(h.original || 0) + ', opt ' + fmtTokens(h.optimized || 0) + ', saved ' + fmtTokens(h.saved || 0);
        cols += '<rect x="' + x.toFixed(1) + '" y="' + (padT + plotH - sH).toFixed(1) + '" width="' + colW.toFixed(1) + '" height="' + sH.toFixed(1) + '" class="' + cls + '" tabindex="0" data-tip="' + tip + '"></rect>';
        if (h.is_current) {
          nowPill = '<text x="' + cx(i).toFixed(1) + '" y="' + (padT - 4) + '" class="now-pill">now</text>';
        }
      });

      const linePts = (key, scale) => hours.map((h, i) => cx(i).toFixed(1) + ',' + scale(h[key] || 0).toFixed(1)).join(' ');
      const lineOrig = '<polyline points="' + linePts('original', yLine) + '" class="chart-line line-orig" />';
      const lineOpt = '<polyline points="' + linePts('optimized', yLine) + '" class="chart-line line-opt" />';

      let dots = '';
      hours.forEach((h, i) => {
        dots += '<circle cx="' + cx(i).toFixed(1) + '" cy="' + yLine(h.original || 0).toFixed(1) + '" r="2" class="dot-orig" data-tip="' + h.hour + ':00 — orig ' + fmtTokens(h.original || 0) + '" tabindex="0"></circle>';
        dots += '<circle cx="' + cx(i).toFixed(1) + '" cy="' + yLine(h.optimized || 0).toFixed(1) + '" r="2" class="dot-opt" data-tip="' + h.hour + ':00 — opt ' + fmtTokens(h.optimized || 0) + '" tabindex="0"></circle>';
      });

      let xlabels = '';
      hours.forEach((h, i) => {
        xlabels += '<text x="' + cx(i).toFixed(1) + '" y="' + (H - 7) + '" class="chart-xlabel">' + (h.is_current ? 'now' : h.hour) + '</text>';
      });

      const svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" class="combo-chart" preserveAspectRatio="none">' +
        grid + axes + seps + cols + lineOrig + lineOpt + dots + nowPill + xlabels + '</svg>';

      chart.innerHTML = kpi + legend + '<div class="chart-wrap">' + svg + '<div class="chart-tip" id="chart-tip"></div></div>';
      bindChartTooltip(chart);
    }
  }
}

function bindChartTooltip(scope) {
  const tip = scope.querySelector('#chart-tip');
  if (!tip) return;
  scope.querySelectorAll('[data-tip]').forEach(el => {
    const show = () => {
      tip.textContent = el.getAttribute('data-tip');
      tip.style.opacity = '1';
    };
    const move = (e) => {
      const r = scope.querySelector('.chart-wrap').getBoundingClientRect();
      tip.style.left = (e.clientX - r.left + 10) + 'px';
      tip.style.top = (e.clientY - r.top + 10) + 'px';
    };
    const hide = () => { tip.style.opacity = '0'; };
    el.addEventListener('mouseenter', show);
    el.addEventListener('mousemove', move);
    el.addEventListener('mouseleave', hide);
    el.addEventListener('focus', show);
    el.addEventListener('blur', hide);
  });
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
}

function refreshEmbedStatus() {
  const btn = document.getElementById('btn-embed-refresh');
  if (btn) { btn.disabled = true; btn.textContent = 'Refreshing…'; }
  Promise.all([
    fetch('/api/stats').then(r => r.ok ? r.json() : null),
    fetch('/health').then(r => r.ok ? r.json() : null),
  ]).then(([stats, health]) => {
    if (stats) render(stats);
    if (health) renderHealth(health, stats?.totals?.embed_queries);
  }).catch(() => {}).finally(() => {
    if (btn) { btn.disabled = false; btn.textContent = 'Refresh Model Status'; }
  });
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

function startPoll() {
  stopPoll();
  const view = document.querySelector('.sidebar nav a.active')?.dataset?.view;
  const pollSpanId = view === 'actions' ? 'actions-poll' : (view === 'recent-calls' ? 'recent-calls-poll' : null);
  if (pollSpanId) {
    const el = document.getElementById(pollSpanId);
    if (el) el.textContent = '(polling 5s)';
  }
  if (!document.hidden) pollTimer = setInterval(fetchData, 5000);
  pollBackoff = 1000;
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  const aEl = document.getElementById('actions-poll');
  if (aEl) aEl.textContent = '';
  const rEl = document.getElementById('recent-calls-poll');
  if (rEl) rEl.textContent = '';
}

document.addEventListener('visibilitychange', () => {
  const view = document.querySelector('.sidebar nav a.active')?.dataset?.view;
  const onPollView = view === 'actions' || view === 'recent-calls';
  if (document.hidden) { stopPoll(); }
  else if (onPollView) { startPoll(); }
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
