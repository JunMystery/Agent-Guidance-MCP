import { setText, el, emptyState } from '../dom.js';
import { fmtTokens, fmtPct, savingsBadge } from '../format.js';
import { renderHourlyChart } from './chart/index.js';
import { renderRecentCalls } from './recent.js';
import { makeSortable, filterRows, bindFilter } from '../interactions.js';
import { store } from '../state.js';

export function renderDashboard(data) {
  const t = data.totals || {};

  setText('out-client-name', 'global');
  setText('out-session-label', 'per-call tracking');

  setText('sidebar-proj', 'project: ' + (data.project_path ? data.project_path.split('/').pop() : '--'));
  const projEl = el('sidebar-proj');
  if (projEl) projEl.title = data.project_path || '';
  setText('sidebar-port', 'port: ' + (data.server_port || '--'));
  setText('sys-project', data.project_path || '--');
  setText('sys-version', data.version || '--');
  setText('sys-db-status', data.db_status || '--');

  setText('out-tool-calls', t.tool_calls || 0);
  setText('out-skills-loaded', t.skills_loaded || 0);
  setText('out-embed-queries', t.embed_queries || 0);

  setText('out-original-tokens', fmtTokens(t.tokens_original));
  setText('out-optimized-tokens', fmtTokens(t.tokens_optimized));
  setText('out-token-savings', fmtTokens(t.token_savings) + ' (' + fmtPct(t.savings_pct) + ' savings)');

  renderSkillsTable(data.top_skills);
  renderActionsTable(data.tool_breakdown);
  renderHourlyChart(data, t);
  renderRecentCalls(data.recent_actions);
}

function renderSkillsTable(topSkills) {
  const body = el('dash-skills');
  if (!body) return;
  body.innerHTML = '';
  if (topSkills && topSkills.length) {
    topSkills.slice(0, 10).forEach(sk => {
      body.innerHTML += '<tr><td>' + sk.skill_id + '</td><td>' + sk.cnt + '</td></tr>';
    });
  } else {
    emptyState('dash-skills', 2, 'No skills loaded yet.');
  }
}

function renderActionsTable(toolBreakdown) {
  store.tool_breakdown = (toolBreakdown || []).map(r => {
    const saved = (r.tok_orig || 0) - (r.tok_opt || 0);
    return { ...r, savings: saved, status: r.error_message ? 'error' : 'ok' };
  });
  bindFilter('actions-filter', () => drawActionsTable());
  makeSortable('actions-body', store.tool_breakdown);
  drawActionsTable();
}

function drawActionsTable() {
  const body = el('actions-body');
  if (!body) return;
  const query = el('actions-filter')?.value || '';
  const rows = filterRows(store.tool_breakdown, query, ['tool_name', 'operation']);
  body.innerHTML = '';
  if (rows.length) {
    rows.forEach(r => {
      const saved = r.savings;
      const { pct, badgeClass } = savingsBadge(saved, r.tok_orig);
      body.innerHTML += '<tr><td>' + r.tool_name + '</td><td>' + (r.operation || '--') + '</td><td>' + r.cnt + '</td><td>' + fmtTokens(r.tok_orig) + '</td><td>' + fmtTokens(r.tok_opt) + '</td><td><span class="' + badgeClass + '">' + pct + '%</span></td></tr>';
    });
  } else {
    emptyState('actions-body', 6, 'No matching tool calls.');
  }
}


