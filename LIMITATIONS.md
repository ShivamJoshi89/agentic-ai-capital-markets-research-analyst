# Known Limitations

This document states, plainly, what this tool does **not** reliably do, so you
can judge whether to trust its output for a specific company. It is written for
someone deciding whether to rely on a given analysis — not for the engineering
team. Read it before using a memo or metric to inform a real decision.

_Last updated: 2026-08-11._

---

## 1. Cash-runway analysis cannot warn of a fast bank/financial failure

The financing-risk layer estimates cash runway from operating cash flow and
suppresses that estimate for banks, insurers, and REITs (whose negative
operating cash flow is structural, not a burn signal). For those sectors it
instead looks at whether **total assets are growing or shrinking** year-over-year
and raises a "Balance Sheet Contraction" flag only when they shrink.

**This is a lagging, quarterly-cadence signal, not an early-warning system.** A
deposit-run-style failure happens in days; the balance-sheet data this tool sees
updates once a quarter and is filed weeks after quarter-end. SVB's balance sheet
was still *growing* the quarter before it collapsed. The contraction flag can
confirm a slow, multi-quarter decline; it **cannot** anticipate a sudden
liquidity collapse. Do not treat the absence of a financing flag on a bank as
evidence of liquidity safety.

## 2. Single data vendor (yfinance), with no independent cross-check on the numbers

Almost every figure — prices, financial-statement line items, and precomputed
ratios — comes from **yfinance (Yahoo Finance) alone.** Correctness is bounded by
Yahoo's own data quality, and this audit found concrete cases where it was wrong
or internally inconsistent, not merely differently based:

- **Toyota's P/B**: Yahoo's own precomputed `priceToBook` was simply wrong (implied
  a per-share book value inconsistent with Toyota's filed equity and share count).
- **Profit margin — found and fixed (2026-08-11).** The 100-ticker sweep found
  Yahoo's precomputed `profitMargins` wrong for 6 tickers (reported 0% while the
  real margin was non-zero — e.g. a Korean tech ADR at a real ~13.5% — or the
  wrong sign — Sony reported −1.7% vs a real +8.8%). **`profit_margin` is now
  computed locally** as net income to common ÷ revenue, from this pipeline's own
  already-verified inputs, and no longer read from `profitMargins` at all.
- **Gross margin & operating margin — found and fixed (2026-08-11).** An earlier
  pass had left these as Yahoo passthrough on the belief that a Moderna
  discrepancy (Yahoo −66% gross vs a local +23%) was a definitional write-down
  difference. Corroborating against **Moderna's actual SEC XBRL filings** disproved
  that: the filed quarterly cost-of-revenue matches yfinance's own income-statement
  line items exactly, the filed TTM gross profit is **+$503M on $2.21B revenue
  (+22.8%)**, and Yahoo's −66% (which would imply a $3.67B cost of revenue vs the
  filed $1.71B) is simply wrong — as is its −558% operating margin, which implies a
  $12.3B operating loss vs the filed $3.32B. Domino's showed the same shape
  (SEC ≈ 40% gross vs Yahoo's 28.7%). **`gross_margin` and `operating_margin` are
  now computed locally** as a trailing-twelve-month ratio from the income
  statement's own Gross Profit / Operating Income over Total Revenue. This matched
  the filings for Moderna and left normal companies unchanged (Yahoo already agreed
  there within ~1pp). It **falls back** to Yahoo's precomputed value only when the
  statement can't support a recompute — fewer than four quarters (thin OTC
  micro-caps) or an impossible result (a reported "Gross Profit" exceeding revenue)
  — so for those specific cases the displayed value can still inherit a Yahoo error;
  a `gross_margin_basis` / `operating_margin_basis` field records which case
  applies. (Gross margin is separately shown as N/A for all financial-sector
  companies, per an earlier round.)

The only independent cross-check in the system is on **financing-event
classification** (SEC EDGAR is used to confirm splits and to classify
registration/prospectus filings). The **underlying financial numbers themselves
are not cross-checked against SEC XBRL or any second vendor.** Treat a single
surprising figure as possibly a data error, and verify against the company's
filings before relying on it.

## 3. Currency conversion covers a finite currency list

Foreign issuers (ADRs) report financial statements in a home currency while
trading in USD. The tool converts those statements to USD using FRED FX rates,
but **only for a fixed set of currencies**: USD, EUR, GBP, JPY, CHF, CAD, DKK,
plus (added 2026-08) INR, BRL, KRW, TWD, HKD, MXN, CNY, SGD, SEK, NOK, AUD.

For an issuer reporting in a currency **not** on that list (e.g. TRY, ZAR, IDR,
PLN, THB), the statement figures are **left in the native currency**. The tool
labels this correctly — the UI shows the native-currency code instead of a `$`
and the LLM memo is told the figures are unconverted — so it will not silently
present, say, rupiah as dollars. But the aggregate dollar figures (revenue,
assets, equity, debt) for such an issuer are **not comparable** to a USD peer's,
and per-share/ratio metrics that mix the USD-quoted price with native-currency
book value may be unreliable. Check the currency label before comparing a foreign
issuer's absolute figures to anything.

## 4. Non-operating securities produce mostly-empty, not rejected, output

