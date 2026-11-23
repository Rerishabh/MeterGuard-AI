import { useState } from "react";
import {
  Clock3,
  Wifi,
  WifiOff,
  Cpu,
  Radio,
  Network,
  Activity,
  AlertTriangle,
  ShieldAlert,
  ClipboardList,
} from "lucide-react";

import MeterLogo from "../components/MeterLogo";
import MeterSummaryCard from "../components/MeterSummaryCard";
import NetworkDifferentialCard from "../components/NetworkDifferentialCard";
import TamperingSimulatorCard from "../components/TamperingSimulatorCard";
import InvestigationBriefPanel from "../components/InvestigationBriefPanel";
import LiveElectricalChart from "../charts/LiveElectricalChart";
import LoadProfileChart from "../charts/LoadProfileChart";
import { getStatusType, getStatusText } from "../services/statusHelpers";

const backgroundImage = "/tower-background.webp";

/* -------------------------------------------------------
   ACCOUNT CATEGORY & BADGE HELPERS
------------------------------------------------------- */
function getAccountCategory(meterId) {
  if (meterId === "M001" || meterId === "M002") {
    return {
      type: "DEMO",
      label: "DEMO",
      fullLabel: "Primary Demonstration Account",
      badgeColor: "#4ADE80",
      badgeBg: "rgba(34, 197, 94, 0.15)",
      badgeBorder: "rgba(34, 197, 94, 0.35)",
    };
  }
  if (meterId && meterId.startsWith("M_TEST")) {
    return {
      type: "TEST",
      label: "TEST",
      fullLabel: "Synthetic Test Benchmark",
      badgeColor: "#93C5FD",
      badgeBg: "rgba(59, 130, 246, 0.15)",
      badgeBorder: "rgba(59, 130, 246, 0.35)",
    };
  }
  if (meterId && meterId.startsWith("M_SIM")) {
    return {
      type: "SYNTH",
      label: "SYNTH",
      fullLabel: "Scenario Simulation Profile",
      badgeColor: "#C084FC",
      badgeBg: "rgba(168, 85, 247, 0.15)",
      badgeBorder: "rgba(168, 85, 247, 0.35)",
    };
  }
  return {
    type: "ACCOUNT",
    label: "ACCOUNT",
    fullLabel: "Registered Account",
    badgeColor: "#CBD5E1",
    badgeBg: "rgba(148, 163, 184, 0.15)",
    badgeBorder: "rgba(148, 163, 184, 0.35)",
  };
}

/* -------------------------------------------------------
   PRIORITY QUEUE — Account Investigation Priority Table
------------------------------------------------------- */
function PriorityBadge({ priority }) {
  const map = {
    HIGH: { bg: "rgba(239,68,68,0.18)", color: "#FCA5A5", border: "rgba(239,68,68,0.45)" },
    MEDIUM: { bg: "rgba(245,158,11,0.18)", color: "#FCD34D", border: "rgba(245,158,11,0.45)" },
    LOW: { bg: "rgba(34,197,94,0.14)", color: "#4ADE80", border: "rgba(34,197,94,0.35)" },
  };
  const s = map[priority] || map.LOW;
  return (
    <span style={{
      background: s.bg,
      color: s.color,
      border: `1px solid ${s.border}`,
      borderRadius: "5px",
      padding: "2px 8px",
      fontSize: "0.72rem",
      fontWeight: 700,
      letterSpacing: "0.6px",
    }}>
      {priority || "LOW"}
    </span>
  );
}

