import { useState, useEffect, useMemo } from "react";
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
    const blob = new Blob([activeReport.report_markdown], {
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
  const checklistItems = useMemo(() => {
    if (!activeReport || !activeReport.report_markdown) return [];
    const lines = activeReport.report_markdown.split("\n");
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
  }, [activeReport]);

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
                          color: isChecked ? "#E2E8F0" : "var(--text-secondary)",
                          textDecoration: isChecked ? "line-through" : "none",
                          opacity: isChecked ? 0.8 : 1,
                        }}
                      >
                        {item}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* MARKDOWN REPORT PREVIEW */}
          <div
            className="report-markdown-view"
            style={{
              background: "rgba(3, 17, 31, 0.7)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "20px",
              color: "#E2E8F0",
              fontSize: "0.9rem",
              lineHeight: "1.6",
              maxHeight: "500px",
              overflowY: "auto",
              fontFamily: "var(--font-mono, monospace)",
              whiteSpace: "pre-wrap",
            }}
          >
            {activeReport.report_markdown}
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
            live sensor telemetry, LSTM reconstruction error, and temporal decision arbitration.
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
