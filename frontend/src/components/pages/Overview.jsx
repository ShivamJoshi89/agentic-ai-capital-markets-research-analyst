import MetricCard from "../MetricCard.jsx";
import PriceChart from "../PriceChart.jsx";
import { parseNumeric, formatLargeNumber } from "../../utils/format.js";

export default function Overview({ data }) {
  const info = data.company_info ?? {};
  const metrics = data.market_data?.metrics ?? {};
  const fundamentals = data.fundamentals_data?.fundamentals ?? {};

  const marketCap = parseNumeric(info.market_cap);

  const quickStats = [
    ["Sector", info.sector],
    ["Industry", info.industry],
    ["Exchange", info.exchange],
    ["Country", info.country],
    ["52-Week High", info["52_week_high"] != null ? `$${info["52_week_high"]}` : "N/A"],
    ["52-Week Low", info["52_week_low"] != null ? `$${info["52_week_low"]}` : "N/A"],
    ["Employees", info.employees != null ? Number(info.employees).toLocaleString() : "N/A"],
    ["Dividend Yield", fundamentals.dividend_yield],
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold text-gold">Overview</h1>

      {/* Hero metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Current Price" value={metrics.latest_price} prefix="$" />
        <MetricCard
          label={metrics.ytd_basis === "trailing_since_series_start" ? "Return (Since Start)" : "YTD Return"}
          value={metrics.ytd_return}
          suffix="%"
          signed
          sub={metrics.ytd_basis === "trailing_since_series_start" ? "No calendar-YTD base available yet" : null}
        />
        <MetricCard
          label="Market Cap"
          value={marketCap !== null ? marketCap / 1e9 : null}
          prefix="$"
          suffix="B"
          decimals={1}
        />
        <MetricCard label="P/E Ratio" value={fundamentals.pe_ratio} />
      </div>

      {/* Price chart */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-gray-400">
          1-Year Price &amp; Volume
        </h2>
        <PriceChart history={data.price_history} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Company description */}
        <div className="rounded-xl border border-navy-600 bg-navy-700 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gold">
            About {info.company_name ?? data.ticker}
          </h2>
          <p className="mt-3 max-h-64 overflow-y-auto text-sm leading-relaxed text-gray-300">
            {info.business_summary || "No company description available."}
          </p>
        </div>

        {/* Quick stats grid */}
        <div className="rounded-xl border border-navy-600 bg-navy-700 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gold">Quick Stats</h2>
          <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3">
            {quickStats.map(([label, value]) => (
              <div key={label} className="flex items-baseline justify-between gap-2 border-b border-navy-600/60 pb-2">
                <span className="text-xs text-gray-400">{label}</span>
                <span className="text-sm font-semibold text-white text-right">
                  {value ?? "N/A"}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-500">
            Market cap {formatLargeNumber(info.market_cap)} · Data via yfinance
          </div>
        </div>
      </div>
    </div>
  );
}
