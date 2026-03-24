export function formatNumber(n, decimals = 2) {
  if (n == null || isNaN(n)) return '—';
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(decimals) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(decimals) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(decimals) + 'K';
  return Number(n).toFixed(decimals);
}

export function formatPercent(n, decimals = 2) {
  if (n == null || isNaN(n)) return '—';
  const prefix = n > 0 ? '+' : '';
  return prefix + Number(n).toFixed(decimals) + '%';
}

export function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function severityColor(severity) {
  const map = { critical: 'var(--red)', warning: 'var(--orange)', info: 'var(--accent)', neutral: 'var(--text-muted)' };
  return map[severity] || map.neutral;
}
