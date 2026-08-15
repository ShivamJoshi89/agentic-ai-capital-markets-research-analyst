import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  TrendingUp,
  DollarSign,
  Building2,
  Newspaper,
  Globe,
  AlertTriangle,
  FileText,
  Info,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { parseNumeric } from "../utils/format.js";

import Overview from "../components/pages/Overview.jsx";
import MarketPerformance from "../components/pages/MarketPerformance.jsx";
import Fundamentals from "../components/pages/Fundamentals.jsx";
import PeerComparison from "../components/pages/PeerComparison.jsx";
import NewsSentiment from "../components/pages/NewsSentiment.jsx";
import MacroEnvironment from "../components/pages/MacroEnvironment.jsx";
import RiskAnalysis from "../components/pages/RiskAnalysis.jsx";
import ResearchMemo from "../components/pages/ResearchMemo.jsx";
import About from "../components/pages/About.jsx";

const NAV = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, component: Overview },
  { id: "market", label: "Market Performance", icon: TrendingUp, component: MarketPerformance },
  { id: "fundamentals", label: "Fundamentals", icon: DollarSign, component: Fundamentals },
  { id: "peers", label: "Peer Comparison", icon: Building2, component: PeerComparison },
  { id: "news", label: "News & Sentiment", icon: Newspaper, component: NewsSentiment },
  { id: "macro", label: "Macro Environment", icon: Globe, component: MacroEnvironment },
  { id: "risk", label: "Risk Analysis", icon: AlertTriangle, component: RiskAnalysis },
  { id: "memo", label: "Research Memo", icon: FileText, component: ResearchMemo },
  { id: "about", label: "About", icon: Info, component: About },
];

export default function Dashboard({ data, onReset, onChangeTicker, error, busy }) {
  const [activePage, setActivePage] = useState("overview");
  const [now, setNow] = useState(new Date());
  const [changingTicker, setChangingTicker] = useState(false);
  const [tickerInput, setTickerInput] = useState("");
  const inputRef = useRef(null);
  const wasBusy = useRef(busy);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Jump back to Overview whenever the analyzed ticker actually changes, so
  // the user never lands on a stale-looking page (e.g. Research Memo) that
  // silently now belongs to a different company.
  useEffect(() => {
    setActivePage("overview");
  }, [data.ticker]);

  // Reveal the inline search fresh (cleared + focused) whenever it opens.
  useEffect(() => {
    if (changingTicker) {
      setTickerInput("");
      const id = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(id);
    }
    return undefined;
  }, [changingTicker]);

  // Close the inline search automatically once a switch finishes - but only
  // on success. If it errored, keep it open (with the error shown) so the
  // user can fix the ticker and retry without losing their place.
  useEffect(() => {
    if (wasBusy.current && !busy && !error) {
      setChangingTicker(false);
    }
    wasBusy.current = busy;
  }, [busy, error]);

  // "/" focuses the ticker switcher from anywhere in the dashboard, unless
  // the user is already typing in some other input.
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key !== "/") return;
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      e.preventDefault();
      setChangingTicker(true);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const submitTickerChange = () => {
    const cleaned = tickerInput.trim().toUpperCase();
    if (!cleaned || busy) return;
    onChangeTicker(cleaned);
  };

  const metrics = data.market_data?.metrics ?? {};
  const price = parseNumeric(metrics.latest_price);
  const changePct = parseNumeric(metrics.price_change_pct);
  const ActiveComponent = NAV.find((item) => item.id === activePage)?.component ?? Overview;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex min-h-screen"
    >
      {/* Sidebar */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-navy-600 bg-navy-800 p-4">
        <div className="border-b border-navy-600 pb-4">
          <div className="text-lg font-extrabold text-gold">📊 AI Analyst</div>
          <div className="text-[10px] font-medium uppercase tracking-widest text-gray-400">
            Institutional Research Platform
          </div>
          <button
            onClick={onReset}
            className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border
                       border-navy-600 px-2.5 py-1.5 text-xs text-gray-400 transition
                       hover:border-gold hover:text-gold"
          >
            <RotateCcw size={12} />
            New Analysis
          </button>
        </div>

        <nav className="mt-4 flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = item.id === activePage;
            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                className={`flex items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 text-left
                            text-sm transition ${
                              active
                                ? "border-gold bg-navy-700 font-semibold text-gold"
                                : "border-transparent text-gray-400 hover:bg-navy-700 hover:text-white"
                            }`}
              >
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex items-center justify-between gap-4 border-b border-navy-600 bg-navy-800 px-6 py-3">
          {changingTicker ? (
            <div className="flex max-w-md flex-1 items-center gap-2">
              <div className="relative flex-1">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  ref={inputRef}
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") submitTickerChange();
                    if (e.key === "Escape") setChangingTicker(false);
                  }}
                  disabled={busy}
                  placeholder="Enter new ticker..."
                  className="w-full rounded-lg border-2 border-gold bg-navy-700 py-1.5 pl-9 pr-3
                             text-sm text-white placeholder-gray-500 outline-none
                             shadow-[0_0_14px_rgba(240,180,41,0.35)] disabled:opacity-60"
                />
              </div>
              <button
                onClick={submitTickerChange}
                disabled={busy || !tickerInput.trim()}
                className="shrink-0 rounded-lg bg-gold px-3 py-1.5 text-sm font-bold text-navy-900
                           transition hover:bg-gold-light disabled:opacity-50"
              >
                Analyze
              </button>
              <button
                onClick={() => setChangingTicker(false)}
                title="Cancel (Esc)"
                className="shrink-0 rounded-lg p-1.5 text-gray-400 transition hover:text-white"
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <div className="flex min-w-0 items-center gap-4">
              <span className="shrink-0 rounded-lg bg-gold px-3 py-1 text-sm font-extrabold text-navy-900">
                {data.ticker}
              </span>
              <span className="truncate font-semibold text-white">
                {data.company_info?.company_name ?? ""}
              </span>
              {price !== null && (
                <span className="shrink-0 font-bold text-white">
                  ${price.toFixed(2)}{" "}
                  {changePct !== null && (
                    <span className={changePct >= 0 ? "text-success" : "text-danger"}>
                      {changePct >= 0 ? "+" : ""}
                      {changePct.toFixed(2)}%
                    </span>
                  )}
                </span>
              )}
              <button
                onClick={() => setChangingTicker(true)}
                title="Change ticker (press /)"
                className="flex shrink-0 items-center gap-1.5 rounded-lg border border-navy-600
                           px-2.5 py-1 text-xs text-gray-400 transition hover:border-gold hover:text-gold"
              >
                <Search size={12} />
                Change Ticker
              </button>
            </div>
          )}

          <div className="shrink-0 text-xs text-gray-400 tabular-nums">
            {now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}{" "}
            {now.toLocaleTimeString()}
          </div>
        </header>

        {changingTicker && error && (
          <div className="border-b border-danger/40 bg-danger/10 px-6 py-2 text-xs text-danger">
            {error}
          </div>
        )}

        {/* Page content */}
        <main className="min-w-0 flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activePage}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
            >
              <ActiveComponent data={data} />
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className="shrink-0 border-t border-navy-600 bg-navy-800 px-6 py-2 text-center text-[11px] leading-relaxed text-gray-500">
          Research &amp; educational demo — <span className="text-gray-400">not investment advice</span> and not a
          commercial data product. Figures come from yfinance / FRED / SEC EDGAR and may be delayed, incomplete, or
          inaccurate; verify against primary filings before relying on them.
        </footer>
      </div>
    </motion.div>
  );
}
