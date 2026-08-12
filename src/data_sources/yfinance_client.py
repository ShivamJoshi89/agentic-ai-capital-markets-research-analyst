"""
yfinance client for fetching stock market data
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
import pandas as pd

from data_sources.fred_client import FREDClient

logger = logging.getLogger(__name__)


class YFinanceClient:
    """
    Client for fetching stock data from yfinance.
    """

    # Rate-limit resilience: Yahoo throttles bursts of requests, and yfinance
    # raises YFRateLimitError for them. A throttled call is retried with
    # exponential backoff up to this cap; once exhausted the error is
    # surfaced (raised) rather than swallowed to None, so a caller can't
    # mistake throttling for "this company has no data".
    RATE_LIMIT_MAX_RETRIES = 3
    RATE_LIMIT_BASE_DELAY_SEC = 1.0

    def __init__(self):
        """Initialize YFinance client"""
        self.name = "YFinance Client"
        self.fred_client = FREDClient()
        logger.info(f"{self.name} initialized")

    @classmethod
    def _fetch_with_retry(cls, fn, what: str):
        """Call `fn()`, retrying only on yfinance rate-limit errors with
        exponential backoff (1s, 2s, 4s, ...). After RATE_LIMIT_MAX_RETRIES
        exhausted attempts, re-raises YFRateLimitError so the caller surfaces
        an explicit rate-limit failure instead of a silent bad/empty result.
        Any non-rate-limit exception propagates immediately (not retried)."""
        delay = cls.RATE_LIMIT_BASE_DELAY_SEC
        for attempt in range(1, cls.RATE_LIMIT_MAX_RETRIES + 1):
            try:
                return fn()
            except YFRateLimitError:
                if attempt >= cls.RATE_LIMIT_MAX_RETRIES:
                    logger.error(f"{what}: yfinance rate limit persisted after {attempt} attempts")
                    raise
                logger.warning(
                    f"{what}: rate-limited (attempt {attempt}/{cls.RATE_LIMIT_MAX_RETRIES}), "
                    f"backing off {delay:.1f}s"
                )
                time.sleep(delay)
                delay *= 2
    
    def get_stock_data(self, ticker: str, period: str = "1y") -> Optional[Dict[str, Any]]:
        """
        Fetch historical stock data.
        
        Args:
            ticker: Stock ticker symbol
            period: Time period ('1y', '5y', etc.)
        
        Returns:
            Dictionary with stock data or None if error
        """
        try:
            logger.info(f"Fetching stock data for {ticker} ({period})")

            # Create ticker object
            stock = yf.Ticker(ticker)

            # Fetch historical data (retried on rate-limit, see _fetch_with_retry)
            history = self._fetch_with_retry(
                lambda: stock.history(period=period), f"{ticker} history")

            if history.empty:
                logger.warning(f"No data found for {ticker}")
                return None

            return {
                "ticker": ticker,
                "history": history,
                "period": period,
                "success": True
            }

        except YFRateLimitError:
            # Surface throttling as a clear failure rather than swallowing it to
            # None (which the caller would read as "no such data").
            logger.error(f"Rate limited fetching stock data for {ticker}")
            raise
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
            return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch company information.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with company info or None if error
        """
        try:
            logger.info(f"Fetching company info for {ticker}")

            stock = yf.Ticker(ticker)
            info = self._fetch_with_retry(lambda: stock.info, f"{ticker} info")

            if not info:
                logger.warning(f"No info found for {ticker}")
                return None
            
            # Extract key information
            company_data = {
                "ticker": ticker,
                "company_name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", None),
                "employees": info.get("fullTimeEmployees", None),
                "website": info.get("website", ""),
                "country": info.get("country", ""),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "business_summary": info.get("longBusinessSummary", ""),
                "current_price": info.get("currentPrice", None),
                "previous_close": info.get("previousClose", None),
                "open_price": info.get("open", None),
                "day_high": info.get("dayHigh", None),
                "day_low": info.get("dayLow", None),
                "52_week_high": info.get("fiftyTwoWeekHigh", None),
                "52_week_low": info.get("fiftyTwoWeekLow", None),
                "success": True
            }
            
            return company_data

        except YFRateLimitError:
            logger.error(f"Rate limited fetching company info for {ticker}")
            raise
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {str(e)}")
            return None
    
    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch company fundamentals.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with financial data or None if error
        """
        try:
            logger.info(f"Fetching fundamentals for {ticker}")

            stock = yf.Ticker(ticker)
            info = self._fetch_with_retry(lambda: stock.info, f"{ticker} info")

            if not info:
                logger.warning(f"No fundamentals found for {ticker}")
                return None

            # The info dict lacks several fields (all balance-sheet totals, and
            # for banks also leverage/liquidity ratios) - fall back to the
            # financial statement DataFrames for those. Quarterly statements
            # are tried before annual ones: yfinance's annual balance_sheet/
            # cashflow only refresh once a fiscal year, so they can lag the
            # TTM income-statement figures in `info` (as of mostRecentQuarter)
            # by up to several quarters, while quarterly_* is refreshed each
            # quarter and stays much closer to that same cutoff.
            quarterly_balance_sheet = self._safe_statement(stock, "quarterly_balance_sheet")
            balance_sheet = self._safe_statement(stock, "balance_sheet")
            quarterly_cashflow = self._safe_statement(stock, "quarterly_cashflow")
            cashflow = self._safe_statement(stock, "cashflow")
            quarterly_income_stmt = self._safe_statement(stock, "quarterly_income_stmt")

            total_assets = info.get("totalAssets") or self._latest_row(
                quarterly_balance_sheet, ["Total Assets"]) or self._latest_row(
                balance_sheet, ["Total Assets"])
            total_liabilities = info.get("totalLiabilities") or self._latest_row(
                quarterly_balance_sheet, ["Total Liabilities Net Minority Interest", "Total Liab"]) or self._latest_row(
                balance_sheet, ["Total Liabilities Net Minority Interest", "Total Liab"])
            total_equity = info.get("totalEquity") or self._latest_row(
                quarterly_balance_sheet, ["Stockholders Equity", "Common Stock Equity",
                                "Total Equity Gross Minority Interest"]) or self._latest_row(
                balance_sheet, ["Stockholders Equity", "Common Stock Equity",
                                "Total Equity Gross Minority Interest"])
            total_debt = info.get("totalDebt") or self._latest_row(
                quarterly_balance_sheet, ["Total Debt"]) or self._latest_row(
                balance_sheet, ["Total Debt"])

            # Cash flow fields are trailing-twelve-month in `info`, not a
            # single period - so the fallback sums the latest 4 quarters
            # rather than reading one quarter's (or one stale fiscal year's)
            # value, to stay period-consistent with the TTM income figures.
            operating_cash_flow = info.get("operatingCashflow") or self._ttm_sum_row(
                quarterly_cashflow, ["Operating Cash Flow"]) or self._latest_row(
                cashflow, ["Operating Cash Flow"])
            free_cash_flow = info.get("freeCashflow") or self._ttm_sum_row(
                quarterly_cashflow, ["Free Cash Flow"]) or self._latest_row(
                cashflow, ["Free Cash Flow"])

            # net_income and total_equity/total_assets/total_debt above are
            # this codebase's own point-in-time figures (Round-1-fixed to
            # prefer the freshest quarterly statement). debt_to_equity/
            # pb_ratio are recomputed from those same point-in-time figures
            # (a balance-sheet snapshot ratio and a market-value-vs-book-
            # value-at-a-moment ratio both want the ending balance, not an
            # average) rather than taken from yfinance's own precomputed
            # `.info` fields.
            #
            # roe/roa are different: the standard convention for both is
            # net income over *average* equity/assets, not a point-in-time
            # ending balance - using the ending balance would be internally
            # consistent with this card but structurally offset from
            # Bloomberg, Yahoo, and most screeners. `.info`'s own
            # returnOnEquity/returnOnAssets do use an average basis, but
            # it's a black box we can't verify or reproduce (reverse-
            # engineering AAPL's implied equity base matched an average of
            # this-quarter and year-ago equity, not any two adjacent
            # quarters, and ROA's implied asset base didn't match any
            # average tried) - so rather than trust it or abandon
            # averaging entirely, roe/roa are computed against the average
            # of the two most recent quarters of our own already-fixed
            # total_equity/total_assets source. That's the standard
            # convention and reproducible from data already on this card,
            # at the cost of not bit-for-bit matching Yahoo's own number.
            net_income = info.get("netIncomeToCommon")
            market_cap = info.get("marketCap")
            revenue = info.get("totalRevenue")
            cash = info.get("totalCash")

            # ROE's denominator specifically needs equity attributable to
            # COMMON shareholders, to match net_income (netIncomeToCommon,
            # which already excludes preferred dividends) on the same
            # footing - "Stockholders Equity" and "Total Equity Gross
            # Minority Interest" both still include preferred stock (and
            # the latter also minority interest), which doesn't belong in
            # a ratio paired with income to common alone. Confirmed live:
            # JPM carries $21B of preferred stock inside Stockholders
            # Equity, absent from Common Stock Equity. This is a distinct
            # basis from the point-in-time `total_equity` above (which
            # correctly stays "Stockholders Equity"-preferring, since the
            # Balance Sheet card's "Total Equity" is meant to be the whole
            # equity base, not just the common-shareholder slice) - only
            # ROE's average uses "Common Stock Equity" first.
            average_equity, equity_average_basis, equity_average_row = self._average_of_latest_two_periods(
                quarterly_balance_sheet, balance_sheet,
                ["Common Stock Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"],
                fallback_value=total_equity,
            )
            average_assets, assets_average_basis, _assets_average_row = self._average_of_latest_two_periods(
                quarterly_balance_sheet, balance_sheet, ["Total Assets"],
                fallback_value=total_assets,
            )

            # Year-over-year total-assets trend (currency-invariant percent
            # change). Consumed by the financing-risk layer to distinguish a
            # balance-sheet-driven company funding GROWTH (rising assets +
            # negative operating cash flow - benign) from one CONTRACTING
            # (falling assets + negative operating cash flow - potential
            # stress), which the runway/sector logic would otherwise treat
            # identically. None when no genuine year-ago period is available.
            total_assets_yoy_change_pct = self._yoy_change_pct(
                quarterly_balance_sheet, balance_sheet, ["Total Assets"]
            )

            # Foreign private issuers (e.g. ADRs) report financial
            # statements in their home currency while trading - and
            # therefore market_cap/price - in USD. Every figure sourced
            # from the statements above (revenue, net_income, total_assets,
            # total_liabilities, total_equity, total_debt, cash, operating/
            # free cash flow, and the ROE/ROA averages) is still in that
            # home currency at this point - convert them all to USD using
            # one shared, dated FX rate so nothing downstream (this card,
            # the LLM memo, peer comps) silently mixes currencies or gets
            # rendered with a "$" it doesn't have.
            financial_currency = info.get("financialCurrency")
            quote_currency = info.get("currency")
            fx_mismatch = bool(
                financial_currency and quote_currency and financial_currency != quote_currency
            )
            fx_conversion = {"applied": False, "native_currency": financial_currency}

            if fx_mismatch:
                fx_info = self.fred_client.get_fx_rate_to_usd(financial_currency)
                if fx_info is not None:
                    rate = fx_info["rate"]

                    def _to_usd(value):
                        return value * rate if value is not None else None

                    revenue = _to_usd(revenue)
                    net_income = _to_usd(net_income)
                    total_assets = _to_usd(total_assets)
                    total_liabilities = _to_usd(total_liabilities)
                    total_equity = _to_usd(total_equity)
                    total_debt = _to_usd(total_debt)
                    cash = _to_usd(cash)
                    operating_cash_flow = _to_usd(operating_cash_flow)
                    free_cash_flow = _to_usd(free_cash_flow)
                    average_equity = _to_usd(average_equity)
                    average_assets = _to_usd(average_assets)

                    fx_conversion = {
                        "applied": True,
                        "from_currency": financial_currency,
                        "to_currency": quote_currency,
                        "rate": rate,
                        "rate_as_of": fx_info["as_of"],
                    }
                else:
                    logger.warning(
                        f"{ticker}: financials reported in {financial_currency} but no FX "
                        f"rate to {quote_currency} was available - dollar figures left in "
                        f"{financial_currency}, must not be displayed with a \"$\" prefix"
                    )

            # Now that a currency mismatch has been resolved (converted to
            # USD) wherever possible, equity_ratios only needs to know
            # about a *residual* mismatch - one FX couldn't fix - so it can
            # fall back to yfinance's own priceToBook rather than dividing
            # mismatched currencies directly. Once converted, total_equity
            # and market_cap are both in quote_currency, so no mismatch
            # remains and the direct computation is safe.
            residual_mismatch = fx_mismatch and not fx_conversion["applied"]

            equity_ratios = self._compute_equity_ratios(
                net_income=net_income,
                total_equity=total_equity,
                average_equity=average_equity,
                average_assets=average_assets,
                total_debt=total_debt,
                market_cap=market_cap,
                financial_currency=financial_currency if residual_mismatch else None,
                quote_currency=quote_currency if residual_mismatch else None,
                info_price_to_book=info.get("priceToBook"),
            )
            debt_to_equity = equity_ratios["debt_to_equity"]
            roa = equity_ratios["roa"]
            roe = equity_ratios["roe"]
            pb_ratio = equity_ratios["pb_ratio"]
            pb_ratio_basis = equity_ratios["pb_ratio_basis"]

            # Liquidity ratios from the current asset/liability split when the
            # info dict lacks them (banks report neither - stays None there).
            # Current assets/liabilities/inventory are pulled from the same
            # statement (quarterly, or annual only if quarterly lacks either
            # leg) so the ratio never mixes a quarterly numerator with an
            # annual denominator from a different period.
            current_ratio = info.get("currentRatio")
            quick_ratio = info.get("quickRatio")
            if current_ratio is None or quick_ratio is None:
                current_assets = self._latest_row(quarterly_balance_sheet, ["Current Assets"])
                current_liabilities = self._latest_row(quarterly_balance_sheet, ["Current Liabilities"])
                statement_for_ratios = quarterly_balance_sheet
                if not (current_assets and current_liabilities):
                    current_assets = self._latest_row(balance_sheet, ["Current Assets"])
                    current_liabilities = self._latest_row(balance_sheet, ["Current Liabilities"])
                    statement_for_ratios = balance_sheet
                if current_assets and current_liabilities:
                    if current_ratio is None:
                        current_ratio = round(current_assets / current_liabilities, 2)
                    if quick_ratio is None:
                        inventory = self._latest_row(statement_for_ratios, ["Inventory"]) or 0
                        quick_ratio = round((current_assets - inventory) / current_liabilities, 2)

            # Period disclosure: `mostRecentQuarter` is the cutoff Yahoo's own
            # TTM income-statement figures (revenue, net income, EPS, margins)
            # are aligned to. balance_sheet_period_end is the actual statement
            # column the point-in-time fields above were read from, so a caller
            # can surface it when it lags the income-statement cutoff instead
            # of silently presenting both as if they were the same date.
            financials_period_end = self._epoch_to_date(info.get("mostRecentQuarter"))
            balance_sheet_period_end = (
                self._statement_period_end(quarterly_balance_sheet)
                or self._statement_period_end(balance_sheet)
            )
            if financials_period_end and balance_sheet_period_end:
                gap_days = (
                    datetime.fromisoformat(financials_period_end)
                    - datetime.fromisoformat(balance_sheet_period_end)
                ).days
                if gap_days > 100:
                    logger.warning(
                        f"{ticker}: balance sheet data ({balance_sheet_period_end}) is "
                        f"~{gap_days} days behind the income-statement TTM cutoff "
                        f"({financials_period_end})"
                    )

            # profit/gross/operating margins are computed locally from the
            # income statement rather than trusting yfinance's precomputed
            # profitMargins/grossMargins/operatingMargins, which the 100-ticker
            # sweep - corroborated against SEC XBRL filings - found wrong:
            #  - profitMargins: 0.0 while real (KOKSF 13.5%, STRG/ATALF/PCT/
            #    SWISF) or the wrong sign (SONY -1.7% reported vs a real +8.8%).
            #  - grossMargins/operatingMargins: MRNA reported -66% gross /
            #    -558% operating, both impossible against its own filings - the
            #    filed TTM gross profit is +$503M on $2.21B revenue (+22.8%),
            #    with SEC-filed quarterly COGS matching yfinance's own line
            #    items exactly; DPZ likewise filed ~40% gross vs Yahoo's 28.7%.
            #
            # profit_margin uses net income to common / revenue (this
            # pipeline's own already-verified, FX-converted figures - the ROE
            # numerator and TTM revenue; the ratio is FX-invariant). gross_ and
            # operating_margin are TTM sums of the income statement's own Gross
            # Profit / Operating Income over Total Revenue (see _ttm_margin),
            # which matched the SEC filings exactly for MRNA and left the
            # curated normal-company set (AAPL/MSFT/TM/NVO...) unchanged (Yahoo
            # already matched a local recompute there within ~1pp). This is the
            # same recompute-from-verified-inputs pattern already used for
            # ROE/ROA - NOT a blanket distrust of yfinance: gross_/operating_
            # margin fall back to Yahoo's precomputed value whenever the income
            # statement can't support a reliable recompute (fewer than 4
            # quarters, e.g. thin OTC micro-caps like ATALF/KOKSF; or an
            # impossible result like STRG's "Gross Profit" exceeding revenue).
            profit_margin = (
                net_income / revenue if net_income is not None and revenue else None
            )
            gross_margin, gross_margin_basis = self._ttm_margin(
                quarterly_income_stmt, ["Gross Profit"], info.get("grossMargins"))
            operating_margin, operating_margin_basis = self._ttm_margin(
                quarterly_income_stmt, ["Operating Income", "Operating Income Loss"],
                info.get("operatingMargins"))

            fundamentals = {
                "ticker": ticker,
                "sector": info.get("sector", None),
                "revenue": revenue,
                "net_income": net_income,
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "total_debt": total_debt,
                "cash": cash,
                "free_cash_flow": free_cash_flow,
                "operating_cash_flow": operating_cash_flow,
                "gross_margin": gross_margin,
                "operating_margin": operating_margin,
                # "computed" (TTM from the income statement) or "info_fallback"
                # (Yahoo's precomputed value - the income statement couldn't
                # support a reliable local recompute for this filer).
                "gross_margin_basis": gross_margin_basis,
                "operating_margin_basis": operating_margin_basis,
                "profit_margin": profit_margin,
                "roe": roe,
                "roa": roa,
                # "year_ago_average" (the standard, intended basis),
                # "point_in_time_fallback" (no valid year-ago period - too
                # little history, or the gap check failed), or
                # "unavailable_fallback" (no equity/asset data at all).
                "equity_average_basis": equity_average_basis,
                "assets_average_basis": assets_average_basis,
                # YoY total-assets trend (percent), or None if unavailable -
                # used by the financing-risk layer to tell balance-sheet
                # growth from contraction (see _yoy_change_pct).
                "total_assets_yoy_change_pct": total_assets_yoy_change_pct,
                # Which underlying equity line ROE's average actually used
                # - "Common Stock Equity" (the intended basis, matching
                # net_income's to-common scope) or a fallback ("Stockholders
                # Equity"/"Total Equity Gross Minority Interest", both of
                # which still include preferred stock) when Common Stock
                # Equity wasn't reported for this filer.
                "equity_average_row": equity_average_row,
                "eps": info.get("trailingEps", None),
                "pe_ratio": info.get("trailingPE", None),
                "pb_ratio": pb_ratio,
                "pb_ratio_basis": pb_ratio_basis,
                "dividend_yield": info.get("dividendYield", None),
                "debt_to_equity": debt_to_equity,
                "current_ratio": current_ratio,
                "quick_ratio": quick_ratio,
                "financials_period_end": financials_period_end,
                "balance_sheet_period_end": balance_sheet_period_end,
                "fx_conversion": fx_conversion,
                "success": True
            }

            return fundamentals

        except YFRateLimitError:
            # Surface throttling clearly so the agent layer can report a
            # rate-limit failure, not a generic "no fundamentals".
            logger.error(f"Rate limited fetching fundamentals for {ticker}")
            raise
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
            return None

    @staticmethod
    def _compute_equity_ratios(
        net_income: Optional[float],
        total_equity: Optional[float],
        total_debt: Optional[float],
        market_cap: Optional[float],
        average_equity: Optional[float],
        average_assets: Optional[float],
        financial_currency: Optional[str] = None,
        quote_currency: Optional[str] = None,
        info_price_to_book: Optional[float] = None,
    ) -> Dict[str, Optional[float]]:
        """Derive debt_to_equity/roa/roe/pb_ratio from this codebase's own
        already-fixed figures, rather than mixing in yfinance's own
        precomputed (and differently-based) `.info` ratios.

        debt_to_equity and pb_ratio use `total_equity` - the point-in-time
        ending balance - since both are inherently snapshot ratios (a
        balance-sheet leverage ratio and a market-value-vs-book-value-at-a-
        moment ratio). roe and roa use `average_equity`/`average_assets`
        instead (conventionally the average of the two most recent
        periods) - the standard convention for both ratios, and callers
        are expected to always pass an explicit average (falling back to
        the point-in-time value themselves when fewer than two periods of
        history exist) rather than relying on an implicit default here.

        ROE and P/B are only computed when total_equity is strictly
        positive: dividing by a negative equity base produces a signed
        number that reads backwards (e.g. a profitable company with
        negative equity would get a *negative* "ROE"), so both are left
        None (rendered as N/A by the caller) rather than a misleading
        multiple. ROA has no such issue since assets are never negative.
        debt_to_equity is still computed (and may be negative) so the risk
        layer can detect the negative-equity condition itself; display-
        layer N/A-ing happens in fundamentals_agent.py.

        P/B specifically cannot always be recomputed from market_cap /
        total_equity: foreign private issuers (ADRs) report financial
        statements in their home currency (financial_currency) while
        trading - and therefore market_cap - in USD (quote_currency).
        Dividing one by the other when they differ silently produces an
        FX-scale-off ratio (confirmed live: Toyota's USD market_cap over
        untouched JPY total_equity understated P/B by ~1500x). The caller
        (get_fundamentals) converts total_equity to USD first whenever a
        real FX rate is available, so by the time `financial_currency`/
        `quote_currency` reach this function as *different* values, it
        specifically means conversion was attempted and failed (no FX
        rate available) - only then does P/B fall back to
        `info_price_to_book`. That fallback is NOT assumed correct either:
        it's labeled `pb_ratio_basis: "info_fallback_unverified"` rather
        than presented with the same confidence as a direct computation,
        because Yahoo's own priceToBook has independently been observed
        wrong for at least one real ADR (Toyota: Yahoo's priceToBook of
        ~15.6x implies a per-share book value wildly inconsistent with
        Toyota's real, filed total equity divided by its real share count
        - not just an FX issue, a basis Yahoo computes some other,
        unreliable way for this security type). debt_to_equity/roe/roa
        aren't affected by any of this - both operands in each come from
        the financial statements, so they're same-currency regardless of
        what market_cap is doing.
        """
        currency_mismatch = bool(
            financial_currency and quote_currency and financial_currency != quote_currency
        )

        debt_to_equity = (
            round(total_debt / total_equity * 100, 2)
            if total_debt is not None and total_equity else None
        )
        roa = (
            round(net_income / average_assets, 4)
            if net_income is not None and average_assets else None
        )
        # Guarded on total_equity (the actual current balance) for the
        # negative-equity determination, but divides by average_equity -
        # if averaging ever produced a non-positive base while the current
        # balance is positive (or vice versa), treat it as undefined too.
        roe = (
            round(net_income / average_equity, 4)
            if net_income is not None and total_equity and total_equity > 0
            and average_equity and average_equity > 0 else None
        )
        pb_ratio_basis = None
        if total_equity and total_equity > 0:
            if not currency_mismatch and market_cap is not None:
                pb_ratio = round(market_cap / total_equity, 2)
                pb_ratio_basis = "computed"
            elif info_price_to_book is not None:
                # market_cap missing, or a currency mismatch that FX
                # conversion couldn't resolve - fall back to yfinance's
                # own priceToBook, but mark it explicitly unverified
                # rather than presenting a guess with full confidence.
                pb_ratio = round(info_price_to_book, 2)
                pb_ratio_basis = "info_fallback_unverified"
            else:
                pb_ratio = None
        else:
            pb_ratio = None
        return {
            "debt_to_equity": debt_to_equity,
            "roa": roa,
            "roe": roe,
            "pb_ratio": pb_ratio,
            "pb_ratio_basis": pb_ratio_basis,
        }

    # A genuine year-ago pairing must fall in this window regardless of
    # which index position produced it - guards against non-calendar-
    # quarterly reporting, stub periods (e.g. around an M&A or fiscal-year
    # change), or any other irregular cadence where "4 columns back" isn't
    # actually ~12 months back for a particular filer.
    MIN_YEAR_AGO_GAP_DAYS = 300
    MAX_YEAR_AGO_GAP_DAYS = 430

    @classmethod
    def _average_of_latest_two_periods(
        cls, quarterly_statement, annual_statement, row_names, fallback_value: Optional[float]
    ) -> Tuple[Optional[float], str, Optional[str]]:
        """Average of the current period and the period ~12 months prior,
        for the standard average-equity/average-assets basis of ROE/ROA -
        the same trailing-twelve-month window the net income numerator was
        earned over. This is deliberately NOT "the latest two" periods:
        averaging two adjacent quarters (~3 months apart) barely moves the
        ratio and misses most of a year's equity change, understating the
        real point-in-time-vs-average gap by roughly an order of magnitude
        (confirmed live: AAPL's genuine year-ago pairing shifted ROE by
        ~28.8pp, matching Yahoo's own returnOnEquity almost exactly, versus
        under 1pp from an adjacent-quarter average - the two are not
        interchangeable).

        Quarterly columns are ~3 months apart, so the year-ago period is
        4 columns back; annual columns are already a year apart, so it's
        1 column back there. The actual date gap is checked (not assumed
        from column position alone) against MIN/MAX_YEAR_AGO_GAP_DAYS -
        verified live at 365 days for AAPL/JPM/MSFT/TM/SONY/NVO's quarterly
        series, but a filer with an irregular or non-calendar-quarterly
        cadence could have a 4-columns-back period that isn't really a
        year prior, which would silently reintroduce this same class of
        bug through a different door.

        Falls back to the single latest period (not an average) whenever
        a genuine year-ago period isn't available - too few periods (e.g.
        a recent IPO) or the gap check fails - since averaging two periods
        that aren't ~12 months apart would reintroduce the bug this fixes
        either way. Returns `fallback_value` (the already-resolved point-
        in-time figure) if neither statement has any data for these row
        names at all.

        `row_names` is priority-ordered - the first name present in a
        statement wins, so callers control which underlying concept is
        preferred (e.g. "Common Stock Equity" before "Stockholders Equity"
        when the two diverge due to preferred stock - see ROE's caller).

        Returns (value, temporal_basis, matched_row_name). temporal_basis
        is one of "year_ago_average", "point_in_time_fallback", or
        "unavailable_fallback" (no statement had any of row_names at all,
        in which case matched_row_name is None).
        """
        for statement, periods_apart in ((quarterly_statement, 4), (annual_statement, 1)):
            if statement is None:
                continue
            for name in row_names:
                if name not in statement.index:
                    continue
                series = statement.loc[name].dropna()
                if len(series) > periods_apart:
                    gap_days = abs((series.index[0] - series.index[periods_apart]).days)
                    if cls.MIN_YEAR_AGO_GAP_DAYS <= gap_days <= cls.MAX_YEAR_AGO_GAP_DAYS:
                        return float((series.iloc[0] + series.iloc[periods_apart]) / 2), "year_ago_average", name
                if len(series) >= 1:
                    return float(series.iloc[0]), "point_in_time_fallback", name
        return fallback_value, "unavailable_fallback", None

    @classmethod
    def _yoy_change_pct(cls, quarterly_statement, annual_statement, row_names) -> Optional[float]:
        """Percent change of a statement row between the current period and
        the period ~12 months prior, using the same year-ago pairing and gap
        tolerance as _average_of_latest_two_periods. Returns None when a
        genuine year-ago period isn't available (too little history, or the
        gap check fails) - callers must treat None as "trend unknown", never
        as zero/flat.

        Currency-invariant: both endpoints come from the same raw statement in
        one native currency, so the percent change is unaffected by any FX
        conversion applied downstream - which is why it's computed here from
        the untouched statements rather than from the converted figures. Used
        to tell balance-sheet GROWTH (rising assets) from CONTRACTION (falling
        assets), e.g. to distinguish a bank funding loan growth from one
        shrinking under deposit stress - both of which produce negative
        operating cash flow but mean opposite things."""
        for statement, periods_apart in ((quarterly_statement, 4), (annual_statement, 1)):
            if statement is None:
                continue
            for name in row_names:
                if name not in statement.index:
                    continue
                series = statement.loc[name].dropna()
                if len(series) > periods_apart:
                    gap_days = abs((series.index[0] - series.index[periods_apart]).days)
                    if cls.MIN_YEAR_AGO_GAP_DAYS <= gap_days <= cls.MAX_YEAR_AGO_GAP_DAYS:
                        now = float(series.iloc[0])
                        prior = float(series.iloc[periods_apart])
                        if prior:
                            return (now - prior) / prior * 100
        return None

    @staticmethod
    def _safe_statement(stock, attribute: str):
        """Fetch a financial statement DataFrame, returning None on any failure"""
        try:
            statement = getattr(stock, attribute)
            if statement is None or statement.empty:
                return None
            return statement
        except Exception as e:
            logger.warning(f"Could not fetch {attribute}: {str(e)}")
            return None

    @staticmethod
    def _latest_row(statement, row_names) -> Optional[float]:
        """Most recent non-null value for the first matching row name.
        Statement columns are ordered most-recent first."""
        if statement is None:
            return None
        for name in row_names:
            if name in statement.index:
                series = statement.loc[name].dropna()
                if not series.empty:
                    return float(series.iloc[0])
        return None

    @staticmethod
    def _ttm_sum_row(statement, row_names, quarters: int = 4) -> Optional[float]:
        """Sum of the most recent `quarters` non-null quarterly values for the
        first matching row name - a trailing-twelve-month approximation for
        flow items (cash flow) that `.info` doesn't report directly. Returns
        None rather than a partial-period sum if fewer than `quarters` of
        data are available."""
        if statement is None:
            return None
        for name in row_names:
            if name in statement.index:
                series = statement.loc[name].dropna()
                if len(series) >= quarters:
                    return float(series.iloc[:quarters].sum())
        return None

    @classmethod
    def _ttm_margin(cls, quarterly_income_stmt, numerator_rows,
                    info_fallback: Optional[float]) -> Tuple[Optional[float], str]:
        """TTM margin computed from the income statement's own line items -
        sum(numerator, 4 quarters) / sum(Total Revenue, 4 quarters) - rather
        than trusting yfinance's precomputed grossMargins/operatingMargins,
        which the 100-ticker sweep (corroborated against SEC XBRL) found wrong
        for real tickers (MRNA: -66% reported gross vs a filed +22.8%). The
        numerator and Total Revenue come from the same statement and the same
        four quarters, so the ratio is self-consistent, and both operands are
        in one native currency so it's FX-invariant.

        Falls back to `info_fallback` (Yahoo's precomputed value) - returning
        basis "info_fallback" - whenever the statement can't support a
        reliable recompute: no statement, fewer than 4 quarters of either row
        (thin OTC micro-caps like ATALF/KOKSF), non-positive revenue, or an
        impossible result where the numerator exceeds revenue (margin > 100%,
        e.g. a filer whose reported "Gross Profit" is larger than its
        revenue). Returns (value, basis) with basis "computed" or
        "info_fallback"."""
        revenue = cls._ttm_sum_row(quarterly_income_stmt, ["Total Revenue", "Operating Revenue"])
        numerator = cls._ttm_sum_row(quarterly_income_stmt, numerator_rows)
        if revenue and revenue > 0 and numerator is not None:
            margin = numerator / revenue
            if margin <= 1.01:  # reject garbage: a real margin can't exceed 100%
                return margin, "computed"
        return info_fallback, "info_fallback"

    @staticmethod
    def _statement_period_end(statement) -> Optional[str]:
        """ISO date of the most recent column in a statement DataFrame."""
        if statement is None or statement.empty:
            return None
        try:
            return pd.Timestamp(statement.columns[0]).date().isoformat()
        except Exception:
            return None

    @staticmethod
    def _epoch_to_date(value) -> Optional[str]:
        """Unix timestamp (as returned in e.g. info['mostRecentQuarter']) to
        an ISO date string."""
        if value is None:
            return None
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
        except Exception:
            return None