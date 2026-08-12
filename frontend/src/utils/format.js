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

/** 922665484288 -> "$922.7B". `prefix` defaults to "$" for USD (the vast
 *  majority of figures in this app), but must be overridden to a non-"$"
 *  value (or "") for a figure that isn't actually USD-denominated - e.g. a
 *  foreign issuer's financials when no FX rate was available to convert
 *  them (see Fundamentals.jsx's use of fx_conversion). Never call this on
 *  a non-USD figure with the default prefix. */
export function formatLargeNumber(value, prefix = "$") {
  const n = parseNumeric(value);
  if (n === null) return "N/A";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${prefix}${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${prefix}${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${prefix}${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${prefix}${(n / 1e3).toFixed(1)}K`;
  return `${prefix}${n.toFixed(2)}`;
}

/** Data-quality sub-label for a margin card. Warns when the displayed value
 *  is Yahoo's precomputed fallback (basis "info_fallback") - which the audit
 *  found unreliable for some filers - rather than a local income-statement
 *  recompute. Returns null when the value is N/A (e.g. a bank's gross margin)
 *  or was computed locally. Mirrors the pb_ratio_basis "Unverified" pattern. */
export function marginBasisNote(value, basis) {
  if (value == null || value === "N/A") return null;
  return basis === "info_fallback" ? "Unverified — Yahoo value" : null;
}

/** Data-quality sub-label for the ROE card. Warns when ROE used a point-in-
 *  time equity base (too little history for the standard year-ago average)
 *  instead of the standard basis. Returns null for "year_ago_average". */
export function roeBasisNote(basis) {
  return basis && basis !== "year_ago_average" ? "Point-in-time basis (limited history)" : null;
}

/** Compact date for chart axes: "2026-07-22" -> "Jul '26" */
export function formatChartDate(dateStr) {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" }).replace(" ", " '");
}