function StatusBadge({ status }) {
  const map = {
    "NORMAL": { bg: "rgba(34,197,94,0.15)", color: "#4ADE80", border: "rgba(34,197,94,0.35)" },
    "FAULT DETECTED": { bg: "rgba(239,68,68,0.18)", color: "#FCA5A5", border: "rgba(239,68,68,0.45)" },
    "SUSPICIOUS": { bg: "rgba(139,94,60,0.22)", color: "#D4A96A", border: "rgba(139,94,60,0.5)" },
    "MONITORING": { bg: "rgba(59,130,246,0.16)", color: "#93C5FD", border: "rgba(59,130,246,0.4)" },
  };
  const s = map[status] || { bg: "rgba(148,163,184,0.15)", color: "#CBD5E1", border: "rgba(148,163,184,0.3)" };
  return (
    <span style={{
      background: s.bg,
      color: s.color,
      border: `1px solid ${s.border}`,
      borderRadius: "5px",
      padding: "2px 9px",
      fontSize: "0.72rem",
      fontWeight: 700,
      letterSpacing: "0.5px",
      whiteSpace: "nowrap",
    }}>
      {status || "MONITORING"}
    </span>
  );
}

function LstmBadge({ status }) {
  if (!status || status === "WAITING" || status === "INSUFFICIENT DATA") {
    return (
      <span style={{ color: "var(--sage)", fontSize: "0.7rem", fontStyle: "italic" }}>
        INSUFFICIENT DATA
      </span>
    );
  }
  const map = {
    NORMAL: { color: "#4ADE80" },
    SUSPICIOUS: { color: "#FCD34D" },
    ANOMALY: { color: "#FCA5A5" },
  };
  const s = map[status] || { color: "#CBD5E1" };
  return (
    <span style={{ color: s.color, fontSize: "0.72rem", fontWeight: 700 }}>
      {status}
    </span>
  );
}

