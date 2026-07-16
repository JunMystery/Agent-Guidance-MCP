// KPI + legend blocks shown above the chart SVG.

import { fmtTokens, fmtPct } from '../format.js';

export function buildKpi(t) {
  return '<div class="savings-kpi">' +
    '<div class="kpi"><span class="kpi-label">Original</span><span class="kpi-val">' + fmtTokens(t.tokens_original) + '</span></div>' +
    '<div class="kpi"><span class="kpi-label">Optimized</span><span class="kpi-val">' + fmtTokens(t.tokens_optimized) + '</span></div>' +
    '<div class="kpi"><span class="kpi-label">Saved</span><span class="kpi-val kpi-saved">' + fmtTokens(t.token_savings) + '</span></div>' +
    '<div class="kpi"><span class="kpi-label">Savings</span><span class="kpi-val kpi-saved">' + fmtPct(t.savings_pct) + '</span></div>' +
    '</div>';
}

export function buildLegend() {
  return '<div class="chart-legend">' +
    '<span class="lg-item"><span class="lg-swatch lg-line-orig"></span>Original (right)</span>' +
    '<span class="lg-item"><span class="lg-swatch lg-line-opt"></span>Optimized (right)</span>' +
    '<span class="lg-item"><span class="lg-swatch lg-col-saved"></span>Saved (left)</span>' +
    '</div>';
}
