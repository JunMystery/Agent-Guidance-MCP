import { setText } from '../dom.js';
import { timeAgo, fmtDuration } from '../format.js';

export function renderHealthPanel(h, embedQueries) {
  const modelLoaded = h.model_loaded !== undefined ? h.model_loaded : null;
  const clients = h.clients !== undefined ? h.clients : null;

  setText('sys-daemon', h.status === 'ok' ? 'running' : 'stopped');
  setText('sys-model', modelLoaded === null ? 'unknown' : (modelLoaded ? 'loaded' : 'unloaded'));
  setText('sys-clients', clients === null ? '0' : String(clients));

  const modelStatus = modelLoaded === null ? 'unknown' : (modelLoaded ? 'loaded' : 'unloaded');
  setText('out-daemon-status', h.status === 'ok' ? 'running' : 'stopped');
  setText('out-model-status', modelStatus);
  setText('out-engine', h.engine || 'unknown');
  setText('out-embed-queries', String(embedQueries || 0));
  setText('out-embed-metrics-queries', String(embedQueries || 0));
  setText('out-uptime', h.uptime_seconds ? fmtDuration(h.uptime_seconds) : '--');
  setText('out-clients', clients === null ? '0' : String(clients));
  setText('out-last-embed', h.last_embed_time ? timeAgo(h.last_embed_time) : '--');

  setText('sys-embed-model', modelStatus);
  setText('sys-embed-daemon', h.status === 'ok' ? 'running' : 'stopped');
  setText('sys-embed-clients', clients === null ? '0' : String(clients));
  setText('sys-embed-backend', h.backend || 'unknown');
}
