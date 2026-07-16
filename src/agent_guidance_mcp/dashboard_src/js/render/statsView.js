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
  renderTokenBars(t);
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

function renderTokenBars(t) {
  const tokenBars = el('token-bars');
  if (!tokenBars) return;
  let barsHtml = '<h3 style="font-size:14px;margin-bottom:12px">Lifetime Summary</h3>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Original</span><div class="bar-track"><div class="bar-fill" style="width:100%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_original) + '</span></div>';
  const optW = t.tokens_original ? Math.round((t.tokens_optimized / t.tokens_original) * 100) : 0;
  barsHtml += '<div class="bar-row"><span class="bar-label">Optimized</span><div class="bar-track"><div class="bar-fill opt" style="width:' + optW + '%"></div></div><span class="bar-num">' + fmtTokens(t.tokens_optimized) + '</span></div>';
  barsHtml += '<div class="bar-row"><span class="bar-label">Saved</span><div class="bar-track"><div class="bar-fill" style="width:' + (100 - optW) + '%;background:var(--accent-secondary);opacity:0.6"></div></div><span class="bar-num" style="font-weight:700;color:var(--accent-secondary)">' + fmtTokens(t.token_savings) + '</span></div>';
  tokenBars.innerHTML = barsHtml;
}
