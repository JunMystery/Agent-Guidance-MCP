// SVG string builders for the combo chart. Pure: inputs in, SVG string out.

import { fmtTokens } from '../format.js';
import { plotBox, slotCenter, columnWidth, CHART_W, CHART_H, PAD } from './scale.js';

export function buildGrid(box) {
  let grid = '';
  for (let g = 0; g <= 4; g++) {
    const gy = box.y0 + (box.h / 4) * g;
    grid += '<line x1="' + box.x0 + '" y1="' + gy.toFixed(1) + '" x2="' + (CHART_W - PAD.right) + '" y2="' + gy.toFixed(1) + '" class="chart-grid" />';
  }
  return grid;
}

export function buildDaySeps(hours, box) {
  let seps = '';
  let lastDate = null;
  const slot = box.w / hours.length;
  hours.forEach((h, i) => {
    if (lastDate !== null && h.date !== lastDate) {
      const x = box.x0 + slot * i;
      seps += '<line x1="' + x + '" y1="' + box.y0 + '" x2="' + x + '" y2="' + box.yMax + '" class="chart-sep" />';
    }
    lastDate = h.date;
  });
  return seps;
}

export function buildAxes(box, maxSaved, maxLine) {
  let axes = '';
  axes += '<line x1="' + box.x0 + '" y1="' + box.y0 + '" x2="' + box.x0 + '" y2="' + box.yMax + '" class="axis" />';
  axes += '<line x1="' + (CHART_W - PAD.right) + '" y1="' + box.y0 + '" x2="' + (CHART_W - PAD.right) + '" y2="' + box.yMax + '" class="axis" />';
  axes += '<text x="' + (box.x0 - 5) + '" y="' + (box.y0 + 3) + '" class="axis-label axis-left">tokens</text>';
  axes += '<text x="' + (box.x0 - 4) + '" y="' + (box.y0 + 12) + '" class="axis-label axis-left">' + fmtTokens(maxSaved) + '</text>';
  axes += '<text x="' + (CHART_W - PAD.right + 5) + '" y="' + (box.y0 + 3) + '" class="axis-label axis-right">tokens</text>';
  axes += '<text x="' + (CHART_W - PAD.right + 4) + '" y="' + (box.y0 + 12) + '" class="axis-label axis-right">' + fmtTokens(maxLine) + '</text>';
  axes += '<text x="' + (box.x0 - 4) + '" y="' + box.yMax + '" class="axis-label axis-left">0</text>';
  axes += '<text x="' + (CHART_W - PAD.right + 4) + '" y="' + box.yMax + '" class="axis-label axis-right">0</text>';
  return axes;
}

export function buildCols(hours, box, ySaved, maxSaved) {
  let cols = '';
  const colW = columnWidth(hours.length, box);
  hours.forEach((h, i) => {
    const sH = Math.max(((h.saved || 0) / (maxSaved || 1)) * box.h, maxSaved ? 1 : 0);
    const x = slotCenter(i, hours.length, box) - colW / 2;
    const cls = h.is_current ? 'chart-col is-current' : 'chart-col';
    const tip = h.hour + ':00 — orig ' + fmtTokens(h.original || 0) + ', opt ' + fmtTokens(h.optimized || 0) + ', saved ' + fmtTokens(h.saved || 0);
    cols += '<rect x="' + x.toFixed(1) + '" y="' + (box.y0 + box.h - sH).toFixed(1) + '" width="' + colW.toFixed(1) + '" height="' + sH.toFixed(1) + '" class="' + cls + '" tabindex="0" data-tip="' + tip + '"></rect>';
  });
  return cols;
}

export function buildLines(hours, box, yLine) {
  const linePts = (key) => hours.map((h, i) => slotCenter(i, hours.length, box).toFixed(1) + ',' + yLine(h[key] || 0).toFixed(1)).join(' ');
  const lineOrig = '<polyline points="' + linePts('original') + '" class="chart-line line-orig" />';
  const lineOpt = '<polyline points="' + linePts('optimized') + '" class="chart-line line-opt" />';
  return lineOrig + lineOpt;
}

export function buildDots(hours, box, yLine) {
  let dots = '';
  hours.forEach((h, i) => {
    const cx = slotCenter(i, hours.length, box).toFixed(1);
    dots += '<circle cx="' + cx + '" cy="' + yLine(h.original || 0).toFixed(1) + '" r="2" class="dot-orig" data-tip="' + h.hour + ':00 — orig ' + fmtTokens(h.original || 0) + '" tabindex="0"></circle>';
    dots += '<circle cx="' + cx + '" cy="' + yLine(h.optimized || 0).toFixed(1) + '" r="2" class="dot-opt" data-tip="' + h.hour + ':00 — opt ' + fmtTokens(h.optimized || 0) + '" tabindex="0"></circle>';
  });
  return dots;
}

export function buildXLabels(hours, box) {
  let xlabels = '';
  hours.forEach((h, i) => {
    xlabels += '<text x="' + slotCenter(i, hours.length, box).toFixed(1) + '" y="' + (CHART_H - 7) + '" class="chart-xlabel">' + (h.is_current ? 'now' : h.hour) + '</text>';
  });
  return xlabels;
}

export function buildNowPill(hours, box) {
  let pill = '';
  hours.forEach((h, i) => {
    if (h.is_current) pill = '<text x="' + slotCenter(i, hours.length, box).toFixed(1) + '" y="' + (box.y0 - 4) + '" class="now-pill">now</text>';
  });
  return pill;
}
