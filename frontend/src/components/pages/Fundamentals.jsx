import { Info, ExternalLink } from "lucide-react";
import MetricCard from "../MetricCard.jsx";
import { parseNumeric, formatLargeNumber, marginBasisNote, roeBasisNote } from "../../utils/format.js";

function SectionGrid({ title, items }) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-gray-400">{title}</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map(([label, value, sub]) => (
          <MetricCard key={label} label={label} value={value} decimals={2} sub={sub} />
        ))}
      </div>
    </div>
  );
}

export default function Fundamentals({ data }) {
  const f = data.fundamentals_data?.fundamentals ?? {};
  const financing = data.financing_data ?? {};
  const dilution = financing.dilution ?? {};
  const runway = financing.cash_runway ?? {};
  const filings = financing.financing_filings ?? [];

  // Foreign private issuers (e.g. ADRs) report financials in a home
  // currency while trading in USD - fx_conversion tells us whether
  // revenue/net_income/total_assets/etc. below have already been
  // converted to USD (the normal case) or, on the rare occasion no FX
  // rate was available, are still in that home currency and must not be
  // shown with a "$" prefix that would misstate them by the FX rate.
  const fx = f.fx_conversion ?? { applied: false, native_currency: null };
  const isUnconvertedForeignCurrency = !fx.applied && fx.native_currency && fx.native_currency !== "USD";
  const currencyPrefix = isUnconvertedForeignCurrency ? `${fx.native_currency} ` : "$";

  const large = (v) => {
    const n = parseNumeric(v);
    return n !== null ? formatLargeNumber(n, currencyPrefix) : (v ?? "N/A");
  };

  const formatPeriodDate = (iso) => {
    if (!iso) return null;
    // Build the Date from local y/m/d components (not `new Date(iso)`, which
    // parses a bare "YYYY-MM-DD" as UTC midnight and can render a day early
    // in timezones behind UTC).
    const [year, month, day] = iso.split("-").map(Number);
    if (!year || !month || !day) return null;
    const d = new Date(year, month - 1, day);
    return Number.isNaN(d.getTime())
      ? null
      : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  };
  const financialsPeriod = formatPeriodDate(f.financials_period_end);
  const balanceSheetPeriod = formatPeriodDate(f.balance_sheet_period_end);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-gold">Financial Fundamentals</h1>
        {(financialsPeriod || balanceSheetPeriod) && (
          <p className="mt-1 text-xs text-gray-500">
            {financialsPeriod && <>Income statement: TTM ending {financialsPeriod}</>}
            {financialsPeriod && balanceSheetPeriod && " · "}
            {balanceSheetPeriod && <>Balance sheet: as of {balanceSheetPeriod}</>}
          </p>
        )}
        {fx.applied && (
          <p className="mt-1 text-xs text-gray-500">
            Converted from {fx.from_currency} to {fx.to_currency} at {fx.rate.toFixed(6)} (rate as of {formatPeriodDate(fx.rate_as_of) ?? fx.rate_as_of})
          </p>
        )}
        {isUnconvertedForeignCurrency && (
          <p className="mt-1 text-xs text-danger">
            Figures below are in {fx.native_currency} - no USD conversion rate was available
          </p>
        )}
      </div>

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
          ["Gross Margin", f.gross_margin, marginBasisNote(f.gross_margin, f.gross_margin_basis)],
          ["Operating Margin", f.operating_margin, marginBasisNote(f.operating_margin, f.operating_margin_basis)],
          ["Profit Margin", f.profit_margin],
          ["ROE", f.roe, roeBasisNote(f.equity_average_basis)],
        ]}
      />

      <SectionGrid
        title="Valuation"
        items={[
          ["EPS", f.eps],
          ["P/E Ratio", f.pe_ratio],
          [
            "P/B Ratio",
            f.pb_ratio,
            f.pb_ratio_basis === "info_fallback_unverified" ? "Unverified - no FX rate available" : null,
          ],
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
            ratios and gross margin are not meaningful metrics for banks and insurers (no
            current/non-current balance-sheet split, no cost-of-goods line) and are shown as N/A,
            and operating/free cash flow is dominated by lending and reserve flows — routinely
            large and negative, and not a cash-burn signal. The cash-runway risk flag is suppressed
            here for that reason, refined only by whether total assets are growing (funding growth)
            or shrinking (possible stress) year-over-year — a coarse proxy that reads asset
            direction, not deposit-level detail. Leverage is formally assessed via regulatory
            capital (e.g., Tier 1 ratio); D/E here is total debt ÷ stockholders&apos; equity.
          </p>
        </div>
      )}

      {f.is_reit && (
        <div className="flex gap-3 rounded-xl border border-sky-400/40 bg-sky-400/5 p-4 text-sm text-gray-300">
          <Info size={18} className="mt-0.5 shrink-0 text-sky-400" />
          <p>
            <strong className="text-white">REIT note:</strong> a REIT&apos;s GAAP net income (and
            therefore its P/E and profit margin) is structurally depressed by large non-cash
            real-estate depreciation. REITs are valued on FFO/AFFO (funds from operations), which
            this pipeline does not compute — so the GAAP-based P/E shown here reads far more
            expensive than the metric the sector actually trades on. Treat the P/E and margin
            figures with that caveat.
          </p>
        </div>
      )}

      {financing.success && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
            Financing &amp; Dilution Risk
          </h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="bg-navy-700 border border-navy-600 rounded-xl px-5 py-4">
              <div
                className={`flex items-center gap-1.5 text-2xl font-bold ${
                  { Low: "text-success", Medium: "text-gold", High: "text-danger" }[
                    financing.overhang_level
                  ] ?? "text-gray-400"
                }`}
              >
                <span>
                  {{ Low: "🟢", Medium: "🟡", High: "🔴" }[financing.overhang_level] ?? "⚪"}
                </span>
                <span>{financing.overhang_level ?? "Unknown"}</span>
              </div>
              <div className="mt-1.5 text-[11px] font-medium uppercase tracking-widest text-gray-400">
                Overhang Level
              </div>
            </div>

            <MetricCard
              label="Shares Out (YoY)"
              value={dilution.available && dilution.yoy_change_pct != null ? dilution.yoy_change_pct : "N/A"}
              decimals={1}
              suffix="%"
            />

            <MetricCard
              label="Cash Runway"
              value={
                runway.available
                  ? runway.cash_flow_positive
                    ? "CF Positive"
                    : runway.sector_exempt
                      ? "n/m"
                      : runway.runway_months != null
                        ? `~${Math.round(runway.runway_months)} mo`
                        : "N/A"
                  : "N/A"
              }
              sub={
                runway.available && !runway.cash_flow_positive && runway.sector_exempt
                  ? "Not a burn-rate metric for this sector"
                  : null
              }
            />
          </div>

          {financing.summary && (
            <div
              className={`whitespace-pre-wrap rounded-xl border-l-4 p-5 text-sm leading-relaxed text-gray-200 ${
                financing.overhang_level === "High"
                  ? "border-l-danger bg-danger/5"
                  : financing.overhang_level === "Medium"
                    ? "border-l-gold bg-gold/5"
                    : "border-l-success bg-success/5"
              }`}
            >
              {financing.summary}
            </div>
          )}

          {filings.length > 0 ? (
            <div className="space-y-3">
              {filings.map((f, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-navy-600 border-l-4 border-l-gold bg-navy-700 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-semibold text-white">{f.form}</div>
                      <div className="mt-1 text-xs text-gray-400">
                        {f.filing_date} · {f.reason}
                      </div>
                    </div>
                    {f.url && (
                      <a
                        href={f.url}
                        target="_blank"
                        rel="noreferrer"
                        className="shrink-0 text-gold transition hover:text-gold-light"
                      >
                        <ExternalLink size={16} />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              No financing-related SEC filings detected in the past ~18 months.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