The tool does not distinguish operating companies from **ETFs, warrants,
preferred shares, units, and closed-end funds.** Handed one of those tickers, it
returns a structurally valid but mostly-N/A fundamentals page rather than saying
"this isn't an operating company." It does not crash or invent data, but the
output is not meaningful for these security types. Confirm the ticker is a common
share of an operating company before reading its fundamentals.

## 5. Extreme-but-real micro-cap figures are passed through unfiltered

For companies with near-zero revenue (a pre-revenue or shell-like micro-cap), a
legitimately extreme ratio — an operating margin of several thousand percent, a
profit margin of tens of thousands of percent from a one-time gain — is displayed
as-is. These are faithful to the source (e.g. a company with $21 of revenue and a
$78K loss genuinely has a −373,000% margin) but are not useful as valuation
signals. Ratios on companies with negligible revenue should be ignored, not
interpreted.

## 6. Which tickers have actually been validated, and how

"Validated" here has a precise, checkable meaning — it does **not** mean
"everything works for every ticker."

- **Curated deep-dive set (11):** AAPL, JPM, MSFT, NVDA, O, PGR, DPZ, MRNA, TM,
  SONY, NVO — repeatedly checked in detail across successive audit rounds for
  ratio sourcing, ROE/ROA basis, currency conversion, negative-equity handling,
  split detection, and sector gating.
- **Random validation sweep (100), 2026-08-11:** drawn with a fixed, disclosed
  seed (`20260811`) from a broad universe — the SEC `company_tickers.json` filer
  list (10,398 names: every cap tier, financials, REITs, SEC-filing ADRs; 82
  drawn) plus a 35-name major-ADR basket for foreign coverage (18 drawn). The
  full 100-ticker list and seed are recorded with the audit. Every ticker was run
  through fundamentals, ratios, sector gates, currency handling, market-data
  returns, cash-runway framing, and the LLM-context number formatting.
  - **Result: 0 crashes / unhandled exceptions across all 100** (including
    warrants, preferred, ETFs, and thin OTC names, which were handled gracefully).
  - Every audit-established invariant held: sector gates, currency labeling, LLM
    number formatting, cash-runway framing, and market-data/YTD basis were correct
    on all 100.
  - The 39 "flagged" tickers all root-caused to the limitations documented above,
    **not to new pipeline bugs.** Two of those patterns have since been fixed
    outright rather than merely documented: unconverted ADR currencies (FX map
    expanded, §3) and Yahoo's wrong precomputed `profitMargins` (now computed
    locally, §2). The rest are data-availability for non-operating securities and
    extreme-but-real micro-cap figures.

  _Sampling caveat:_ the intended S&P 500 / Russell 2000 constituent lists were
  not fetchable (Wikipedia blocked automated access), so the SEC filer universe
  stood in for the US-cap-tier strata. It contains all of those names but is
  weighted toward small/micro-caps, which is if anything a stricter bug-finding
  sample.

Anything outside these sets is **unvalidated**. A ticker not listed above has
not been specifically checked.

## 7. LLM model, and why

Research memos are generated by **OpenAI `gpt-5.4-mini`** (upgraded from the
previous `gpt-3.5-turbo` baseline on 2026-08-11).

The choice was made on evidence, not defaults. On an 8-ticker faithfulness
comparison (AAPL, JPM, O, PGR, MRNA, DPZ, TM, NVO) against the exact structured
input each memo was given:

- **Faithfulness:** `gpt-5.4-mini` reproduced the input revenue magnitude in
  **8/8** memos vs **4/8** for `gpt-3.5-turbo`; it correctly narrated N/A ratios
  ("ROE is not meaningful with negative equity", "price-to-book is not meaningful
  given negative equity") rather than inventing figures, where `gpt-3.5-turbo`
  produced unsupported claims (e.g. "consistent revenue growth" with no growth
  data) and referenced a debt-to-equity ratio that was actually N/A.
- **Quality:** materially more detailed, better-hedged, more sector-aware prose.
- **Cost:** ~**$0.006** per memo at standard rates vs ~$0.002 for
  `gpt-3.5-turbo`. (The Batch API's ~50%-off rate does *not* apply: the public
  `/api/analyze` endpoint is synchronous and a user waits on it, so it's
  real-time, billed at the standard rate.) The ~3× multiple is a few tenths of
  a cent per memo — immaterial for this tool — so the more faithful model was
  chosen.
- **Latency:** ~20–25s per memo vs ~5–8s for the old model. Acceptable for a
  one-memo-per-analysis workflow, but noticeably slower.

_The memo remains an LLM narrative built from the structured data. It can still
phrase things imperfectly; the structured metrics and their caveats are the
authoritative part. A caveat block is now injected into the model's context for
REITs (GAAP P/E is depreciation-inflated; FFO/AFFO is the real metric), banks/
insurers, and negative-equity companies, because both models otherwise re-derived
the exact framing the risk layer suppresses._

## 8. General scope

This tool is a research aid, not investment advice or a substitute for reading
primary filings. It has no view of intraday data, no forward estimates or
consensus, no FFO/AFFO or other sector-specific valuation metrics beyond the
standard GAAP set, and no guarantee of freshness between quarterly filing cycles.
