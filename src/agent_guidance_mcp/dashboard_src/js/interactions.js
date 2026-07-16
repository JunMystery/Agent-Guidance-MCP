// Client-side table sorting + text filtering. State-light, no framework.

import { qsa } from './dom.js';

// Sort state per table id: { key, dir }
const sortState = {};

export function makeSortable(tbodyId, rows) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  const headers = tbody.closest('table')?.querySelectorAll('th[data-sort]');
  if (!headers) return;
  headers.forEach(th => {
    if (th.dataset.sortBound) return;
    th.dataset.sortBound = '1';
    th.setAttribute('role', 'columnheader');
    th.setAttribute('tabindex', '0');
    th.addEventListener('click', () => toggleSort(tbodyId, rows, th.dataset.sort));
    th.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSort(tbodyId, rows, th.dataset.sort); }
    });
  });
  applySort(tbodyId, rows);
}

function toggleSort(tbodyId, rows, key) {
  const prev = sortState[tbodyId] || { key: null, dir: 1 };
  const dir = prev.key === key ? -prev.dir : 1;
  sortState[tbodyId] = { key, dir };
  applySort(tbodyId, rows);
  qsa(`#${tbodyId}`).forEach(() => {});
  const tbody = document.getElementById(tbodyId);
  tbody?.closest('table')?.querySelectorAll('th[data-sort]').forEach(th => {
    th.classList.toggle('sorted', th.dataset.sort === key);
    th.setAttribute('aria-sort', th.dataset.sort === key ? (dir === 1 ? 'ascending' : 'descending') : 'none');
  });
}

function applySort(tbodyId, rows) {
  const st = sortState[tbodyId];
  if (!st || !st.key) return;
  rows.sort((a, b) => {
    const av = a[st.key], bv = b[st.key];
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * st.dir;
    return String(av).localeCompare(String(bv)) * st.dir;
  });
}

export function filterRows(rows, query, fields) {
  if (!query) return rows;
  const q = query.toLowerCase();
  return rows.filter(r => fields.some(f => String(r[f] ?? '').toLowerCase().includes(q)));
}

export function bindFilter(inputId, onInput) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.addEventListener('input', () => onInput(input.value));
}
