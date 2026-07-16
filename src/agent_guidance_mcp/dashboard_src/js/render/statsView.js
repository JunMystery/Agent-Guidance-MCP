import { setText, el } from '../dom.js';
import { fmtTokens, fmtPct, savingsBadge } from '../format.js';
import { renderHourlyChart } from './chart.js';
import { renderRecentCalls } from './recent.js';

export function renderDashboard(data) {
  const t = data.totals || {};

  setText('out-client-name', 'global');
  setText('out-session-label', 'per-call tracking');

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
    body.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted)">No skills loaded yet</td></tr>';
  }
}

function renderActionsTable(toolBreakdown) {
  const body = el('actions-body');
  if (!body) return;
  body.innerHTML = '';
  if (toolBreakdown && toolBreakdown.length) {
    toolBreakdown.forEach(r => {
      const saved = (r.tok_orig || 0) - (r.tok_opt || 0);
      const { pct, badgeClass } = savingsBadge(saved, r.tok_orig);
      body.innerHTML += '<tr><td>' + r.tool_name + '</td><td>' + (r.operation || '--') + '</td><td>' + r.cnt + '</td><td>' + fmtTokens(r.tok_orig) + '</td><td>' + fmtTokens(r.tok_opt) + '</td><td><span class="' + badgeClass + '">' + pct + '%</span></td></tr>';
    });
  } else {
    body.innerHTML = '<tr><td colspan="6" style="color:var(--text-muted)">No tool calls recorded yet</td></tr>';
  }
}


