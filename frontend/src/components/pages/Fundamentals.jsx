import { Info } from "lucide-react";
import MetricCard from "../MetricCard.jsx";
import { parseNumeric, formatLargeNumber } from "../../utils/format.js";

function SectionGrid({ title, items }) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-gray-400">{title}</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map(([label, value]) => (
          <MetricCard key={label} label={label} value={value} decimals={2} />
        ))}
      </div>
    </div>
  );
}

export default function Fundamentals({ data }) {
  const f = data.fundamentals_data?.fundamentals ?? {};

  const large = (v) => {
    const n = parseNumeric(v);
    return n !== null ? formatLargeNumber(n) : (v ?? "N/A");
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-extrabold text-gold">Financial Fundamentals</h1>

      <SectionGrid
        title="Income Statement"
        items={[
          ["Revenue", large(f.revenue)],
          ["Net Income", large(f.net_income)],
          ["Free Cash Flow", large(f.free_cash_flow)],
          ["Operating Cash Flow", large(f.operating_cash_flow)],
        ]}
      />

      <SectionGrid
        title="Balance Sheet"
        items={[
          ["Total Assets", large(f.total_assets)],
          ["Total Liabilities", large(f.total_liabilities)],
          ["Total Equity", large(f.total_equity)],
          ["Total Debt", large(f.total_debt)],
        ]}
      />

      <SectionGrid
        title="Profitability"
        items={[
          ["Gross Margin", f.gross_margin],
          ["Operating Margin", f.operating_margin],
          ["Profit Margin", f.profit_margin],
          ["ROE", f.roe],
        ]}
      />

      <SectionGrid
        title="Valuation"
        items={[
          ["EPS", f.eps],
          ["P/E Ratio", f.pe_ratio],
          ["P/B Ratio", f.pb_ratio],
          ["Dividend Yield", f.dividend_yield],
        ]}
      />

      <SectionGrid
        title="Leverage & Liquidity"
        items={[
          ["Debt-to-Equity", f.debt_to_equity],
          ["Current Ratio", f.current_ratio],
          ["Quick Ratio", f.quick_ratio],
          ["Cash", large(f.cash)],
        ]}
      />

      {f.is_financial_sector && (
        <div className="flex gap-3 rounded-xl border border-sky-400/40 bg-sky-400/5 p-4 text-sm text-gray-300">
          <Info size={18} className="mt-0.5 shrink-0 text-sky-400" />
          <p>
            <strong className="text-white">Financial institution note:</strong> current and quick
            ratios are not reported by banks (no current/non-current balance-sheet split), gross
            margin is not a bank metric, and operating/free cash flow is dominated by lending flows
            — routinely large and negative. Bank leverage is formally assessed via regulatory
            capital (e.g., Tier 1 ratio); D/E here is total debt ÷ stockholders&apos; equity.
          </p>
        </div>
      )}
    </div>
  );
}
