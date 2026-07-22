import { useEffect, useState } from "react";
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
  RotateCcw,
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

const NAV = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, component: Overview },
  { id: "market", label: "Market Performance", icon: TrendingUp, component: MarketPerformance },
  { id: "fundamentals", label: "Fundamentals", icon: DollarSign, component: Fundamentals },
  { id: "peers", label: "Peer Comparison", icon: Building2, component: PeerComparison },
  { id: "news", label: "News & Sentiment", icon: Newspaper, component: NewsSentiment },
  { id: "macro", label: "Macro Environment", icon: Globe, component: MacroEnvironment },
  { id: "risk", label: "Risk Analysis", icon: AlertTriangle, component: RiskAnalysis },
  { id: "memo", label: "Research Memo", icon: FileText, component: ResearchMemo },
];

export default function Dashboard({ data, onReset }) {
  const [activePage, setActivePage] = useState("overview");
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

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

        <button
          onClick={onReset}
          className="mt-4 flex items-center justify-center gap-2 rounded-lg border border-navy-600
                     px-3 py-2.5 text-sm text-gray-400 transition hover:border-gold hover:text-gold"
        >
          <RotateCcw size={14} />
          New Analysis
        </button>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex items-center justify-between border-b border-navy-600 bg-navy-800 px-6 py-3">
          <div className="flex items-center gap-4">
            <span className="rounded-lg bg-gold px-3 py-1 text-sm font-extrabold text-navy-900">
              {data.ticker}
            </span>
            <span className="font-semibold text-white">
              {data.company_info?.company_name ?? ""}
            </span>
            {price !== null && (
              <span className="text-white font-bold">
                ${price.toFixed(2)}{" "}
                {changePct !== null && (
                  <span className={changePct >= 0 ? "text-success" : "text-danger"}>
                    {changePct >= 0 ? "+" : ""}
                    {changePct.toFixed(2)}%
                  </span>
                )}
              </span>
            )}
          </div>
          <div className="text-xs text-gray-400 tabular-nums">
            {now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}{" "}
            {now.toLocaleTimeString()}
          </div>
        </header>

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
      </div>
    </motion.div>
  );
}
