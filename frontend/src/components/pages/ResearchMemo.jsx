import { useRef, useState } from "react";
import { Download, Loader2 } from "lucide-react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

const HEADER_RE = /^(?:\d+\.\s*)?([A-Z][A-Z0-9 /&()',.\-]{3,}):?$/;

/** Split memo text into [{title, body}] sections on numbered/uppercase
 *  header lines (mirrors the backend's split_memo_sections). */
function splitMemoSections(memo) {
  const sections = [];
  let title = null;
  let lines = [];

  for (const line of memo.split("\n")) {
    const match = line.trim().match(HEADER_RE);
    if (match) {
      if (title !== null || lines.length) {
        sections.push({ title, body: lines.join("\n").trim() });
      }
      title = match[1].trim().replace(/:$/, "");
      lines = [];
    } else {
      lines.push(line);
    }
  }
  if (title !== null || lines.length) {
    sections.push({ title, body: lines.join("\n").trim() });
  }

  if (!sections.some((s) => s.title)) return [{ title: null, body: memo.trim() }];
  return sections;
}

const CASE_STYLES = {
  BULL: { border: "border-l-success", bg: "bg-success/5", tag: "text-success", icon: "🐂" },
  BEAR: { border: "border-l-danger", bg: "bg-danger/5", tag: "text-danger", icon: "🐻" },
  BASE: { border: "border-l-sky-400", bg: "bg-sky-400/5", tag: "text-sky-400", icon: "⚖️" },
};

// Print-only palette: white background, black text, muted color accents that
// stay legible on paper (the on-screen gold/green/red are too low-contrast
// or too saturated for a printed document).
const PRINT_CASE_STYLES = {
  BULL: { border: "#16a34a", bg: "#f0fdf4", tag: "#15803d", icon: "🐂" },
  BEAR: { border: "#dc2626", bg: "#fef2f2", tag: "#b91c1c", icon: "🐻" },
  BASE: { border: "#2563eb", bg: "#eff6ff", tag: "#1d4ed8", icon: "⚖️" },
};
const PRINT_ACCENT = "#92400e"; // amber-800: reads as "gold" but has real contrast on white

function caseType(title) {
  const upper = (title ?? "").toUpperCase();
  if (upper.includes("BULL")) return "BULL";
  if (upper.includes("BEAR")) return "BEAR";
  if (upper.includes("BASE")) return "BASE";
  return null;
}

export default function ResearchMemo({ data }) {
  const memo = data.memo_data?.memo ?? "";
  const reportDate = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const printRef = useRef(null);
  const [isExporting, setIsExporting] = useState(false);

  if (!memo) {
    return <div className="text-gray-400">No research memo was generated for this analysis.</div>;
  }

  const sections = splitMemoSections(memo);
  const companyName = data.company_info?.company_name ?? data.ticker;

  const handleDownloadPdf = async () => {
    if (!printRef.current || isExporting) return;
    setIsExporting(true);
    try {
      const canvas = await html2canvas(printRef.current, {
        backgroundColor: "#ffffff",
        scale: 2,
        useCORS: true,
      });

      const pdf = new jsPDF({ unit: "mm", format: "a4", orientation: "portrait" });
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 10;
      const contentWidthMm = pageWidth - margin * 2;
      const contentHeightMm = pageHeight - margin * 2;

      // Slice the full-height canvas into page-sized chunks so long memos
      // paginate correctly instead of being cropped to a single page.
      const pageHeightPx = (contentHeightMm * canvas.width) / contentWidthMm;
      let renderedPx = 0;
      let pageIndex = 0;

      while (renderedPx < canvas.height) {
        const sliceHeightPx = Math.min(pageHeightPx, canvas.height - renderedPx);

        const pageCanvas = document.createElement("canvas");
        pageCanvas.width = canvas.width;
        pageCanvas.height = sliceHeightPx;
        const ctx = pageCanvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
        ctx.drawImage(
          canvas,
          0, renderedPx, canvas.width, sliceHeightPx,
          0, 0, canvas.width, sliceHeightPx
        );

        const sliceHeightMm = (sliceHeightPx * contentWidthMm) / canvas.width;
        if (pageIndex > 0) pdf.addPage();
        pdf.addImage(pageCanvas.toDataURL("image/png"), "PNG", margin, margin, contentWidthMm, sliceHeightMm);

        renderedPx += sliceHeightPx;
        pageIndex += 1;
      }

      const safeTicker = (data.ticker || "TICKER").replace(/[^A-Z0-9]/gi, "");
      const fileDate = new Date().toISOString().slice(0, 10);
      pdf.save(`${safeTicker}_Research_Memo_${fileDate}.pdf`);
    } catch (err) {
      console.error("PDF export failed:", err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold text-gold">Research Memo</h1>
        <button
          onClick={handleDownloadPdf}
          disabled={isExporting}
          className="flex items-center gap-2 rounded-lg border border-navy-600 px-4 py-2 text-sm
                     text-gray-300 transition hover:border-gold hover:text-gold disabled:opacity-60"
        >
          {isExporting ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
          {isExporting ? "Generating PDF..." : "Download PDF"}
        </button>
      </div>

      <div className="rounded-2xl border border-navy-600 bg-navy-700 p-8 md:p-10">
        {/* Report header */}
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b-2 border-gold pb-5">
          <div>
            <div className="text-[11px] font-extrabold uppercase tracking-[0.3em] text-gold">
              {data.ticker} Equity Research
            </div>
            <div className="mt-1 text-xl font-extrabold text-white">{companyName}</div>
          </div>
          <div className="text-right text-xs text-gray-400">
            {reportDate}
            <br />
            Multi-Agent AI Research Desk
          </div>
        </div>

        {/* Sections */}
        {sections.map((section, i) => {
          const type = caseType(section.title);

          if (type) {
            const style = CASE_STYLES[type];
            return (
              <div
                key={i}
                className={`my-5 rounded-xl border border-navy-600 border-l-4 ${style.border} ${style.bg} p-5`}
              >
                <div className={`text-xs font-extrabold uppercase tracking-[0.15em] ${style.tag}`}>
                  {style.icon} {section.title}
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-gray-200">
                  {section.body}
                </p>
              </div>
            );
          }

          return (
            <div key={i}>
              {section.title && (
                <>
                  <hr className="my-5 border-t border-gold/40" />
                  <div className="text-sm font-bold uppercase tracking-wider text-gold">
                    {section.title}
                  </div>
                </>
              )}
              {section.body && (
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-gray-200">
                  {section.body}
                </p>
              )}
            </div>
          );
        })}

        <hr className="my-6 border-t border-gold/40" />
        <p className="text-[11px] leading-relaxed text-gray-500">
          For informational and educational purposes only. Not investment advice. Data sourced from
          public APIs and may be delayed or incomplete. Generated by a multi-agent AI system.
        </p>
      </div>

      {/* Hidden print-only layout: white background, black text, captured by
          html2canvas for the PDF export. Kept in the layout tree (position:
          fixed) but invisible (opacity 0) and non-interactive so it never
          flashes on screen. */}
      <div
        ref={printRef}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "800px",
          opacity: 0,
          pointerEvents: "none",
          zIndex: -1,
          backgroundColor: "#ffffff",
          color: "#111111",
          fontFamily: "Arial, Helvetica, sans-serif",
          padding: "48px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            gap: "12px",
            borderBottom: `3px solid ${PRINT_ACCENT}`,
            paddingBottom: "16px",
            marginBottom: "20px",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 800,
                letterSpacing: "3px",
                color: PRINT_ACCENT,
                textTransform: "uppercase",
              }}
            >
              {data.ticker} Equity Research
            </div>
            <div style={{ fontSize: "22px", fontWeight: 800, marginTop: "4px" }}>{companyName}</div>
          </div>
          <div style={{ textAlign: "right", fontSize: "11px", color: "#555555" }}>
            {reportDate}
            <br />
            Multi-Agent AI Research Desk
          </div>
        </div>

        {sections.map((section, i) => {
          const type = caseType(section.title);

          if (type) {
            const style = PRINT_CASE_STYLES[type];
            return (
              <div
                key={i}
                style={{
                  margin: "16px 0",
                  padding: "14px 16px",
                  borderRadius: "6px",
                  borderLeft: `4px solid ${style.border}`,
                  backgroundColor: style.bg,
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: 800,
                    letterSpacing: "1.5px",
                    textTransform: "uppercase",
                    color: style.tag,
                    marginBottom: "6px",
                  }}
                >
                  {style.icon} {section.title}
                </div>
                <div style={{ fontSize: "12.5px", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                  {section.body}
                </div>
              </div>
            );
          }

          return (
            <div key={i}>
              {section.title && (
                <>
                  <hr style={{ border: "none", borderTop: `1px solid ${PRINT_ACCENT}`, margin: "18px 0 8px" }} />
                  <div
                    style={{
                      fontSize: "12px",
                      fontWeight: 800,
                      textTransform: "uppercase",
                      letterSpacing: "1px",
                      color: PRINT_ACCENT,
                    }}
                  >
                    {section.title}
                  </div>
                </>
              )}
              {section.body && (
                <div style={{ marginTop: "6px", fontSize: "12.5px", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                  {section.body}
                </div>
              )}
            </div>
          );
        })}

        <hr style={{ border: "none", borderTop: `1px solid ${PRINT_ACCENT}`, margin: "20px 0 10px" }} />
        <div style={{ fontSize: "9.5px", lineHeight: 1.5, color: "#666666" }}>
          For informational and educational purposes only. Not investment advice. Data sourced from
          public APIs and may be delayed or incomplete. Generated by a multi-agent AI system.
        </div>
      </div>
    </div>
  );
}
