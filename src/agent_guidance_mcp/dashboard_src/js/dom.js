export function qs(s) { return document.querySelector(s); }
export function qsa(s) { return document.querySelectorAll(s); }
export function el(id) { return document.getElementById(id); }

export function setText(id, val) {
  const node = el(id);
  if (node) node.textContent = val;
}

export function setDisplay(id, val) {
  const node = el(id);
  if (node) node.style.display = val;
}

export function activeView() {
  return qs('.sidebar nav a.active')?.dataset?.view;
}

export function pollSpanFor(view) {
  if (view === 'actions') return 'actions-poll';
  if (view === 'recent-calls') return 'recent-calls-poll';
  return null;
}
