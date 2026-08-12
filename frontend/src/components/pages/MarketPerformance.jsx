import MetricCard from "../MetricCard.jsx";
import PriceChart from "../PriceChart.jsx";
import { parseNumeric } from "../../utils/format.js";

export default function MarketPerformance({ data }) {
  const metrics = data.market_data?.metrics ?? {};
  const avgVolume = parseNumeric(metrics.avg_volume);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold text-gold">Market Performance</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="1-Month Return" value={metrics.one_month_return} suffix="%" signed />
        <MetricCard label="3-Month Return" value={metrics.three_month_return} suffix="%" signed />
        <MetricCard label="6-Month Return" value={metrics.six_month_return} suffix="%" signed />
        <MetricCard
          label={metrics.ytd_basis === "trailing_since_series_start" ? "Return (Since Start)" : "YTD Return"}
          value={metrics.ytd_return}
          suffix="%"
          signed
          sub={metrics.ytd_basis === "trailing_since_series_start" ? "No calendar-YTD base available yet" : null}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Volatility (Annual)" value={metrics.volatility} suffix="%" />
        <MetricCard label="Max Drawdown" value={metrics.max_drawdown} suffix="%" signed />
        <MetricCard
          label="Avg Volume"
          value={avgVolume !== null ? avgVolume / 1e6 : null}
          suffix="M"
          decimals={1}
        />
        <MetricCard label="Latest Price" value={metrics.latest_price} prefix="$" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard label="20-Day MA" value={metrics.ma_20} prefix="$" />
        <MetricCard label="50-Day MA" value={metrics.ma_50} prefix="$" />
        <MetricCard label="200-Day MA" value={metrics.ma_200} prefix="$" />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-gray-400">
          1-Year Price &amp; Volume
        </h2>
        <PriceChart history={data.price_history} />
      </div>
    </div>
  );
}
