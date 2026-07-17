export function timeAgo(ts) {
  const sec = Math.floor((Date.now() / 1000) - ts);
  if (sec < 60) return sec + 's ago';
  if (sec < 3600) return Math.floor(sec / 60) + 'm ago';
  if (sec < 86400) return Math.floor(sec / 3600) + 'h ago';
  return Math.floor(sec / 86400) + 'd ago';
}

export function fmtTokens(n) {
  if (!n) return '0';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}

export function fmtPct(n) {
  return (n || 0).toFixed(1) + '%';
}

export function fmtDuration(sec) {
  if (sec < 60) return sec + 's';
  if (sec < 3600) return Math.floor(sec / 60) + 'm ' + (sec % 60) + 's';
  if (sec < 86400) return Math.floor(sec / 3600) + 'h ' + Math.floor((sec % 3600) / 60) + 'm';
  return Math.floor(sec / 86400) + 'd ' + Math.floor((sec % 86400) / 3600) + 'h';
}

export function fmtDurationMs(ms) {
  if (!ms) return '--';
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return h + 'h ' + m + 'm ' + s + 's';
}

export function savingsBadge(saved, orig) {
  const pct = orig ? ((saved / orig) * 100).toFixed(1) : '0.0';
  const pctNum = parseFloat(pct);
  const badgeClass = pctNum > 50 ? 'badge green' : (pctNum > 20 ? 'badge' : 'badge red');
  return { pct, badgeClass };
}
