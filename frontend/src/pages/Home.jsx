import { useState } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Bot,
  Database,
  Zap,
  Landmark,
  TrendingUp,
  DollarSign,
  Newspaper,
  Globe,
  Building2,
  AlertTriangle,
  FileText,
  RotateCcw,
} from "lucide-react";

const FEATURES = [
  { icon: Bot, title: "8 AI Agents", sub: "Specialized analysts working in concert" },
  { icon: Database, title: "5 Data Sources", sub: "yfinance, FRED, Google News, SEC EDGAR, OpenAI" },
  { icon: Zap, title: "Real-Time FRED Data", sub: "Live fed funds, treasury, CPI, unemployment, VIX" },
  { icon: Landmark, title: "Wall Street Methodology", sub: "Comps, earnings quality, bull/base/bear cases" },
];

const PIPELINE = [
  { icon: TrendingUp, name: "Market Data" },
  { icon: DollarSign, name: "Fundamentals" },
  { icon: Landmark, name: "Financing" },
  { icon: Newspaper, name: "News" },
  { icon: Globe, name: "Macro" },
  { icon: Building2, name: "Peers" },
  { icon: AlertTriangle, name: "Risk" },
  { icon: FileText, name: "Report" },
];

export default function Home({ onAnalyze, error, busy, lastTicker }) {
  const [ticker, setTicker] = useState("");

  const submit = () => {
    const cleaned = ticker.trim().toUpperCase();
    if (cleaned && !busy) onAnalyze(cleaned);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen flex flex-col items-center justify-center px-6 py-16"
    >
      {/* Hero */}
      <motion.h1
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="text-4xl md:text-6xl font-extrabold text-center text-white leading-tight"
      >
        Institutional-Grade
        <br />
        Equity Research
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.25 }}
        className="mt-4 text-lg text-gold font-medium"
      >
        Powered by Multi-Agent AI
      </motion.p>

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.45 }}
        className="mt-10 w-full max-w-xl"
      >
        <div className="relative">
          <Search size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Enter a ticker — JPM, AAPL, NVDA..."
            className="w-full rounded-2xl border-2 border-navy-600 bg-navy-700 py-4 pl-14 pr-6
                       text-lg text-white placeholder-gray-500 outline-none transition
                       focus:border-gold focus:shadow-[0_0_24px_rgba(240,180,41,0.35)]"
          />
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={submit}
          disabled={busy}
          className="mt-4 w-full rounded-2xl bg-gold py-4 text-lg font-bold text-navy-900
                     transition hover:bg-gold-light disabled:opacity-60"
        >
          {busy ? "Analyzing..." : "Analyze"}
        </motion.button>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 rounded-xl border border-danger/50 bg-danger/10 px-5 py-3 text-sm text-danger"
          >
            {error}
          </motion.div>
        )}

        {lastTicker && (
          <div className="mt-4 flex justify-center">
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={() => !busy && onAnalyze(lastTicker)}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-full border border-navy-600
                         bg-navy-700 px-3.5 py-1.5 text-xs text-gray-300 transition
                         hover:border-gold hover:text-gold disabled:opacity-60"
            >
              <RotateCcw size={11} />
              Last analyzed: <span className="font-semibold text-white">{lastTicker}</span>
            </motion.button>
          </div>
        )}
      </motion.div>

      {/* Feature cards */}
      <div className="mt-14 grid w-full max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((feature, i) => {
          const Icon = feature.icon;
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.6 + i * 0.12 }}
              className="rounded-xl border border-navy-600 bg-navy-700 p-5 text-center"
            >
              <Icon size={26} className="mx-auto text-gold" />
              <div className="mt-3 font-bold text-white">{feature.title}</div>
              <div className="mt-1 text-xs text-gray-400">{feature.sub}</div>
            </motion.div>
          );
        })}
      </div>

      {/* Agent pipeline */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.1, duration: 0.6 }}
        className="mt-14 w-full max-w-5xl"
      >
        <div className="mb-4 text-center text-[11px] font-semibold uppercase tracking-[0.25em] text-gray-400">
          Analysis Pipeline
        </div>
        <div className="flex flex-wrap items-center justify-center gap-1">
          {PIPELINE.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={step.name} className="flex items-center gap-1">
                <motion.div
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 1.2 + i * 0.15 }}
                  className="flex w-[92px] flex-col items-center gap-1.5 rounded-xl border
                             border-navy-600 bg-navy-700 px-3 py-3"
                >
                  <Icon size={18} className="text-gold" />
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                    {step.name}
                  </span>
                </motion.div>
                {i < PIPELINE.length - 1 && (
                  <motion.div
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ delay: 1.3 + i * 0.15, duration: 0.3 }}
                    className="h-0.5 w-5 origin-left bg-gold/60"
                  />
                )}
              </div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}
