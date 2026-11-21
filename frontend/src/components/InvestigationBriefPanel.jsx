import { useState, useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  FileText,
  Download,
  Sparkles,
  RefreshCw,
  CheckSquare,
  Square,
  AlertCircle,
  Clock,
  ShieldAlert,
} from "lucide-react";
import {
  generateInvestigationReport,
  fetchMeterReports,
} from "../services/api";

export default function InvestigationBriefPanel({
  selectedMeterId = "M001",
  latestReportFromSimulation = null,
}) {
  const [reports, setReports] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  // Checklist state for interactive field audit (session-persisted)
  const [checkedItems, setCheckedItems] = useState({});

  // Fetch reports whenever selectedMeterId changes
  useEffect(() => {
    let isMounted = true;
    async function loadReports() {
      if (!selectedMeterId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await fetchMeterReports(selectedMeterId);
        if (isMounted) {
          const list = data.reports || [];
          setReports(list);
          if (list.length > 0) {
            setSelectedReportId(list[0].id);
          } else {
            setSelectedReportId(null);
          }
        }
      } catch (err) {
        if (isMounted) {
          console.error("Failed to fetch reports:", err);
          setError("Failed to load investigation history for this meter.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadReports();
    return () => {
      isMounted = false;
    };
  }, [selectedMeterId]);

  const displayReports = useMemo(() => {
    if (!latestReportFromSimulation || latestReportFromSimulation.meter_id !== selectedMeterId) {
      return reports;
    }
    const exists = reports.some((r) => r.id === latestReportFromSimulation.id);
    return exists ? reports : [latestReportFromSimulation, ...reports];
  }, [reports, latestReportFromSimulation, selectedMeterId]);

  const activeReport = useMemo(() => {
    if (selectedReportId) {
      const found = displayReports.find((r) => r.id === selectedReportId);
      if (found) return found;
    }
    if (latestReportFromSimulation && latestReportFromSimulation.meter_id === selectedMeterId) {
      return latestReportFromSimulation;
    }
    return displayReports[0] || null;
  }, [displayReports, selectedReportId, latestReportFromSimulation, selectedMeterId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await generateInvestigationReport(selectedMeterId);
      if (res.status === "success" && res.report) {
        setReports((prev) => [res.report, ...prev]);
        setSelectedReportId(res.report.id);
      }
    } catch (err) {
      setError(err.message || "Failed to generate investigation report.");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!activeReport || !activeReport.report_markdown) return;
    let md = activeReport.report_markdown;
    checklistItems.forEach((item, idx) => {
      const isChecked = !!checkedItems[`${activeReport.id}-${idx}`];
      if (isChecked) {
        md = md.replace(`- [ ] ${item}`, `- [x] ${item}`);
      }
    });

    const blob = new Blob([md], {
      type: "text/markdown;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute(
      "download",
      `MeterGuard-Investigation-${activeReport.meter_id}-Report-${activeReport.id}.md`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Extract checklist items from Markdown Section 4
  const extractChecklist = (report) => {
    if (!report || !report.report_markdown) return [];
    const lines = report.report_markdown.split("\n");
    const items = [];
    let inChecklist = false;

    for (const line of lines) {
      if (line.includes("### 4.") || line.toLowerCase().includes("checklist")) {
        inChecklist = true;
        continue;
      }
      if (inChecklist && line.startsWith("### ")) {
        break;
      }
      if (inChecklist && (line.trim().startsWith("- [ ]") || line.trim().startsWith("- [x]"))) {
        const text = line.replace(/- \[[ x]\]\s*/, "").trim();
        items.push(text);
      }
    }
    return items;
  };

  const checklistItems = extractChecklist(activeReport);

  const toggleCheck = (idx) => {
    const key = `${activeReport?.id}-${idx}`;
    setCheckedItems((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  return (
    <section className="panel investigation-panel" style={{ marginTop: "24px" }}>
      <div className="panel-header" style={{ flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              background: "rgba(34, 197, 94, 0.15)",
              padding: "8px",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <FileText size={22} color="var(--green)" />
          </div>
          <div>
            <h2>Forensic Investigation Brief</h2>
            <p>Evidence-grounded utility tampering analysis (Gemini 2.5 Flash / Evidence Engine)</p>
          </div>
        </div>

        {/* CONTROLS: HISTORY SELECTOR & ACTIONS */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {displayReports.length > 0 && (
            <select
              value={selectedReportId || (activeReport ? activeReport.id : "")}
              onChange={(e) => setSelectedReportId(Number(e.target.value))}
              style={{
                padding: "8px 12px",
                borderRadius: "8px",
                background: "var(--navy-light)",
                color: "#FFF",
                border: "1px solid var(--border)",
                fontSize: "0.85rem",
              }}
            >
              {displayReports.map((r) => (
                <option key={r.id} value={r.id}>
                  Report #{r.id} • {r.model_used === "gemini-2.5-flash" ? "Gemini" : "Fallback"} •{" "}
                  {r.created_at ? new Date(r.created_at).toLocaleTimeString() : "Recent"}
                </option>
              ))}
            </select>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #153E61 0%, #0A2947 100%)",
              color: "var(--cream)",
              border: "1px solid var(--border-light)",
              fontSize: "0.85rem",
              fontWeight: "600",
              cursor: generating ? "not-allowed" : "pointer",
            }}
          >
            {generating ? (
              <RefreshCw size={15} className="spin-icon" />
            ) : (
              <Sparkles size={15} color="var(--cream)" />
            )}
            {generating ? "GENERATING..." : "NEW BRIEF"}
          </button>

          {activeReport && (
            <button
              onClick={handleDownload}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 14px",
                borderRadius: "8px",
                background: "rgba(139, 94, 60, 0.25)",
                color: "var(--cream)",
                border: "1px solid var(--brown)",
                fontSize: "0.85rem",
                fontWeight: "600",
                cursor: "pointer",
              }}
              title="Download report as Markdown file"
            >
              <Download size={15} />
              DOWNLOAD .MD
            </button>
          )}
        </div>
      </div>

      {/* ERROR FEEDBACK */}
      {error && (
        <div
          style={{
            marginTop: "12px",
            padding: "10px 14px",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid var(--red)",
            borderRadius: "8px",
            color: "#FCA5A5",
            fontSize: "0.85rem",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <AlertCircle size={16} color="#EF4444" />
          <span>{error}</span>
        </div>
      )}

      {/* REPORT CONTENT */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
          <RefreshCw size={24} className="spin-icon" style={{ margin: "0 auto 10px" }} />
          <p>Retrieving stored investigation records for Meter {selectedMeterId}...</p>
        </div>
      ) : activeReport ? (
        <div style={{ marginTop: "16px" }}>
          {/* REPORT METADATA BANNER */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "10px",
              padding: "10px 16px",
              background: "rgba(6, 28, 49, 0.6)",
              borderRadius: "8px",
              border: "1px solid var(--border)",
              fontSize: "0.8rem",
              marginBottom: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <span
                style={{
                  background:
                    activeReport.model_used === "gemini-2.5-flash"
                      ? "rgba(34, 197, 94, 0.2)"
                      : "rgba(56, 189, 248, 0.15)",
                  border: `1px solid ${
                    activeReport.model_used === "gemini-2.5-flash" ? "var(--green)" : "#38BDF8"
                  }`,
                  color: activeReport.model_used === "gemini-2.5-flash" ? "#4ADE80" : "#38BDF8",
                  padding: "3px 10px",
                  borderRadius: "16px",
                  fontWeight: "700",
                  fontSize: "0.75rem",
                }}
              >
                ● {activeReport.model_used.toUpperCase()}
              </span>

              <span style={{ color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "4px" }}>
                <Clock size={13} />
                {activeReport.created_at ? new Date(activeReport.created_at).toLocaleString() : "Just now"}
              </span>

              <span style={{ color: "var(--cream)" }}>
                Meter ID: <strong>{activeReport.meter_id}</strong>
              </span>
            </div>

            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                color: "var(--text-muted)",
                fontSize: "0.75rem",
              }}
            >
              <ShieldAlert size={14} color="var(--sage)" />
              AUDIT RECORD #{activeReport.id}
            </span>
          </div>

          {/* INTERACTIVE FIELD INSPECTION CHECKLIST (FROM SECTION 4) */}
          {checklistItems.length > 0 && (
            <div
              style={{
                background: "rgba(10, 41, 71, 0.6)",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                padding: "16px",
                marginBottom: "20px",
              }}
            >
              <h3
                style={{
                  fontSize: "0.95rem",
                  color: "var(--cream)",
                  marginBottom: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <CheckSquare size={18} color="var(--green)" />
                Interactive Field Inspection Audit Checklist
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {checklistItems.map((item, idx) => {
                  const isChecked = !!checkedItems[`${activeReport.id}-${idx}`];
                  return (
                    <div
                      key={idx}
                      onClick={() => toggleCheck(idx)}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "10px",
                        padding: "8px 12px",
                        borderRadius: "6px",
                        background: isChecked ? "rgba(34, 197, 94, 0.12)" : "rgba(6, 28, 49, 0.4)",
                        border: `1px solid ${isChecked ? "var(--green)" : "rgba(211, 212, 192, 0.15)"}`,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {isChecked ? (
                        <CheckSquare size={18} color="var(--green)" style={{ flexShrink: 0, marginTop: "2px" }} />
                      ) : (
                        <Square size={18} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: "2px" }} />
                      )}
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: isChecked ? "#CBD5E1" : "var(--text-secondary)",
                          textDecoration: isChecked ? "line-through" : "none",
                          opacity: isChecked ? 0.8 : 1,
                        }}
                      >
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ _node, ...props }) => <span {...props} />,
                            strong: ({ _node, ...props }) => (
                              <strong style={{ color: isChecked ? "#94A3B8" : "#FFFFFF", fontWeight: "700" }} {...props} />
                            ),
                            code: ({ _node, ...props }) => (
                              <code
                                style={{
                                  background: "rgba(10, 41, 71, 0.7)",
                                  border: "1px solid rgba(211, 212, 192, 0.2)",
                                  padding: "1px 4px",
                                  borderRadius: "3px",
                                  color: "#4ADE80",
                                  fontSize: "0.9em",
                                  fontFamily: "monospace",
                                }}
                                {...props}
                              />
                            ),
                          }}
                        >
                          {item}
                        </ReactMarkdown>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* FORMATTED MARKDOWN REPORT VIEW */}
          <div
            className="report-markdown-view formatted-markdown"
            style={{
              background: "rgba(3, 17, 31, 0.75)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "24px",
              color: "#E2E8F0",
              fontSize: "0.92rem",
              lineHeight: "1.7",
              maxHeight: "550px",
              overflowY: "auto",
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ _node, ...props }) => (
                  <h1 style={{ color: "#FFFFFF", fontSize: "1.45rem", borderBottom: "1px solid rgba(211, 212, 192, 0.2)", paddingBottom: "8px", marginTop: "0", marginBottom: "16px" }} {...props} />
                ),
                h2: ({ _node, ...props }) => (
                  <h2 style={{ color: "var(--cream)", fontSize: "1.25rem", marginTop: "20px", marginBottom: "12px" }} {...props} />
                ),
                h3: ({ _node, ...props }) => (
                  <h3 style={{ color: "#F3E4C9", fontSize: "1.1rem", marginTop: "18px", marginBottom: "10px" }} {...props} />
                ),
                h4: ({ _node, ...props }) => (
                  <h4 style={{ color: "var(--sage)", fontSize: "0.98rem", marginTop: "14px", marginBottom: "8px" }} {...props} />
                ),
                p: ({ _node, ...props }) => <p style={{ marginBottom: "12px", color: "#CBD5E1" }} {...props} />,
                strong: ({ _node, ...props }) => <strong style={{ color: "#FFFFFF", fontWeight: "700" }} {...props} />,
                code: ({ _node, _inline, ...props }) => (
                  <code
                    style={{
                      background: "rgba(10, 41, 71, 0.7)",
                      border: "1px solid rgba(211, 212, 192, 0.2)",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      color: "#4ADE80",
                      fontSize: "0.85em",
                      fontFamily: "monospace",
                    }}
                    {...props}
                  />
                ),
                ul: ({ _node, ...props }) => <ul style={{ paddingLeft: "20px", marginBottom: "12px" }} {...props} />,
                ol: ({ _node, ...props }) => <ol style={{ paddingLeft: "20px", marginBottom: "12px" }} {...props} />,
                li: ({ _node, ...props }) => <li style={{ marginBottom: "6px", color: "#CBD5E1" }} {...props} />,
                blockquote: ({ _node, ...props }) => (
                  <blockquote
                    style={{
                      borderLeft: "4px solid #8B5E3C",
                      color: "var(--sage)",
                      fontStyle: "italic",
                      background: "rgba(139, 94, 60, 0.12)",
                      padding: "10px 14px",
                      margin: "14px 0",
                      borderRadius: "0 6px 6px 0",
                    }}
                    {...props}
                  />
                ),
                hr: ({ _node, ...props }) => (
                  <hr style={{ border: "none", borderTop: "1px solid rgba(211, 212, 192, 0.15)", margin: "20px 0" }} {...props} />
                ),
                table: ({ _node, ...props }) => (
                  <div style={{ overflowX: "auto", margin: "16px 0" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }} {...props} />
                  </div>
                ),
                th: ({ _node, ...props }) => (
                  <th style={{ borderBottom: "1px solid rgba(211, 212, 192, 0.25)", padding: "8px", textAlign: "left", color: "var(--sage)" }} {...props} />
                ),
                td: ({ _node, ...props }) => (
                  <td style={{ borderBottom: "1px solid rgba(211, 212, 192, 0.1)", padding: "8px", color: "#E2E8F0" }} {...props} />
                ),
              }}
            >
              {activeReport.report_markdown}
            </ReactMarkdown>
          </div>
        </div>
      ) : (
        /* EMPTY STATE */
        <div
          style={{
            textAlign: "center",
            padding: "40px 20px",
            background: "rgba(6, 28, 49, 0.4)",
            borderRadius: "10px",
            border: "1px dashed var(--border)",
            marginTop: "16px",
          }}
        >
          <FileText size={36} color="var(--text-muted)" style={{ margin: "0 auto 12px" }} />
          <h3 style={{ color: "var(--cream)", marginBottom: "6px" }}>No Investigation Briefs Generated Yet</h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", maxWidth: "480px", margin: "0 auto 16px" }}>
            Generate an evidence-grounded forensic investigation brief for Meter {selectedMeterId} cross-referencing
            simulated electrical telemetry, LSTM reconstruction error, and temporal decision arbitration.
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 20px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #22C55E 0%, #15803D 100%)",
              color: "#FFF",
              fontWeight: "700",
              border: "none",
              cursor: generating ? "not-allowed" : "pointer",
            }}
          >
            {generating ? <RefreshCw size={16} className="spin-icon" /> : <Sparkles size={16} />}
            {generating ? "GENERATING BRIEF..." : "GENERATE FIRST INVESTIGATION BRIEF"}
          </button>
        </div>
      )}
    </section>
  );
}
