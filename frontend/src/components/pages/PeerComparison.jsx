import { Star } from "lucide-react";

// column key -> [label, higherIsBetter, formatter]
const COLUMNS = [
  ["pe_ratio", "P/E Ratio", false, (v) => v.toFixed(2)],
  ["revenue_growth", "Revenue Growth", true, (v) => `${v.toFixed(1)}%`],
  ["profit_margin", "Profit Margin", true, (v) => `${v.toFixed(1)}%`],
  ["roe", "ROE", true, (v) => `${v.toFixed(1)}%`],
  ["debt_to_equity", "Debt-to-Equity", false, (v) => `${(v / 100).toFixed(2)}x`],
];

function bestWorst(companies, key, higherIsBetter) {
  const values = companies
    .map((c) => ({ ticker: c.ticker, value: c[key] }))
    .filter((entry) => typeof entry.value === "number");
  if (values.length < 2) return { best: null, worst: null };
  const sorted = [...values].sort((a, b) => (higherIsBetter ? b.value - a.value : a.value - b.value));
  return { best: sorted[0].ticker, worst: sorted[sorted.length - 1].ticker };
}

export default function PeerComparison({ data }) {
  const peerData = data.peer_data ?? {};
  const companies = peerData.companies ?? [];

  if (!peerData.success || companies.length === 0) {
    return (
      <div className="space-y-3">
        <h1 className="text-2xl font-extrabold text-gold">Peer Comparison</h1>
        <p className="text-gray-400">No peer comparison available for this ticker.</p>
      </div>
    );
  }

  const highlights = Object.fromEntries(
    COLUMNS.map(([key, , higherIsBetter]) => [key, bestWorst(companies, key, higherIsBetter)])
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-gold">Peer Comparison</h1>
        <p className="mt-1 text-sm text-gray-400">
          {peerData.sector} · {peerData.industry} · {companies.length - 1} peers via yfinance
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-navy-600">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-navy-600 bg-navy-800 text-left text-[11px] uppercase tracking-widest text-gray-400">
              <th className="px-4 py-3">Ticker</th>
              <th className="px-4 py-3">Company</th>
              {COLUMNS.map(([key, label]) => (
                <th key={key} className="px-4 py-3 text-right">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => {
              const isTarget = company.ticker === data.ticker;
              return (
                <tr
                  key={company.ticker}
                  className={`border-b border-navy-600/60 last:border-0 ${
                    isTarget ? "bg-gold/5" : "bg-navy-700"
                  }`}
                >
                  <td className="px-4 py-3 font-bold text-white">
                    <span className="flex items-center gap-1.5">
                      {isTarget && <Star size={13} className="fill-gold text-gold" />}
                      {company.ticker}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{company.company}</td>
                  {COLUMNS.map(([key, , , format]) => {
                    const value = company[key];
                    const { best, worst } = highlights[key];
                    const cellClass =
                      typeof value !== "number"
                        ? "text-gray-500"
                        : company.ticker === best
                          ? "rounded bg-success/15 font-bold text-success"
                          : company.ticker === worst
                            ? "rounded bg-danger/15 font-bold text-danger"
                            : "text-white";
                    return (
                      <td key={key} className="px-4 py-3 text-right">
                        <span className={`px-1.5 py-0.5 ${cellClass}`}>
                          {typeof value === "number" ? format(value) : "N/A"}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-500">
        <span className="text-success">Green</span> = best in class ·{" "}
        <span className="text-danger">Red</span> = worst in class · lower is better for P/E and
        Debt-to-Equity
      </p>
    </div>
  );
}
