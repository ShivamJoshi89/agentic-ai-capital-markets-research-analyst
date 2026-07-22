/** Parse a number out of API-formatted strings like "34.92%", "3.68x",
 *  "186,328,006,656", "$347.28". Returns null for N/A / non-numeric. */
export function parseNumeric(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const cleaned = String(value).replace(/[$%x\s,]/g, "");
  if (cleaned === "" || cleaned.toUpperCase().startsWith("N/A")) return null;
  // Number() (not parseFloat) so partially-numeric strings like "$186.3B"
  // or "3.7% YoY" render as-is instead of losing their suffix
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

/** 922665484288 -> "$922.7B" */
export function formatLargeNumber(value) {
  const n = parseNumeric(value);
  if (n === null) return "N/A";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toFixed(2)}`;
}

/** Compact date for chart axes: "2026-07-22" -> "Jul '26" */
export function formatChartDate(dateStr) {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" }).replace(" ", " '");
}
