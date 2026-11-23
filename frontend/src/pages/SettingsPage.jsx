import { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Server,
  Database,
  Cpu,
  Clock3,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Monitor,
  Bell,
  Shield,
  Layers,
  Activity,
} from "lucide-react";
import { fetchHealth, API_BASE_URL } from "../services/api";

export default function SettingsPage({
  lastUpdate,
  pollingInterval,
  setPollingInterval,
}) {
  const runtimeMode = import.meta.env.MODE;
  const environmentLabel =
    runtimeMode === "development"
      ? "Development (Vite Dev Server)"
      : runtimeMode === "production"
      ? "Production"
      : runtimeMode
      ? runtimeMode.charAt(0).toUpperCase() + runtimeMode.slice(1)
      : "Standard";

  const [health, setHealth] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [healthError, setHealthError] = useState(null);

  // User preferences stored in localStorage
  const [compactView, setCompactView] = useState(() => {
    return localStorage.getItem("meterguard_compact") === "true";
  });
  const [soundAlerts, setSoundAlerts] = useState(() => {
    return localStorage.getItem("meterguard_sound") === "true";
  });
  const [selectedInterval, setSelectedInterval] = useState(() => {
    return Number(localStorage.getItem("meterguard_interval")) || pollingInterval || 1000;
  });

  const checkServerHealth = async () => {
    setLoadingHealth(true);
    setHealthError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err) {
      console.error("Health check failed:", err);
      setHealthError("Failed to reach backend health endpoint.");
      setHealth(null);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetchHealth()
      .then((data) => {
        if (isMounted) {
          setHealth(data);
          setLoadingHealth(false);
        }
      })
      .catch((err) => {
        console.error("Health check failed:", err);
        if (isMounted) {
          setHealthError("Failed to reach backend health endpoint.");
          setHealth(null);
          setLoadingHealth(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleIntervalChange = (val) => {
    const num = Number(val);
    setSelectedInterval(num);
    localStorage.setItem("meterguard_interval", num.toString());
    if (setPollingInterval) {
      setPollingInterval(num);
    }
  };

  const handleCompactToggle = () => {
    const next = !compactView;
    setCompactView(next);
    localStorage.setItem("meterguard_compact", next.toString());
  };

  const handleSoundToggle = () => {
    const next = !soundAlerts;
    setSoundAlerts(next);
    localStorage.setItem("meterguard_sound", next.toString());
  };

  return (
    <div className="settings-container">
      {/* SECTION SUBHEADER */}
      <header className="settings-section-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <SettingsIcon size={24} color="#22C55E" />
            <h1>System Configuration & Diagnostics</h1>
          </div>
          <p>Application parameters, backend microservices health & operational preferences</p>
        </div>

        <div className="time-display" style={{ alignSelf: "center" }}>
          <Clock3 size={16} />
          <span>{lastUpdate ? lastUpdate.toLocaleTimeString() : "--"}</span>
        </div>
      </header>

      {/* TWO-COLUMN: BACKEND STATUS & APPLICATION INFO */}
      <div className="settings-two-column">
        {/* BACKEND CONNECTIVITY PANEL */}
        <section className="settings-panel">
          <div className="panel-header" style={{ marginBottom: "14px" }}>
            <div>
              <h2 style={{ fontSize: "1.05rem", margin: 0 }}>Backend Health & Infrastructure</h2>
              <p style={{ fontSize: "0.78rem", margin: "2px 0 0" }}>Active FastAPI & MySQL microservices</p>
            </div>
            <button
              type="button"
              onClick={checkServerHealth}
              disabled={loadingHealth}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "6px",
                background: "rgba(10, 41, 71, 0.7)",
                border: "1px solid rgba(211, 212, 192, 0.25)",
                color: "var(--cream)",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              <RefreshCw size={13} className={loadingHealth ? "spin" : ""} />
              Ping
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", flexWrap: "wrap", gap: "8px", minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--cream)" }}>
                <Server size={16} color="#22C55E" />
                API Server Host
              </span>
              <strong style={{ color: "#FFFFFF", fontSize: "12.5px", wordBreak: "break-all" }}>{API_BASE_URL}</strong>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", flexWrap: "wrap", gap: "8px", minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--cream)" }}>
                <Database size={16} color="#4ADE80" />
                MySQL Persistence
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
                {health?.database_connected ? (
                  <>
                    <CheckCircle2 size={15} color="#22C55E" />
                    <span style={{ color: "#22C55E", fontWeight: "600" }}>Connected (meterguard_db)</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={15} color="#EF4444" />
                    <span style={{ color: "#EF4444", fontWeight: "600" }}>Disconnected</span>
                  </>
                )}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", flexWrap: "wrap", gap: "8px", minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--cream)" }}>
                <Cpu size={16} color="#F3E4C9" />
                ML Models 1 & 2
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
                {health?.model1_loaded && health?.model2_loaded ? (
                  <>
                    <CheckCircle2 size={15} color="#22C55E" />
                    <span style={{ color: "#22C55E", fontWeight: "600" }}>Models 1 & 2 Loaded</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={15} color="#EF4444" />
                    <span style={{ color: "#EF4444" }}>Pending</span>
                  </>
                )}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", flexWrap: "wrap", gap: "8px", minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--cream)" }}>
                <Layers size={16} color="#22C55E" />
                Model 3 LSTM Autoencoders
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
                {health?.lstm_daily_available && health?.lstm_hourly_available ? (
                  <>
                    <CheckCircle2 size={15} color="#22C55E" />
                    <span style={{ color: "#22C55E", fontWeight: "600" }}>Daily (30d) & Hourly (24h) Active</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={15} color="#EF4444" />
                    <span style={{ color: "#EF4444" }}>Unavailable</span>
                  </>
                )}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", flexWrap: "wrap", gap: "8px", minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--cream)" }}>
                <Activity size={16} color="#38BDF8" />
                Dataset Simulation Replay
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
                {health?.simulation_status === "SIMULATED" ? (
                  <>
                    <span className="live-dot" style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: "#22C55E" }}></span>
                    <span style={{ color: "#22C55E", fontWeight: "600" }}>SIMULATED (Auto-Streaming)</span>
                  </>
                ) : health?.simulation_status === "INITIALIZING" ? (
                  <>
                    <span style={{ background: "#38BDF8", width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" }}></span>
                    <span style={{ color: "#38BDF8", fontWeight: "600" }}>INITIALIZING</span>
                  </>
                ) : (
                  <>
                    <span style={{ background: "#F59E0B", width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" }}></span>
                    <span style={{ color: "#FCD34D", fontWeight: "600" }}>{health?.simulation_status || "SIMULATION PAUSED"}</span>
                  </>
                )}
              </span>
            </div>
          </div>

          {healthError && (
            <div style={{ marginTop: "12px", padding: "10px", background: "rgba(239, 68, 68, 0.15)", borderRadius: "6px", color: "#FCA5A5", fontSize: "12px" }}>
              {healthError}
            </div>
          )}
        </section>

        {/* APPLICATION INFORMATION PANEL */}
        <section className="settings-panel">
          <div className="panel-header" style={{ marginBottom: "14px" }}>
            <div>
              <h2 style={{ fontSize: "1.05rem", margin: 0 }}>Application Metadata</h2>
              <p style={{ fontSize: "0.78rem", margin: "2px 0 0" }}>Platform specifications & controls</p>
            </div>
            <Shield size={22} color="#22C55E" />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ padding: "12px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", minWidth: 0 }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "0.5px" }}>System Name</span>
              <div style={{ color: "#FFFFFF", fontWeight: "600", fontSize: "13.5px", marginTop: "2px" }}>
                MeterGuard AI: Utility Meter Tampering Detector
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px" }}>
              <div style={{ padding: "12px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", minWidth: 0 }}>
                <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Frontend</span>
                <div style={{ color: "#22C55E", fontWeight: "700", fontSize: "13px", marginTop: "2px" }}>
                  {environmentLabel}
                </div>
              </div>

              <div style={{ padding: "12px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", minWidth: 0 }}>
                <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Backend</span>
                <div style={{ color: "#4ADE80", fontWeight: "700", fontSize: "13px", marginTop: "2px" }}>
                  FastAPI (Uvicorn 0.30+)
                </div>
              </div>
            </div>

            <div style={{ padding: "12px 14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", minWidth: 0 }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Security Boundary</span>
              <div style={{ color: "var(--cream)", fontSize: "12px", marginTop: "4px", lineHeight: "1.4" }}>
                Credentials and API keys are isolated server-side inside root <code>.env</code>. Never exposed over client endpoints.
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* OPERATIONAL & DISPLAY PREFERENCES */}
      <section className="settings-panel" style={{ marginBottom: "20px" }}>
        <div className="panel-header" style={{ marginBottom: "12px" }}>
          <div>
            <h2 style={{ fontSize: "1.05rem", margin: 0 }}>Dashboard Display & Polling Preferences</h2>
            <p style={{ fontSize: "0.78rem", margin: "2px 0 0" }}>Customize telemetry refresh rates and interface preferences</p>
          </div>
          <Monitor size={22} color="#22C55E" />
        </div>

        <div className="settings-preferences-grid">
          {/* POLLING INTERVAL CONTROL */}
          <div style={{ padding: "14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)", minWidth: 0 }}>
            <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "0.8px" }}>
              Telemetry Polling Frequency
            </span>
            <div style={{ fontSize: "12.5px", color: "var(--cream-soft)", margin: "4px 0 10px" }}>
              Background dashboard refresh interval:
            </div>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {[
                { label: "1.0s (Fast)", val: 1000 },
                { label: "2.0s (Balanced)", val: 2000 },
                { label: "5.0s (Low Power)", val: 5000 },
              ].map((opt) => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => handleIntervalChange(opt.val)}
                  style={{
                    flex: "1 1 75px",
                    padding: "7px 6px",
                    borderRadius: "6px",
                    border: selectedInterval === opt.val ? "1px solid #22C55E" : "1px solid rgba(211, 212, 192, 0.2)",
                    background: selectedInterval === opt.val ? "rgba(34, 197, 94, 0.25)" : "rgba(10, 41, 71, 0.5)",
                    color: selectedInterval === opt.val ? "#FFFFFF" : "var(--sage)",
                    fontSize: "11px",
                    fontWeight: selectedInterval === opt.val ? "700" : "500",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* COMPACT VIEW TOGGLE */}
          <div style={{ padding: "14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px", minWidth: 0 }}>
            <div style={{ minWidth: 0 }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "0.8px" }}>
                Compact Card Density
              </span>
              <div style={{ fontSize: "12px", color: "var(--cream-soft)", marginTop: "3px" }}>
                Reduce spacing on telemetry panels
              </div>
            </div>

            <button
              type="button"
              onClick={handleCompactToggle}
              style={{
                width: "44px",
                height: "24px",
                borderRadius: "12px",
                background: compactView ? "#22C55E" : "rgba(10, 41, 71, 0.9)",
                border: "1px solid rgba(211, 212, 192, 0.3)",
                position: "relative",
                cursor: "pointer",
                transition: "background 0.2s ease",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  width: "16px",
                  height: "16px",
                  borderRadius: "50%",
                  background: "#FFFFFF",
                  position: "absolute",
                  top: "3px",
                  left: compactView ? "23px" : "4px",
                  transition: "left 0.2s ease",
                }}
              />
            </button>
          </div>

          {/* AUDIO ALERTS TOGGLE */}
          <div style={{ padding: "14px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px", minWidth: 0 }}>
            <div style={{ minWidth: 0 }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "0.8px", display: "flex", alignItems: "center", gap: "6px" }}>
                <Bell size={13} color="#22C55E" /> Audio Chime on Alert
              </span>
              <div style={{ fontSize: "12px", color: "var(--cream-soft)", marginTop: "3px" }}>
                Auditory notification on tampering breach
              </div>
            </div>

            <button
              type="button"
              onClick={handleSoundToggle}
              style={{
                width: "44px",
                height: "24px",
                borderRadius: "12px",
                background: soundAlerts ? "#22C55E" : "rgba(10, 41, 71, 0.9)",
                border: "1px solid rgba(211, 212, 192, 0.3)",
                position: "relative",
                cursor: "pointer",
                transition: "background 0.2s ease",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  width: "16px",
                  height: "16px",
                  borderRadius: "50%",
                  background: "#FFFFFF",
                  position: "absolute",
                  top: "3px",
                  left: soundAlerts ? "23px" : "4px",
                  transition: "left 0.2s ease",
                }}
              />
            </button>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{
        display: "flex",
        flexDirection: "column",
        gap: "4px",
        fontSize: "11px",
        color: "var(--sage)",
        marginTop: "20px",
        paddingTop: "14px",
        borderTop: "1px solid rgba(211, 212, 192, 0.12)",
        textAlign: "center",
      }}>
        <span>MeterGuard AI • Enterprise Settings</span>
        <span>Runtime Mode: {environmentLabel} • Architecture: Microservice REST</span>
      </footer>
    </div>
  );
}
