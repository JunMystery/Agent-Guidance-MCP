import { fmtTokens, fmtPct } from './format.js';
import { el } from './dom.js';

export function renderHourlyChart(data, totals) {
  const chart = el('hourly-chart');
  if (!chart) return;

  const hours = (data.hourly_savings || []);
  const maxSaved = hours.reduce((m, h) => Math.max(m, h.saved || 0), 0);
  const maxLine = hours.reduce((m, h) => Math.max(m, h.original || 0, h.optimized || 0), 0);

  if (!hours.length || (maxSaved === 0 && maxLine === 0)) {
    chart.innerHTML = '<div class="chart-empty">No token data in the last 24h — make a tool call to start saving tokens.</div>';
    return;
  }

  chart.innerHTML = buildChartHtml(chart, hours, maxSaved, maxLine, totals);
  bindChartTooltip(chart);
}

const W = 720, H = 210, padL = 38, padR = 42, padT = 16, padB = 24;

function buildChartHtml(chart, hours, maxSaved, maxLine, t) {
  const kpi = buildKpi(t);
  const legend = buildLegend();

  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const n = hours.length;
  const slot = plotW / n;
  const colW = Math.max(4, slot * 0.5);
  const ySaved = (v) => padT + plotH - (maxSaved ? (v / maxSaved) * plotH : 0);
  const yLine = (v) => padT + plotH - (maxLine ? (v / maxLine) * plotH : 0);
  const cx = (i) => padL + slot * i + slot / 2;
  const yMax = padT + plotH;

  const grid = buildGrid();
  const seps = buildDaySeps(hours, slot, padL, padT, yMax);
  const axes = buildAxes(yMax, maxSaved, maxLine);
  const cols = buildCols(hours, cx, colW, padT, plotH, maxSaved);
  const lines = buildLines(hours, cx, yLine);
  const dots = buildDots(hours, cx, yLine);
  const xlabels = buildXLabels(hours, cx, H);

  let nowPill = '';
  hours.forEach((h, i) => {
    if (h.is_current) nowPill = '<text x="' + cx(i).toFixed(1) + '" y="' + (padT - 4) + '" class="now-pill">now</text>';
  });

  const svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" class="combo-chart" preserveAspectRatio="none">' +
    grid + axes + seps + cols + lines + dots + nowPill + xlabels + '</svg>';

  return kpi + legend + '<div class="chart-wrap">' + svg + '<div class="chart-tip" id="chart-tip"></div></div>';
}

function buildKpi(t) {
  return '<div class="savings-kpi">' +
    '<div class="kpi"><span class="kpi-label">Original</span><span class="kpi-val">' + fmtTokens(t.tokens_original) + '</span></div>' +
    '<div class="kpi"><span class="kpi-label">Optimized</span><span class="kpi-val">' + fmtTokens(t.tokens_optimized) + '</span></div>' +
    '<div class="kpi"><span class="kpi-label">Saved</span><span class="kpi-val kpi-saved">' + fmtTokens(t.token_savings) + '</span></div>' +
    '<div class="kpi"><span class="kpi-label">Savings</span><span class="kpi-val kpi-saved">' + fmtPct(t.savings_pct) + '</span></div>' +
    '</div>';
}

function buildLegend() {
  return '<div class="chart-legend">' +
    '<span class="lg-item"><span class="lg-swatch lg-line-orig"></span>Original (right)</span>' +
    '<span class="lg-item"><span class="lg-swatch lg-line-opt"></span>Optimized (right)</span>' +
    '<span class="lg-item"><span class="lg-swatch lg-col-saved"></span>Saved (left)</span>' +
    '</div>';
}

function buildGrid() {
  let grid = '';
  const plotH = H - padT - padB;
  for (let g = 0; g <= 4; g++) {
    const gy = padT + (plotH / 4) * g;
    grid += '<line x1="' + padL + '" y1="' + gy.toFixed(1) + '" x2="' + (W - padR) + '" y2="' + gy.toFixed(1) + '" class="chart-grid" />';
  }
  return grid;
}

function buildDaySeps(hours, slot, padL, padT, yMax) {
  let seps = '';
  let lastDate = null;
  hours.forEach((h, i) => {
    if (lastDate !== null && h.date !== lastDate) {
      const x = padL + slot * i;
      seps += '<line x1="' + x + '" y1="' + padT + '" x2="' + x + '" y2="' + yMax + '" class="chart-sep" />';
    }
    lastDate = h.date;
  });
  return seps;
}

