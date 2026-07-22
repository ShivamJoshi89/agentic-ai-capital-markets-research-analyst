import { Zap, AlertTriangle, ExternalLink } from "lucide-react";
import MetricCard from "../MetricCard.jsx";

const SENTIMENT_BADGES = {
  Positive: "bg-success/15 text-success",
  Negative: "bg-danger/15 text-danger",
  Neutral: "bg-navy-600 text-gray-300",
};

export default function NewsSentiment({ data }) {
  const news = data.news_data ?? {};
  const articles = news.articles ?? [];
  const counts = news.sentiment_counts ?? {};
  const flags = data.risk_data?.special_situations ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold text-gold">News &amp; Sentiment</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Overall Sentiment" value={news.overall_sentiment ?? "N/A"} />
        <MetricCard label="Positive Articles" value={counts.positive ?? 0} decimals={0} />
        <MetricCard label="Neutral Articles" value={counts.neutral ?? 0} decimals={0} />
        <MetricCard label="Negative Articles" value={counts.negative ?? 0} decimals={0} />
      </div>

      {/* Special situations radar */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-gray-400">
          Special Situations Radar
        </h2>
        {flags.length === 0 ? (
          <p className="text-sm text-gray-500">
            No special situation signals detected in recent headlines.
          </p>
        ) : (
          <div className="space-y-3">
            {flags.map((flag, i) => {
              const isOpportunity = flag.signal_type === "opportunity_signal";
              return (
                <div
                  key={i}
                  className={`rounded-xl border-l-4 p-4 ${
                    isOpportunity
                      ? "border-l-success bg-success/5"
                      : "border-l-gold bg-gold/5"
                  }`}
                >
                  <div className="flex items-center gap-2 text-sm font-bold text-white">
                    {isOpportunity ? (
                      <Zap size={15} className="text-success" />
                    ) : (
                      <AlertTriangle size={15} className="text-gold" />
                    )}
                    {flag.category}
                    <span className="text-xs font-medium text-gray-400">
                      — {isOpportunity ? "Opportunity" : "Risk"} signal (matched: &quot;
                      {flag.matched_keyword}&quot;)
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm text-gray-300">{flag.headline}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Headlines */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-gray-400">
          Recent Headlines ({news.total_articles ?? articles.length})
        </h2>
        <div className="space-y-3">
          {articles.length === 0 && (
            <p className="text-sm text-gray-500">No recent articles found.</p>
          )}
          {articles.map((article, i) => (
            <div
              key={i}
              className="rounded-xl border border-navy-600 border-l-4 border-l-sky-400 bg-navy-700 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-semibold text-white">{article.title}</div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-gray-400">
                    <span
                      className={`rounded px-1.5 py-0.5 font-semibold ${
                        SENTIMENT_BADGES[article.sentiment] ?? SENTIMENT_BADGES.Neutral
                      }`}
                    >
                      {article.sentiment ?? "Neutral"}
                    </span>
                    <span>{article.source}</span>
                    <span>{article.published_date}</span>
                  </div>
                </div>
                {article.url && (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-gold transition hover:text-gold-light"
                  >
                    <ExternalLink size={16} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
