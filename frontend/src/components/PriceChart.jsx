import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { formatChartDate } from "../utils/format.js";

const GOLD = "#f0b429";
const GREEN = "#00c851";
const RED = "#ff4444";
const GRID = "#1e2d4a";
const SURFACE = "#141929";
const TEXT = "#a0aec0";

const tooltipStyle = {
  backgroundColor: SURFACE,
  border: `1px solid ${GRID}`,
  borderRadius: "8px",
  color: "#ffffff",
  fontSize: "12px",
};

/**
 * Stacked price + volume panels sharing a synchronized x-axis (one scale per
 * panel - deliberately not a dual-axis overlay). Gold price line, volume bars
 * colored by up/down day.
 */
export default function PriceChart({ history }) {
  const data = useMemo(() => {
    if (!Array.isArray(history)) return [];
    return history.map((point, i) => ({
      ...point,
      up: i === 0 ? true : (point.close ?? 0) >= (history[i - 1].close ?? 0),
    }));
  }, [history]);

  if (data.length === 0) {
    return <div className="text-gray-500 text-sm">No price history available.</div>;
  }

  return (
    <div className="bg-navy-700 border border-navy-600 rounded-xl p-4">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} syncId="pricevol" margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatChartDate}
            stroke={TEXT}
            tick={{ fontSize: 11 }}
            interval="preserveStartEnd"
            minTickGap={60}
            axisLine={{ stroke: GRID }}
            tickLine={false}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(v) => `$${v}`}
            stroke={TEXT}
            tick={{ fontSize: 11 }}
            width={64}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            labelStyle={{ color: TEXT }}
            formatter={(v) => [`$${Number(v).toFixed(2)}`, "Close"]}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke={GOLD}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: GOLD, stroke: SURFACE }}
          />
        </LineChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={110}>
        <BarChart data={data} syncId="pricevol" margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="date" hide />
          <YAxis
            tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(0)}M` : v)}
            stroke={TEXT}
            tick={{ fontSize: 10 }}
            width={64}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            labelStyle={{ color: TEXT }}
            labelFormatter={formatChartDate}
            formatter={(v) => [Number(v).toLocaleString(), "Volume"]}
          />
          <Bar dataKey="volume" isAnimationActive={false}>
            {data.map((point, i) => (
              <Cell key={i} fill={point.up ? GREEN : RED} fillOpacity={0.75} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
