import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  DollarSign,
  Landmark,
  Newspaper,
  Globe,
  Building2,
  AlertTriangle,
  FileText,
  Check,
} from "lucide-react";

// Cumulative seconds at which each agent "completes" (~50s total, matching
// the real pipeline; the report/LLM stage is the longest)
const AGENTS = [
  { name: "Market Data", icon: TrendingUp, done: 5 },
  { name: "Fundamentals", icon: DollarSign, done: 9 },
  { name: "Financing", icon: Landmark, done: 13 },
  { name: "News", icon: Newspaper, done: 18 },
  { name: "Macro", icon: Globe, done: 24 },
  { name: "Peers", icon: Building2, done: 31 },
  { name: "Risk", icon: AlertTriangle, done: 36 },
  { name: "Report", icon: FileText, done: 50 },
];

const TOTAL = 50;

/** Full-screen overlay simulating pipeline progress while the API request
 *  runs. The overlay unmounts when the real response arrives. */
export default function LoadingPipeline() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((s) => s + 0.25), 250);
    return () => clearInterval(timer);
  }, []);

  // Cap at 97% - the real completion closes the overlay
  const progress = Math.min((elapsed / TOTAL) * 100, 97);
  const remaining = Math.max(Math.ceil(TOTAL - elapsed), 0);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-navy-900/95 backdrop-blur-sm"
    >
      <div className="text-gold font-bold text-xl mb-1">Running Multi-Agent Analysis</div>
      <div className="text-gray-400 text-sm mb-10">
        Eight specialized agents are building your research report
      </div>

      <div className="flex items-center gap-2 flex-wrap justify-center px-6 max-w-4xl">
        {AGENTS.map((agent, i) => {
          const isDone = elapsed >= agent.done;
          const isActive = !isDone && (i === 0 || elapsed >= AGENTS[i - 1].done);
          const Icon = agent.icon;

          return (
            <div key={agent.name} className="flex items-center gap-2">
              <motion.div
                animate={
                  isActive
                    ? { scale: [1, 1.06, 1], borderColor: ["#1e2d4a", "#f0b429", "#1e2d4a"] }
                    : {}
                }
                transition={isActive ? { repeat: Infinity, duration: 1.4 } : {}}
                className={`flex flex-col items-center gap-1.5 rounded-xl border px-4 py-3 w-24 ${
                  isDone
                    ? "border-gold bg-gold/10"
                    : isActive
                      ? "border-navy-600 bg-navy-700"
                      : "border-navy-600 bg-navy-800 opacity-50"
                }`}
              >
                {isDone ? (
                  <Check size={20} className="text-gold" />
                ) : (
                  <Icon size={20} className={isActive ? "text-gold" : "text-gray-500"} />
                )}
                <span
                  className={`text-[10px] font-semibold uppercase tracking-wider ${
                    isDone ? "text-gold" : isActive ? "text-white" : "text-gray-500"
                  }`}
                >
                  {agent.name}
                </span>
              </motion.div>
              {i < AGENTS.length - 1 && (
                <div className={`h-px w-4 ${isDone ? "bg-gold" : "bg-navy-600"}`} />
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-12 w-full max-w-xl px-6">
        <div className="h-1.5 w-full rounded-full bg-navy-700 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gold"
            animate={{ width: `${progress}%` }}
            transition={{ ease: "linear", duration: 0.25 }}
          />
        </div>
        <div className="mt-3 flex justify-between text-xs text-gray-400">
          <span>{Math.round(progress)}%</span>
          <span>
            {remaining > 0 ? `~${remaining}s remaining` : "Finalizing report..."}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
