// Hourly savings combo chart orchestrator. Public API: renderHourlyChart(data, totals).

import { el } from '../dom.js';
import { plotBox, maxOf, linScale } from './scale.js';
import {
  buildGrid, buildDaySeps, buildAxes, buildCols, buildLines, buildDots, buildXLabels, buildNowPill,
} from './builders.js';
import { buildKpi, buildLegend } from './kpi.js';
import { bindChartTooltip } from './tooltip.js';
import { CHART_W, CHART_H } from './scale.js';

export function renderHourlyChart(data, totals) {
  const chart = el('hourly-chart');
  if (!chart) return;

  const hours = (data.hourly_savings || []);
  const maxSaved = maxOf(hours, ['saved']);
  const maxLine = maxOf(hours, ['original', 'optimized']);

  if (!hours.length || (maxSaved === 0 && maxLine === 0)) {
    chart.innerHTML = '<div class="chart-empty">No token data in the last 24h — make a tool call to start saving tokens.</div>';
    return;
  }

  chart.innerHTML = buildChartHtml(hours, maxSaved, maxLine, totals);
  bindChartTooltip(chart);
}

function buildChartHtml(hours, maxSaved, maxLine, t) {
  const box = plotBox();
  const ySaved = linScale(maxSaved, box.y0, box.yMax);
  const yLine = linScale(maxLine, box.y0, box.yMax);

  const grid = buildGrid(box);
  const seps = buildDaySeps(hours, box);
  const axes = buildAxes(box, maxSaved, maxLine);
  const cols = buildCols(hours, box, ySaved, maxSaved);
  const lines = buildLines(hours, box, yLine);
  const dots = buildDots(hours, box, yLine);
  const xlabels = buildXLabels(hours, box);
  const nowPill = buildNowPill(hours, box);

  const svg = '<svg viewBox="0 0 ' + CHART_W + ' ' + CHART_H + '" class="combo-chart" preserveAspectRatio="none">' +
    grid + axes + seps + cols + lines + dots + nowPill + xlabels + '</svg>';

  return buildKpi(t) + buildLegend() + '<div class="chart-wrap">' + svg + '<div class="chart-tip" id="chart-tip"></div></div>';
}
