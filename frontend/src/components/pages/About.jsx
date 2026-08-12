import {
  Bot,
  Database,
  TrendingUp,
  DollarSign,
  Landmark,
  Newspaper,
  Globe,
  Building2,
  AlertTriangle,
  FileText,
} from "lucide-react";

const AGENTS = [
  { icon: TrendingUp, name: "Market Data Agent", desc: "Historical prices, returns, volatility, moving averages, and drawdown from yfinance." },
  { icon: DollarSign, name: "Fundamentals Agent", desc: "Income statement, balance sheet, profitability, and valuation ratios." },
  { icon: Landmark, name: "Financing & Dilution Risk Agent", desc: "SEC EDGAR filings scan for dilutive financing activity and cash runway." },
  { icon: Newspaper, name: "News Agent", desc: "Recent headlines from Google News RSS with keyword-based sentiment classification." },
  { icon: Globe, name: "Macro Agent", desc: "Fed funds rate, treasury yields, CPI inflation, unemployment, and VIX from FRED." },
  { icon: Building2, name: "Peer Comparison Agent", desc: "Comparable-company selection and relative valuation across the peer set." },
  { icon: AlertTriangle, name: "Risk Agent", desc: "Consolidates valuation, leverage, market, macro, sentiment, and sector risks." },
  { icon: FileText, name: "Report Agent", desc: "Synthesizes all agent output into a narrative research memo via OpenAI." },
];

const DATA_SOURCES = [
  "yfinance — market prices and company fundamentals",
  "FRED — macroeconomic indicators",
  "Google News RSS — news headlines",
  "SEC EDGAR — financing and dilution filings",
  "OpenAI — research memo generation",
];

export default function About() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-extrabold text-gold">About</h1>

      <div className="rounded-2xl border border-navy-600 bg-navy-700 p-6 md:p-8 space-y-8">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
            What This Is
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-gray-300">
            This tool automates the first pass of equity research: a set of specialized agents
            each pull one piece of the picture — price action, fundamentals, financing risk,
            news, macro conditions, peers, and risk factors — and a final agent synthesizes
            everything into a narrative research memo.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-gray-300">
            It is <strong className="text-white">not</strong> a stock price prediction tool, and
            it does <strong className="text-white">not</strong> constitute investment advice. It
            is a research aid meant to speed up information gathering and synthesis — decision
            support, not decision making.
          </p>
        </div>

        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
            The Agent Pipeline
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {AGENTS.map((agent) => {
              const Icon = agent.icon;
              return (
                <div
                  key={agent.name}
                  className="flex gap-3 rounded-xl border border-navy-600 bg-navy-800 p-4"
                >
                  <Icon size={18} className="mt-0.5 shrink-0 text-gold" />
                  <div>
                    <div className="text-sm font-bold text-white">{agent.name}</div>
                    <div className="mt-1 text-xs leading-relaxed text-gray-400">{agent.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
            Data Sources
          </h2>
          <div className="mt-3 flex items-start gap-3 rounded-xl border border-navy-600 bg-navy-800 p-4">
            <Database size={18} className="mt-0.5 shrink-0 text-gold" />
            <ul className="space-y-1.5 text-sm leading-relaxed text-gray-300">
              {DATA_SOURCES.map((source) => (
                <li key={source}>{source}</li>
              ))}
            </ul>
          </div>
        </div>

        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
            Methodology
          </h2>
          <div className="mt-3 flex items-start gap-3 rounded-xl border border-navy-600 bg-navy-800 p-4">
            <Bot size={18} className="mt-0.5 shrink-0 text-gold" />
            <p className="text-sm leading-relaxed text-gray-300">
              The research memo follows a Wall Street-style structure: executive summary,
              financial analysis, market performance, risk assessment, bull/base/bear cases, and
              an investment recommendation with disclaimers — grounded in the numeric output of
              the agents above rather than free-form generation.
            </p>
          </div>
        </div>

        <hr className="border-t border-gold/40" />
        <p className="text-[11px] leading-relaxed text-gray-500">
          Educational and portfolio purposes only. Not investment advice. Always consult a
          qualified financial professional before making investment decisions.
        </p>
      </div>
    </div>
  );
}