function AccountInvestigationQueue({ meters, selectedMeter, onSelectMeter }) {
  // Sort: HIGH first, then MEDIUM, then LOW; within same priority: FAULT DETECTED > SUSPICIOUS > MONITORING > NORMAL
  const statusOrder = { "FAULT DETECTED": 0, "SUSPICIOUS": 1, "MONITORING": 2, "NORMAL": 3 };
  const priorityOrder = { HIGH: 0, MEDIUM: 1, LOW: 2 };

  const sorted = [...meters].sort((a, b) => {
    const pa = priorityOrder[a?.decision?.priority || "LOW"] ?? 2;
    const pb = priorityOrder[b?.decision?.priority || "LOW"] ?? 2;
    if (pa !== pb) return pa - pb;
    const sa = statusOrder[a?.decision?.final_status || "MONITORING"] ?? 3;
    const sb = statusOrder[b?.decision?.final_status || "MONITORING"] ?? 3;
    return sa - sb;
  });

  return (
    <section className="panel" style={{ marginBottom: "1.5rem" }}>
      <div className="panel-header">
        <div>
          <h2>Account Investigation Priority Queue</h2>
          <p>Real-time ranked anomaly accounts — highest risk first</p>
        </div>
        <ClipboardList size={23} />
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.8rem",
          tableLayout: "auto",
        }}>
          <thead>
            <tr style={{
              borderBottom: "1px solid rgba(211,212,192,0.18)",
              color: "var(--sage)",
              textTransform: "uppercase",
              fontSize: "0.68rem",
              letterSpacing: "0.8px",
            }}>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Meter ID</th>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Status</th>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Priority</th>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Fault Type</th>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Daily LSTM</th>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Hourly LSTM</th>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Last Seen</th>
              <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Investigation</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => {
              const isSelected = item.meter_id === selectedMeter;
              const cat = getAccountCategory(item.meter_id);
              const finalStatus = item?.decision?.final_status || "MONITORING";
              const priority = item?.decision?.priority || "LOW";
              const faultType = item?.decision?.fault_type || item?.model2?.fault_type;
              const lstmStatus = item?.lstm?.status;
              const dailyLstm = item?.lstm?.daily_status || lstmStatus;
              const hourlyLstm = item?.lstm?.hourly_status;
              const lastSeen = item?.last_seen
                ? new Date(item.last_seen).toLocaleTimeString()
                : "—";
              const investigationStatus =
                finalStatus === "FAULT DETECTED"
                  ? "⚠ INVESTIGATE"
                  : finalStatus === "SUSPICIOUS"
                  ? "⚑ MONITOR"
                  : "✓ CLEAR";
              const investigationColor =
                finalStatus === "FAULT DETECTED"
                  ? "#FCA5A5"
                  : finalStatus === "SUSPICIOUS"
                  ? "#FCD34D"
                  : "#4ADE80";

              return (
                <tr
                  key={item.meter_id}
                  onClick={() => onSelectMeter(item.meter_id)}
                  style={{
                    borderBottom: "1px solid rgba(211,212,192,0.07)",
                    background: isSelected
                      ? "rgba(139,94,60,0.18)"
                      : cat.type === "DEMO"
                      ? "rgba(34,197,94,0.04)"
                      : "transparent",
                    cursor: "pointer",
                    transition: "background 0.15s",
                    outline: isSelected ? "1px solid rgba(139,94,60,0.4)" : "none",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "rgba(211,212,192,0.05)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = cat.type === "DEMO" ? "rgba(34,197,94,0.04)" : "transparent";
                  }}
                >
                  <td style={{ padding: "9px 12px" }}>
                    <span style={{
                      fontWeight: 700,
                      color: cat.type === "DEMO" ? "#4ADE80" : "var(--cream)",
                      fontSize: "0.82rem",
                    }}>
                      {item.meter_id}
                      <span style={{
                        marginLeft: "6px",
                        fontSize: "0.6rem",
                        background: cat.badgeBg,
                        color: cat.badgeColor,
                        border: `1px solid ${cat.badgeBorder}`,
                        borderRadius: "3px",
                        padding: "1px 5px",
                        letterSpacing: "0.5px",
                        fontWeight: 700,
                      }} title={cat.fullLabel}>
                        {cat.label}
                      </span>
                    </span>
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <StatusBadge status={finalStatus} />
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <PriorityBadge priority={priority} />
                  </td>
                  <td style={{ padding: "9px 12px", color: "var(--sage)", fontSize: "0.75rem" }}>
                    {faultType ? faultType.replace("FAULT_", "") : <span style={{ fontStyle: "italic", opacity: 0.6 }}>None</span>}
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <LstmBadge status={dailyLstm} />
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <LstmBadge status={hourlyLstm} />
                  </td>
                  <td style={{ padding: "9px 12px", color: "var(--sage)", fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                    {lastSeen}
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <span style={{ color: investigationColor, fontWeight: 700, fontSize: "0.72rem" }}>
                      {investigationStatus}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* -------------------------------------------------------
   METER NETWORK SUMMARY (merged from MeterNetworkPage)
------------------------------------------------------- */
function MeterNetworkSummary({ meters }) {
  const total = meters.length;
  const simulated = meters.filter((m) => m.connection_state === "SIMULATED" || m.online).length;
  const suspicious = meters.filter((m) => {
    const s = m?.decision?.final_status || "";
    return s === "SUSPICIOUS";
  }).length;
  const faults = meters.filter((m) => {
    const s = m?.decision?.final_status || "";
    return s === "FAULT DETECTED";
  }).length;

  const cards = [
    { label: "Registered Accounts", value: total, icon: Network, color: "#93C5FD" },
    { label: "Active Streams", value: simulated, icon: Activity, color: "#4ADE80" },
    { label: "Suspicious Flagged", value: suspicious, icon: AlertTriangle, color: "#FCD34D" },
    { label: "Tampering / Fault", value: faults, icon: ShieldAlert, color: "#FCA5A5" },
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
      gap: "12px",
      marginBottom: "1.5rem",
    }}>
      {cards.map(({ label, value, icon: Icon, color }) => (
        <div
          key={label}
          style={{
            background: "rgba(10,41,71,0.6)",
            border: "1px solid rgba(211,212,192,0.13)",
            borderRadius: "10px",
            padding: "14px 16px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <div style={{
            background: `${color}18`,
            border: `1px solid ${color}40`,
            borderRadius: "8px",
            padding: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>
            <Icon size={18} color={color} />
          </div>
          <div>
            <div style={{ fontSize: "1.5rem", fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
            <div style={{ fontSize: "0.68rem", color: "var(--sage)", marginTop: "3px", textTransform: "uppercase", letterSpacing: "0.6px" }}>{label}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------------
   MAIN DASHBOARD PAGE
------------------------------------------------------- */
export default function DashboardPage({
  dashboard,
  selectedMeter,
  setSelectedMeter,
  lastUpdate,
  error,
}) {
  const [latestSimReport, setLatestSimReport] = useState(null);

  /* =======================================================
     LOADING SCREEN (NO BACKEND CONNECTION YET)
  ======================================================= */
  if (!dashboard) {
    return (
      <div
        className="loading-screen"
        style={{
          backgroundImage: `linear-gradient(
            rgba(10,41,71,.76),
            rgba(6,28,49,.96)
          ), url(${backgroundImage})`,
        }}
      >
        <div className="loading-card">
          <div className="loading-spinner">
            <Activity size={32} />
          </div>

          <h2>MeterGuard AI</h2>
          <p>Connecting to tampering detection backend...</p>

          {error && <div className="error-box">{error}</div>}
        </div>
      </div>
    );
  }

  /* =======================================================
     WAITING FOR TELEMETRY
  ======================================================= */
  const meters = dashboard.meters || [];

  if (meters.length === 0) {
    return (
      <div className="loading-screen">
        <div className="loading-card">
          <Radio size={42} />

          <h2>Waiting for Meter Telemetry</h2>
          <p>No meter readings received yet.</p>
          <small style={{ color: "var(--sage)", marginTop: "12px", display: "block" }}>
            Run the dataset replay simulator: <code>python backend/replay_hardware_dataset.py --loop</code>
          </small>
        </div>
      </div>
    );
  }

  /* =======================================================
     RESOLVE SELECTED METER DATA
  ======================================================= */
  let meter = meters.find((item) => item.meter_id === selectedMeter);
  if (!meter) {
    meter = meters[0];
  }

  const readings = meter.readings || {};
  const electrical = meter.electrical || {};
  const model1 = meter.model1 || {};
  const model2 = meter.model2 || {};
  const lstm = meter.lstm || {};
  const decision = meter.decision || {};
  const liveHistory = meter.live_history || [];

  const voltage = Number(electrical.voltage_V || 0);
  const current = Number(electrical.current_A || 0);
  const power = Number(electrical.power_W || 0);

  const model1Prediction = model1.prediction || "WAITING";
  const model2Prediction = model2.prediction || "WAITING";
  const lstmStatus = lstm.status || "WAITING";
  const lstmError =
    lstm.reconstruction_error !== null && lstm.reconstruction_error !== undefined
      ? Number(lstm.reconstruction_error).toFixed(5)
      : null;
  const lstmThreshold =
    lstm.threshold !== null && lstm.threshold !== undefined
      ? Number(lstm.threshold).toFixed(5)
      : null;
  const finalStatus = decision.final_status || "MONITORING";
  const priority = decision.priority || "LOW";
  const faultType = decision.fault_type || model2.fault_type || null;
  const statusType = getStatusType(meter);

  const liveChartData = liveHistory.map((item, index) => ({
    reading: index + 1,
    power: Number(item.power_W || 0),
    current: Number(item.current_A || 0),
    voltage: Number(item.voltage_V || 0),
  }));

  const consumptionHistory = model1.consumption_history || meter.consumption_history || [];
  const consumptionData = consumptionHistory.map((value, index) => ({
    day: `D${index + 1}`,
    consumption: Number(value),
  }));

  const globalSimStatus = dashboard?.simulation?.status;
  const connectionState = meter.connection_state || (meter.online ? "SIMULATED" : (meter.last_seen ? "SIMULATION PAUSED" : "AWAITING SIMULATION DATA"));
  const isSimulated = connectionState === "SIMULATED";
  const isPaused = connectionState === "SIMULATION PAUSED";

  return (
    <main className="main">
      {/* TOPBAR */}
      <header className="topbar">
        <div>
          <div className="title-row">
            <MeterLogo size={32} />
            <h1>MeterGuard AI Dashboard</h1>
          </div>
          <p>Real-time intelligent utility meter tampering detection</p>
        </div>

          <div className="topbar-right">
            {globalSimStatus === "SIMULATED" || isSimulated ? (
              <div className="live-badge">
                <span className="live-dot"></span>
                SIMULATED STREAM
              </div>
            ) : globalSimStatus === "INITIALIZING" ? (
              <div
                className="live-badge"
                style={{
                  background: "rgba(59, 130, 246, 0.2)",
                  border: "1px solid #3B82F6",
                  color: "#93C5FD",
                }}
              >
                <span style={{ background: "#3B82F6", width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" }}></span>
                INITIALIZING
              </div>
            ) : isPaused || globalSimStatus === "SIMULATION PAUSED" ? (
              <div
                className="live-badge"
                style={{
                  background: "rgba(245, 158, 11, 0.2)",
                  border: "1px solid #F59E0B",
                  color: "#FCD34D",
                }}
              >
                <span style={{ background: "#F59E0B", width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" }}></span>
                SIMULATION PAUSED
              </div>
            ) : (
              <div
                className="live-badge"
                style={{
                  background: "rgba(148, 163, 184, 0.2)",
                  border: "1px solid #94A3B8",
                  color: "#CBD5E1",
                }}
              >
                <span style={{ background: "#94A3B8", width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" }}></span>
                SIMULATION MODE
              </div>
            )}

            <div className="time-display">
              <Clock3 size={17} />
              {lastUpdate ? lastUpdate.toLocaleTimeString() : "--"}
            </div>
          </div>
        </header>

        {/* METER TOOLBAR */}
        <section className="meter-toolbar">
          <div className="meter-selector">
            <span>SELECT ACCOUNT</span>
            <select
              value={meter.meter_id}
              onChange={(e) => setSelectedMeter(e.target.value)}
            >
              {meters.map((item) => {
                const cat = getAccountCategory(item.meter_id);
                let desc = `${item.meter_id} [${cat.label}]`;
                if (item.meter_id === "M001") desc = "M001 [DEMO] • Hardware Replay Stream";
                else if (item.meter_id === "M002") desc = "M002 [DEMO] • Historical Tampering Record";
                else if (item.meter_id === "M_TEST_01") desc = "M_TEST_01 [TEST] • Normal Baseline";
                else if (item.meter_id === "M_TEST_02") desc = "M_TEST_02 [TEST] • Simulated Anomaly";
                else if (item.meter_id === "M_TEST_03") desc = "M_TEST_03 [TEST] • Sparse Telemetry";
                else if (item.meter_id === "M_SIM_01") desc = "M_SIM_01 [SYNTH] • Consumption Spike";
                else if (item.meter_id === "M_SIM_02") desc = "M_SIM_02 [SYNTH] • Normal Profile";
                else if (item.meter_id === "M_SIM_FALLBACK") desc = "M_SIM_FALLBACK [SYNTH] • Sudden Drop";

                return (
                  <option key={item.meter_id} value={item.meter_id}>
                    {desc}
                  </option>
                );
              })}
            </select>
          </div>

          <div className="connection-status">
            {isSimulated ? (
              <>
                <Wifi size={18} color="#22C55E" />
                Account {meter.meter_id}
                <span className="live-dot"></span>
                <span style={{ color: "#4ADE80", fontWeight: "600" }}>SIMULATED STREAM</span>
              </>
            ) : isPaused ? (
              <>
                <Wifi size={18} color="#F59E0B" />
                Account {meter.meter_id}
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#F59E0B", display: "inline-block" }}></span>
                <span style={{ color: "#FCD34D", fontWeight: "600" }}>SIMULATION PAUSED / IDLE</span>
              </>
            ) : (
              <>
                <WifiOff size={18} color="#94A3B8" />
                Account {meter.meter_id}
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#94A3B8", display: "inline-block" }}></span>
                <span style={{ color: "#CBD5E1", fontWeight: "600" }}>AWAITING SIMULATION DATA</span>
              </>
            )}
          </div>
        </section>

        {/* NETWORK SUMMARY METRICS (merged from MeterNetworkPage) */}
        <MeterNetworkSummary meters={meters} />

        {/* ELECTRICAL & STATUS METRICS */}
        <MeterSummaryCard
          voltage={voltage}
          current={current}
          power={power}
          statusType={statusType}
          finalStatus={finalStatus}
          priority={priority}
          faultType={faultType}
        />

        {/* TWO-COLUMN: LIVE READINGS + AI DETECTION */}
        <section className="two-column">
          <LiveElectricalChart
            voltage={voltage}
            current={current}
            power={power}
            liveChartData={liveChartData}
          />

          {/* AI DETECTION PANEL */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>AI Detection</h2>
                <p>Multi-model intelligent analysis</p>
              </div>
              <Cpu size={23} />
            </div>

            <div className="ai-results">
              {/* MODEL 1 */}
              <div className="ai-row">
                <div className="ai-name">
                  <div className="ai-number">01</div>
                  <div>
                    <strong>Consumption Model</strong>
                    <small>Isolation Forest baseline</small>
                  </div>
                </div>

                <span className={`prediction ${model1Prediction.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                  {model1Prediction}
                </span>
              </div>

              {/* MODEL 2 */}
              <div className="ai-row">
                <div className="ai-name">
                  <div className="ai-number">02</div>
                  <div>
                    <strong>Fault Detection Model</strong>
                    <small>Real-time transformer differential</small>
                  </div>
                </div>

                <span className={`prediction ${model2Prediction.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                  {model2Prediction}
                </span>
              </div>

              {/* MODEL 3 */}
              <div className="ai-row">
                <div className="ai-name">
                  <div className="ai-number">03</div>
                  <div>
                    <strong>LSTM Autoencoder</strong>
                    <small>
                      {lstmError !== null && lstmThreshold !== null
                        ? `MSE: ${lstmError} | Thresh: ${lstmThreshold}`
                        : "Time-series sequence reconstruction"}
                    </small>
                  </div>
                </div>

                <span
                  className={`prediction ${
                    lstmStatus === "NORMAL"
                      ? "normal"
                      : lstmStatus === "SUSPICIOUS"
                      ? "suspicious"
                      : "waiting"
                  }`}
                  title={lstm.message || lstmStatus}
                >
                  {lstmStatus}
                </span>
              </div>


              {/* FAULT DETAILS (IF ACTIVE) */}
              {faultType && (
                <div className="fault-details">
                  <div>
                    <span>DETECTED FAULT</span>
                    <strong>{faultType.replace("FAULT_", "")}</strong>
                  </div>
                  <div>
                    <span>DETECTED BY</span>
                    <strong>MODEL 2</strong>
                  </div>
                  <div>
                    <span>PRIORITY</span>
                    <strong>{priority}</strong>
                  </div>
                </div>
              )}

              {/* FINAL DECISION BADGE */}
              <div className={`final-alert ${statusType}`}>
                <div>
                  <span>FINAL DECISION</span>
                  <strong>{finalStatus}</strong>
                  {faultType && (
                    <small>Fault Type: {faultType.replace("FAULT_", "")}</small>
                  )}
                </div>
                <div className="priority">{priority}</div>
              </div>

              <div className="decision-message">
                {decision.message || "System monitoring active."}
              </div>
            </div>
          </div>
        </section>

        {/* 30-DAY CONSUMPTION PROFILE */}
        <LoadProfileChart consumptionData={consumptionData} />

        {/* PHASE 3B: TAMPERING SIMULATOR BENCH */}
        <TamperingSimulatorCard
          meters={meters}
          selectedMeterId={meter.meter_id}
          onMeterSelect={(mId) => setSelectedMeter(mId)}
          onSimulationSuccess={(simRes) => {
            if (simRes.report) {
              setLatestSimReport(simRes.report);
            }
          }}
        />

        {/* PHASE 3B: FORENSIC INVESTIGATION BRIEF & AUDIT PANEL */}
        <InvestigationBriefPanel
          selectedMeterId={meter.meter_id}
          latestReportFromSimulation={latestSimReport}
        />

        {/* ACCOUNT INVESTIGATION PRIORITY QUEUE */}
        <AccountInvestigationQueue
          meters={meters}
          selectedMeter={meter.meter_id}
          onSelectMeter={setSelectedMeter}
        />

        {/* TRANSMISSION DIFFERENTIAL */}
        <section className="two-column bottom-section">
          <NetworkDifferentialCard
            readings={readings}
            statusType={statusType}
          />

          {/* CONNECTED METERS GRID */}
          <section className="panel network-panel" style={{ margin: 0 }}>
            <div className="panel-header">
              <div>
                <h2>Registered Simulation Accounts</h2>
                <p>Evaluation demo accounts (M001-M002) & synthetic benchmark profiles</p>
              </div>
              <Network size={23} />
            </div>

            <div className="network-grid">
              {meters.map((item) => {
                const type = getStatusType(item);
                const fault = item?.decision?.fault_type;
                const cat = getAccountCategory(item.meter_id);

                return (
                  <button
                    key={item.meter_id}
                    className={`network-meter ${
                      item.meter_id === meter.meter_id ? "selected" : ""
                    }`}
                    onClick={() => setSelectedMeter(item.meter_id)}
                  >
                    <div className="network-top">
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <Radio size={16} />
                        <strong>{item.meter_id}</strong>
                        <span style={{
                          fontSize: "0.58rem",
                          background: cat.badgeBg,
                          color: cat.badgeColor,
                          border: `1px solid ${cat.badgeBorder}`,
                          borderRadius: "3px",
                          padding: "1px 5px",
                          fontWeight: 700,
                          letterSpacing: "0.5px",
                        }} title={cat.fullLabel}>
                          {cat.label}
                        </span>
                      </div>
                      <span className={`network-status ${type}`}>
                        {getStatusText(item)}
                      </span>
                    </div>

                    {fault && (
                      <div className="network-fault">
                        Fault: {fault.replace("FAULT_", "")}
                      </div>
                    )}

                    <div className="network-values">
                      <div>
                        <span>POWER</span>
                        <strong>
                          {Number(item?.electrical?.power_W || 0).toFixed(1)} W
                        </strong>
                      </div>
                      <div>
                        <span>MODEL 1</span>
                        <strong>{item?.model1?.prediction || "WAITING"}</strong>
                      </div>
                      <div>
                        <span>MODEL 2</span>
                        <strong>{item?.model2?.prediction || "WAITING"}</strong>
                      </div>
                    </div>

                    <div className="network-bottom">
                      <span>{item.connection_state === "SIMULATED" || item.online ? "● Active Stream" : "○ Paused / Idle"}</span>
                      <span>Priority: {item?.decision?.priority || "LOW"}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </section>

        {/* FOOTER */}
        <footer>
          <span>MeterGuard AI • Utility Meter Tampering Detector</span>
          <span>Software Simulation Platform • AI Anomaly Detection • Real-Time Analytics</span>
        </footer>
      </main>
  );
}
