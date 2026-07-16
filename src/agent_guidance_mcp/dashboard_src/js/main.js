import { qsa, el } from './dom.js';
import { fetchData, refreshEmbedStatus } from './api.js';
import { startPoll, stopPoll } from './poll.js';

function onViewClick(a, e) {
  e.preventDefault();
  qsa('.sidebar nav a').forEach(x => x.classList.remove('active'));
  a.classList.add('active');
  qsa('main section').forEach(s => s.classList.add('hidden'));
  const view = el('view-' + a.dataset.view);
  if (view) view.classList.remove('hidden');
  if (a.dataset.view === 'actions' || a.dataset.view === 'recent-calls') startPoll();
  else stopPoll();
}

function initRouter() {
  qsa('.sidebar nav a').forEach(a => {
    a.addEventListener('click', e => onViewClick(a, e));
  });
  fetchData();
}

export function toggleSidebar() {
  el('sidebar').classList.toggle('open');
}

document.addEventListener('DOMContentLoaded', () => {
  initRouter();
  qsa('.sidebar nav a').forEach(a => {
    a.addEventListener('click', () => {
      if (window.innerWidth <= 768) el('sidebar').classList.remove('open');
    });
  });
});

document.addEventListener('visibilitychange', () => {
  const view = document.querySelector('.sidebar nav a.active')?.dataset?.view;
  const onPollView = view === 'actions' || view === 'recent-calls';
  if (document.hidden) stopPoll();
  else if (onPollView) startPoll();
});

window.toggleSidebar = toggleSidebar;
window.refreshEmbedStatus = refreshEmbedStatus;
