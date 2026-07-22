import MetricCard from "../MetricCard.jsx";

const SEVERITY_STYLES = {
  High: { border: "border-l-danger", bg: "bg-danger/5", chip: "bg-danger/15 text-danger" },
  Medium: { border: "border-l-gold", bg: "bg-gold/5", chip: "bg-gold/15 text-gold" },
  Low: { border: "border-l-success", bg: "bg-success/5", chip: "bg-success/15 text-success" },
};

export default function RiskAnalysis({ data }) {
  const riskData = data.risk_data ?? {};
  const risks = riskData.risks ?? [];

  const highCount = risks.filter((r) => r.severity === "High").length;
  const mediumCount = risks.filter((r) => r.severity === "Medium").length;
  const lowCount = risks.filter((r) => r.severity === "Low").length;
  const riskScore = Math.min(
    (highCount * 100 + mediumCount * 50) / Math.max(risks.length, 1),
    100
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold text-gold">Risk Analysis</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="High Severity" value={highCount} decimals={0} />
        <MetricCard label="Medium Severity" value={mediumCount} decimals={0} />
        <MetricCard label="Low Severity" value={lowCount} decimals={0} />
        <MetricCard label="Risk Score / 100" value={Math.round(riskScore)} decimals={0} />
      </div>

      {riskData.summary && (
        <div
          className={`whitespace-pre-wrap rounded-xl border-l-4 p-5 text-sm leading-relaxed text-gray-200 ${
            highCount >= 2
              ? "border-l-danger bg-danger/5"
              : highCount === 1
                ? "border-l-gold bg-gold/5"
                : "border-l-success bg-success/5"
          }`}
        >
          {riskData.summary}
        </div>
      )}

      <div className="space-y-3">
        {risks.length === 0 && (
          <p className="text-sm text-gray-500">No significant risks identified.</p>
        )}
        {risks.map((risk, i) => {
          const style = SEVERITY_STYLES[risk.severity] ?? SEVERITY_STYLES.Low;
          return (
            <div
              key={i}
              className={`rounded-xl border border-navy-600 border-l-4 ${style.border} ${style.bg} p-5`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-white">{risk.title}</span>
                <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${style.chip}`}>
                  {risk.severity} severity
                </span>
                <span className="rounded bg-navy-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-300">
                  {risk.category}
                </span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-gray-300">{risk.description}</p>
              <p className="mt-2 text-xs text-gray-400">
                <strong>Metric:</strong> {risk.metric ?? "N/A"} · <strong>Potential impact:</strong>{" "}
                {risk.impact ?? "Unknown"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
