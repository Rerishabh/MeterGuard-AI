import { useState, useEffect } from "react";
import {
  Bell,
  Clock3,
  Filter,
  Search,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Layers,
  ShieldAlert,
} from "lucide-react";
import { fetchAlerts } from "../services/api";

export default function AlertsLogsPage({
  dashboard,
  setSelectedMeter,
  lastUpdate,
}) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [meterFilter, setMeterFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const meters = dashboard?.meters || [];

  const handleManualRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAlerts();
      setAlerts(data.alerts || []);
    } catch (err) {
      console.error("Failed to load alerts:", err);
      setError("Unable to load anomaly alerts from backend. Confirm FastAPI is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const data = await fetchAlerts();
        if (isMounted) {
          setAlerts(data.alerts || []);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        console.error("Failed to load alerts:", err);
        if (isMounted) {
          setError("Unable to load anomaly alerts from backend. Confirm FastAPI is running.");
          setLoading(false);
        }
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Filter alerts
  const filteredAlerts = alerts.filter((item) => {
    const matchesSeverity =
      severityFilter === "ALL" || (item.severity || "").toUpperCase() === severityFilter;
    const matchesMeter =
      meterFilter === "ALL" || item.meter_id === meterFilter;
    const matchesSearch =
      !searchQuery ||
      (item.fault_type || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.message || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.meter_id || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.source_model || "").toLowerCase().includes(searchQuery.toLowerCase());

    return matchesSeverity && matchesMeter && matchesSearch;
  });

  const getSeverityBadgeClass = (severity) => {
    const s = (severity || "").toUpperCase();
    if (s === "CRITICAL" || s === "HIGH") return "fault";
    if (s === "MEDIUM") return "suspicious";
    return "normal";
  };

  return (
    <main className="main">
      {/* TOPBAR */}
      <header className="topbar">
        <div>
          <div className="title-row">
            <Bell size={28} color="#EF4444" />
            <h1>Anomaly Alerts & Event Logs</h1>
          </div>
          <p>Audited tamper incidents, reconstruction deviations & simulated differential alarms</p>
        </div>

        <div className="topbar-right">
          <button
            type="button"
            onClick={handleManualRefresh}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 14px",
              borderRadius: "6px",
              background: "rgba(10, 41, 71, 0.7)",
              border: "1px solid rgba(211, 212, 192, 0.25)",
              color: "var(--cream)",
              cursor: "pointer",
              fontSize: "12px",
            }}
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            Refresh
          </button>

          <div className="time-display">
            <Clock3 size={17} />
            {lastUpdate ? lastUpdate.toLocaleTimeString() : "--"}
          </div>
        </div>
      </header>

      {/* ALERT SEVERITY SUMMARY CARDS */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "20px",
        }}
      >
        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>Total Logged Alerts</span>
            <Layers size={16} color="var(--cream)" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
            {alerts.length}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Recorded in MySQL</small>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>High / Critical</span>
            <AlertTriangle size={16} color="#EF4444" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#EF4444", marginTop: "4px" }}>
            {alerts.filter((a) => ["CRITICAL", "HIGH"].includes((a.severity || "").toUpperCase())).length}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Urgent technician audit</small>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>Medium Severity</span>
            <ShieldAlert size={16} color="#F59E0B" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#F59E0B", marginTop: "4px" }}>
            {alerts.filter((a) => (a.severity || "").toUpperCase() === "MEDIUM").length}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Watchlist / Secondary</small>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>Active Incidents</span>
            <Cpu size={16} color="#4ADE80" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#4ADE80", marginTop: "4px" }}>
            {alerts.filter((a) => !a.is_resolved).length}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Unresolved queue</small>
        </div>
      </div>

      {/* FILTER & SEARCH BAR */}
      <section className="panel" style={{ padding: "14px 18px", marginBottom: "22px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "14px", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ position: "relative", flex: "1 1 260px" }}>
            <Search size={18} color="var(--sage)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
            <input
              type="text"
              placeholder="Filter by fault type, meter, or message..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "9px 12px 9px 38px",
                borderRadius: "8px",
                border: "1px solid rgba(211, 212, 192, 0.25)",
                background: "rgba(6, 28, 49, 0.8)",
                color: "#FFFFFF",
                fontSize: "13px",
                outline: "none",
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Filter size={15} color="var(--sage)" />
              <span style={{ fontSize: "12px", color: "var(--sage)" }}>Meter:</span>
              <select
                value={meterFilter}
                onChange={(e) => setMeterFilter(e.target.value)}
                style={{
                  padding: "6px 10px",
                  borderRadius: "6px",
                  background: "rgba(6, 28, 49, 0.8)",
                  border: "1px solid rgba(211, 212, 192, 0.25)",
                  color: "#FFFFFF",
                  fontSize: "12px",
                }}
              >
                <option value="ALL">All Meters</option>
                {meters.map((m) => (
                  <option key={m.meter_id} value={m.meter_id}>
                    {m.meter_id}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--sage)" }}>Severity:</span>
              {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setSeverityFilter(sev)}
                  style={{
                    padding: "5px 10px",
                    borderRadius: "6px",
                    border: severityFilter === sev ? "1px solid var(--cream)" : "1px solid rgba(211, 212, 192, 0.2)",
                    background: severityFilter === sev ? "rgba(139, 94, 60, 0.5)" : "rgba(10, 41, 71, 0.5)",
                    color: severityFilter === sev ? "#FFFFFF" : "var(--sage)",
                    fontSize: "11.5px",
                    cursor: "pointer",
                  }}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ALERTS TABLE / LIST */}
      <section className="panel" style={{ marginBottom: "24px" }}>
        <div className="panel-header">
          <div>
            <h2>Incident Activity Logs ({filteredAlerts.length})</h2>
            <p>Chronological listing of confirmed tampering alerts</p>
          </div>
          <Bell size={20} color="#22C55E" />
        </div>

        {error && (
          <div style={{ padding: "14px", background: "rgba(239, 68, 68, 0.15)", borderRadius: "8px", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#FCA5A5", fontSize: "13px", marginTop: "12px" }}>
            {error}
          </div>
        )}

        <div style={{ overflowX: "auto", marginTop: "14px" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1.5px solid rgba(211, 212, 192, 0.2)", color: "var(--sage)", textTransform: "uppercase", fontSize: "11px", letterSpacing: "0.8px" }}>
                <th style={{ padding: "10px 8px" }}>Severity</th>
                <th style={{ padding: "10px 8px" }}>Meter ID</th>
                <th style={{ padding: "10px 8px" }}>Fault Type</th>
                <th style={{ padding: "10px 8px" }}>Detection Model</th>
                <th style={{ padding: "10px 8px" }}>Message / Details</th>
                <th style={{ padding: "10px 8px" }}>Timestamp (UTC)</th>
                <th style={{ padding: "10px 8px" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.map((item) => {
                const badgeClass = getSeverityBadgeClass(item.severity);
                return (
                  <tr
                    key={item.id}
                    style={{
                      borderBottom: "1px solid rgba(211, 212, 192, 0.08)",
                      transition: "background 0.15s ease",
                      cursor: "pointer",
                    }}
                    onClick={() => {
                      if (item.meter_id) {
                        setSelectedMeter(item.meter_id);
                      }
                    }}
                    title="Click to select this meter"
                  >
                    <td style={{ padding: "12px 8px" }}>
                      <span className={`network-status ${badgeClass}`} style={{ fontSize: "11px", padding: "3px 8px", fontWeight: "700" }}>
                        {item.severity}
                      </span>
                    </td>
                    <td style={{ padding: "12px 8px", color: "#FFFFFF", fontWeight: "600" }}>
                      {item.meter_id}
                    </td>
                    <td style={{ padding: "12px 8px", color: "#F3E4C9", fontWeight: "600" }}>
                      {(item.fault_type || "ANOMALY").replace("SIMULATED_", "").replace("FAULT_", "")}
                    </td>
                    <td style={{ padding: "12px 8px", color: "var(--sage)" }}>
                      <span style={{ background: "rgba(10, 41, 71, 0.6)", padding: "2px 6px", borderRadius: "4px", fontSize: "11px" }}>
                        {item.source_model}
                      </span>
                    </td>
                    <td style={{ padding: "12px 8px", color: "var(--cream-soft)", maxWidth: "340px" }}>
                      {item.message || "Anomaly detected."}
                    </td>
                    <td style={{ padding: "12px 8px", color: "var(--sage-dark)", fontSize: "11.5px" }}>
                      {item.created_at ? new Date(item.created_at).toLocaleString() : "--"}
                    </td>
                    <td style={{ padding: "12px 8px" }}>
                      {item.is_resolved ? (
                        <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#22C55E", fontSize: "12px" }}>
                          <CheckCircle2 size={14} /> Resolved
                        </span>
                      ) : (
                        <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#EF4444", fontSize: "12px", fontWeight: "600" }}>
                          <span className="live-dot" style={{ background: "#EF4444" }}></span> Active
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}

              {!loading && filteredAlerts.length === 0 && (
                <tr>
                  <td colSpan="7" style={{ padding: "40px", textAlign: "center", color: "var(--sage)" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
                      <CheckCircle2 size={36} color="#22C55E" />
                      <strong style={{ color: "#FFFFFF", fontSize: "15px" }}>No Anomaly Alerts Found</strong>
                      <p style={{ margin: 0, fontSize: "12.5px" }}>
                        {alerts.length === 0
                          ? "No historical tampering incidents logged in database yet. All monitored meters normal."
                          : "No alerts match the active severity or meter filters."}
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <span>MeterGuard AI • Forensic Anomaly Audit Trail</span>
        <span>MySQL Anomaly Alerts • Deduplicated Event History</span>
      </footer>
    </main>
  );
}