function buildAxes(yMax, maxSaved, maxLine) {
  let axes = '';
  axes += '<line x1="' + padL + '" y1="' + padT + '" x2="' + padL + '" y2="' + yMax + '" class="axis" />';
  axes += '<line x1="' + (W - padR) + '" y1="' + padT + '" x2="' + (W - padR) + '" y2="' + yMax + '" class="axis" />';
  axes += '<text x="' + (padL - 5) + '" y="' + (padT + 3) + '" class="axis-label axis-left">tokens</text>';
  axes += '<text x="' + (padL - 4) + '" y="' + (padT + 12) + '" class="axis-label axis-left">' + fmtTokens(maxSaved) + '</text>';
  axes += '<text x="' + (W - padR + 5) + '" y="' + (padT + 3) + '" class="axis-label axis-right">tokens</text>';
  axes += '<text x="' + (W - padR + 4) + '" y="' + (padT + 12) + '" class="axis-label axis-right">' + fmtTokens(maxLine) + '</text>';
  axes += '<text x="' + (padL - 4) + '" y="' + yMax + '" class="axis-label axis-left">0</text>';
  axes += '<text x="' + (W - padR + 4) + '" y="' + yMax + '" class="axis-label axis-right">0</text>';
  return axes;
}

function buildCols(hours, cx, colW, padT, plotH, maxSaved) {
  let cols = '';
  hours.forEach((h, i) => {
    const sH = Math.max(((h.saved || 0) / (maxSaved || 1)) * plotH, maxSaved ? 1 : 0);
    const x = cx(i) - colW / 2;
    const cls = h.is_current ? 'chart-col is-current' : 'chart-col';
    const tip = h.hour + ':00 — orig ' + fmtTokens(h.original || 0) + ', opt ' + fmtTokens(h.optimized || 0) + ', saved ' + fmtTokens(h.saved || 0);
    cols += '<rect x="' + x.toFixed(1) + '" y="' + (padT + plotH - sH).toFixed(1) + '" width="' + colW.toFixed(1) + '" height="' + sH.toFixed(1) + '" class="' + cls + '" tabindex="0" data-tip="' + tip + '"></rect>';
  });
  return cols;
}

function buildLines(hours, cx, yLine) {
  const linePts = (key) => hours.map((h, i) => cx(i).toFixed(1) + ',' + yLine(h[key] || 0).toFixed(1)).join(' ');
  const lineOrig = '<polyline points="' + linePts('original') + '" class="chart-line line-orig" />';
  const lineOpt = '<polyline points="' + linePts('optimized') + '" class="chart-line line-opt" />';
  return lineOrig + lineOpt;
}

function buildDots(hours, cx, yLine) {
  let dots = '';
  hours.forEach((h, i) => {
    dots += '<circle cx="' + cx(i).toFixed(1) + '" cy="' + yLine(h.original || 0).toFixed(1) + '" r="2" class="dot-orig" data-tip="' + h.hour + ':00 — orig ' + fmtTokens(h.original || 0) + '" tabindex="0"></circle>';
    dots += '<circle cx="' + cx(i).toFixed(1) + '" cy="' + yLine(h.optimized || 0).toFixed(1) + '" r="2" class="dot-opt" data-tip="' + h.hour + ':00 — opt ' + fmtTokens(h.optimized || 0) + '" tabindex="0"></circle>';
  });
  return dots;
}

function buildXLabels(hours, cx, H) {
  let xlabels = '';
  hours.forEach((h, i) => {
    xlabels += '<text x="' + cx(i).toFixed(1) + '" y="' + (H - 7) + '" class="chart-xlabel">' + (h.is_current ? 'now' : h.hour) + '</text>';
  });
  return xlabels;
}

function bindChartTooltip(scope) {
  const tip = scope.querySelector('#chart-tip');
  if (!tip) return;
  scope.querySelectorAll('[data-tip]').forEach(node => {
    const show = () => {
      tip.textContent = node.getAttribute('data-tip');
      tip.style.opacity = '1';
    };
    const move = (e) => {
      const r = scope.querySelector('.chart-wrap').getBoundingClientRect();
      tip.style.left = (e.clientX - r.left + 10) + 'px';
      tip.style.top = (e.clientY - r.top + 10) + 'px';
    };
    const hide = () => { tip.style.opacity = '0'; };
    node.addEventListener('mouseenter', show);
    node.addEventListener('mousemove', move);
    node.addEventListener('mouseleave', hide);
    node.addEventListener('focus', show);
    node.addEventListener('blur', hide);
  });
}
