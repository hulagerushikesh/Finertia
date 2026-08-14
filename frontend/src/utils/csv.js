/**
 * Client-side CSV export. No backend round-trip — the browser already holds
 * every value the file needs.
 */

/** Quote a field only when it could otherwise break the row. */
function escape(value) {
  if (value === null || value === undefined) return "";
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function toCsv(rows) {
  return rows.map((row) => row.map(escape).join(",")).join("\n");
}

function download(filename, text) {
  const blob = new Blob([text], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // Revoking immediately can cancel the download in some browsers.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function slug(params) {
  return `${params.ticker}_${params.start}_${params.end}`.replace(/[^\w.-]/g, "");
}

/** Equity curve and benchmark, one row per bar. */
export function exportEquityCurve(result, params) {
  const rows = [["date", "strategy_equity", "benchmark_equity"]];
  result.equity_curve.forEach((p) => rows.push([p.date, p.strategy, p.benchmark]));
  download(`finertia_equity_${slug(params)}.csv`, toCsv(rows));
}

/** One row per position change. */
export function exportTrades(result, params) {
  const rows = [["date", "position", "daily_return", "equity"]];
  result.trades.forEach((t) => rows.push([t.date, t.position, t.daily_return, t.equity]));
  download(`finertia_trades_${slug(params)}.csv`, toCsv(rows));
}

/** Headline metrics plus the config that produced them. */
export function exportMetrics(result, params) {
  const rows = [["metric", "value"]];
  Object.entries(result.metrics).forEach(([k, v]) => rows.push([k, v]));
  rows.push([], ["parameter", "value"]);
  Object.entries(params).forEach(([k, v]) => rows.push([k, v]));
  download(`finertia_metrics_${slug(params)}.csv`, toCsv(rows));
}
