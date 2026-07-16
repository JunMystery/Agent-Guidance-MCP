import { setText, setDisplay, setLoading, activeView, pollSpanFor } from './dom.js';
import { renderDashboard } from './render/statsView.js';
import { renderHealthPanel } from './render/health.js';
import { renderEmbedRecentTable } from './render/recent.js';
import { pollBackoff, setBackoff, resetBackoff } from './state.js';

async function fetchStats() {
  const resp = await fetch('/api/stats?window=24h');
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  return resp.json();
}

async function fetchHealth() {
  const resp = await fetch('/health');
  return resp.json();
}

async function showFetchError(e) {
  setBackoff(Math.min(pollBackoff * 2, 30000));
  setText('error-banner', 'Failed to connect to stats: ' + (e.message || 'unknown'));
  setDisplay('error-banner', 'block');
  const pollSpanId = pollSpanFor(activeView());
  if (pollSpanId) {
    setText(pollSpanId, '(retry in ' + (pollBackoff / 1000).toFixed(0) + 's)');
  }
}

async function clearFetchError() {
  resetBackoff();
  setText('error-banner', '');
  setDisplay('error-banner', 'none');
}

export async function fetchData() {
  setLoading(true);
  let data;
  try {
    data = await fetchStats();
    renderDashboard(data);
    await clearFetchError();
  } catch (e) {
    console.error('fetch error', e);
    await showFetchError(e);
  }
  try {
    const hdata = await fetchHealth();
    renderHealthPanel(hdata, data?.totals?.embed_queries);
  } catch (e) {
    renderHealthPanel({ status: 'unknown' }, data?.totals?.embed_queries);
  }
  renderEmbedRecentTable(data);
  setLoading(false);
}

export async function refreshEmbedStatus() {
  const btn = document.getElementById('btn-embed-refresh');
  if (btn) { btn.disabled = true; btn.textContent = 'Refreshing…'; }
  try {
    const [stats, health] = await Promise.all([fetchStats().catch(() => null), fetchHealth().catch(() => null)]);
    if (stats) renderDashboard(stats);
    if (health) renderHealthPanel(health, stats?.totals?.embed_queries);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Refresh Model Status'; }
  }
}
