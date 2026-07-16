import { el, emptyState } from '../dom.js';
import { fmtTokens, savingsBadge } from '../format.js';
import { timeAgo } from '../format.js';
import { makeSortable, filterRows, bindFilter } from '../interactions.js';
import { store } from '../state.js';

export function renderRecentCalls(recentActions) {
  store.recent_actions = (recentActions || []).map(r => {
    const saved = (r.tokens_original || 0) - (r.tokens_optimized || 0);
    return { ...r, savings: saved, status: r.error_message ? 'error' : 'ok' };
  });
  bindFilter('recent-filter', () => drawRecentCalls());
  makeSortable('recent-calls-body', store.recent_actions);
  drawRecentCalls();
}

function drawRecentCalls() {
  const body = el('recent-calls-body');
  if (!body) return;
  const query = el('recent-filter')?.value || '';
  const rows = filterRows(store.recent_actions, query, ['tool_name', 'operation', 'status']);
  body.innerHTML = '';
  if (rows.length) {
    rows.forEach(r => {
      const saved = r.savings;
      const { pct, badgeClass } = savingsBadge(saved, r.tokens_original);
      const duration = r.duration_ms ? r.duration_ms + 'ms' : '--';
      const statusClass = r.error_message ? 'badge red' : 'badge green';
      const statusText = r.error_message ? 'error' : 'ok';
      const statusTitle = r.error_message ? ' title="' + r.error_message.replace(/"/g, '&quot;') + '"' : '';
      body.innerHTML += '<tr>' +
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
    emptyState('recent-calls-body', 8, 'No matching calls.');
  }
}

export function renderEmbedRecentTable(data) {
  const body = el('embed-recent-body');
  if (!body) return;
  const rows = (data && data.embed_recent) || [];
  if (!rows.length) {
    emptyState('embed-recent-body', 4, 'No embed queries yet.');
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
