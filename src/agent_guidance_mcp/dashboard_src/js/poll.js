import { el, activeView, pollSpanFor } from './dom.js';
import { resetBackoff } from './state.js';
import { fetchData } from './api.js';

let pollTimer = null;

export function startPoll() {
  stopPoll();
  const spanId = pollSpanFor(activeView());
  if (spanId) {
    const node = el(spanId);
    if (node) node.textContent = '(polling 5s)';
  }
  if (!document.hidden) pollTimer = setInterval(fetchData, 5000);
  resetBackoff();
}

export function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  const aEl = el('actions-poll');
  if (aEl) aEl.textContent = '';
  const rEl = el('recent-calls-poll');
  if (rEl) rEl.textContent = '';
}
