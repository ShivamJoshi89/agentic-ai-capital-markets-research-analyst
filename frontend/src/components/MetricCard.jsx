import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import AnimatedNumber from "./AnimatedNumber.jsx";
import { parseNumeric } from "../utils/format.js";

/**
 * Dark metric card. If `signed`, the value colors green/red by sign with an
 * up/down arrow. Numeric values animate counting up; strings render as-is.
 */
export default function MetricCard({
  label,
  value,
  decimals = 2,
  prefix = "",
  suffix = "",
  signed = false,
  sub = null,
}) {
  const numeric = parseNumeric(value);
  const isNumeric = numeric !== null;
  const positive = signed && isNumeric && numeric > 0;
  const negative = signed && isNumeric && numeric < 0;

  const valueColor = positive ? "text-success" : negative ? "text-danger" : "text-white";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="bg-navy-700 border border-navy-600 rounded-xl px-5 py-4"
    >
      <div className={`flex items-center gap-1.5 text-2xl font-bold ${valueColor}`}>
        {positive && <ArrowUpRight size={20} className="text-success" />}
        {negative && <ArrowDownRight size={20} className="text-danger" />}
        {isNumeric ? (
          <AnimatedNumber
            value={numeric}
            decimals={decimals}
            prefix={`${positive ? "+" : ""}${prefix}`}
            suffix={suffix}
          />
        ) : (
          <span className="text-xl">{value ?? "N/A"}</span>
        )}
      </div>
      <div className="mt-1.5 text-[11px] font-medium uppercase tracking-widest text-gray-400">
        {label}
      </div>
      {sub && <div className="mt-1 text-xs text-gray-500">{sub}</div>}
    </motion.div>
  );
}
