import MetricCard from "../MetricCard.jsx";

const ANALYSIS_LABELS = [
  ["interest_rates", "Interest Rate Environment"],
  ["treasury_impact", "Treasury Yields"],
  ["inflation_impact", "Inflation Outlook"],
  ["labor_market", "Labor Market"],
];

export default function MacroEnvironment({ data }) {
  const macro = data.macro_data ?? {};
  const indicators = macro.indicators ?? {};
  const analysis = macro.analysis ?? {};

  if (!macro.success) {
    return (
      <div className="space-y-3">
        <h1 className="text-2xl font-extrabold text-gold">Macro Environment</h1>
        <p className="text-gray-400">Macroeconomic data is unavailable for this analysis.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-gold">Macro Environment</h1>
        <p className="mt-1 text-sm text-gray-400">Live indicators from FRED (Federal Reserve Economic Data)</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard label="Fed Funds Rate" value={indicators.fed_rate} />
        <MetricCard label="10-Year Treasury" value={indicators["10y_treasury"]} />
        <MetricCard label="CPI Inflation" value={indicators.cpi_inflation} />
        <MetricCard label="Unemployment" value={indicators.unemployment_rate} />
        <MetricCard label="VIX Index" value={indicators.vix_index} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {ANALYSIS_LABELS.map(([key, label]) =>
          analysis[key] ? (
            <div key={key} className="rounded-xl border border-navy-600 bg-navy-700 p-5">
              <div className="text-xs font-semibold uppercase tracking-widest text-gold">{label}</div>
              <p className="mt-2 text-sm leading-relaxed text-gray-300">{analysis[key]}</p>
            </div>
          ) : null
        )}
      </div>

      {analysis.summary && (
        <div className="rounded-xl border border-gold/40 bg-gold/5 p-5">
          <div className="text-xs font-semibold uppercase tracking-widest text-gold">
            Overall Macro Summary
          </div>
          <p className="mt-2 text-sm leading-relaxed text-gray-200">{analysis.summary}</p>
        </div>
      )}
    </div>
  );
}
