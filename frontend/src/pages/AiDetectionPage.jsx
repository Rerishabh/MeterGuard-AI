import { useState } from "react";
import {
  Cpu,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  TrendingUp,
  Sliders,
  Zap,
  BarChart3,
} from "lucide-react";
import TamperingSimulatorCard from "../components/TamperingSimulatorCard";
import InvestigationBriefPanel from "../components/InvestigationBriefPanel";
import LoadProfileChart from "../charts/LoadProfileChart";
import { getStatusType, getStatusText } from "../services/statusHelpers";

export default function AiDetectionPage({
  dashboard,
  selectedMeter,
  setSelectedMeter,
  lastUpdate,
}) {
  const [latestSimReport, setLatestSimReport] = useState(null);

  const meters = dashboard?.meters || [];
  let meter = meters.find((m) => m.meter_id === selectedMeter) || meters[0] || {};

  const model1 = meter.model1 || {};
  const model2 = meter.model2 || {};
  const lstm = meter.lstm || {};
  const decision = meter.decision || {};

  const model1Prediction = model1.prediction || "WAITING";
  const model2Prediction = model2.prediction || "WAITING";
  const lstmStatus = lstm.status || "WAITING";
  const lstmError =
    lstm.reconstruction_error !== null && lstm.reconstruction_error !== undefined
      ? Number(lstm.reconstruction_error)
      : null;
  const lstmThreshold =
    lstm.threshold !== null && lstm.threshold !== undefined
      ? Number(lstm.threshold)
      : 0.013009;

  const finalStatus = decision.final_status || "MONITORING";
  const priority = decision.priority || "LOW";
  const faultType = decision.fault_type || model2.fault_type || null;
  const statusType = getStatusType(meter);

  const consumptionHistory = model1.consumption_history || meter.consumption_history || [];
  const consumptionData = consumptionHistory.map((value, index) => ({
    day: `D${index + 1}`,
    consumption: Number(value),
  }));

  // LSTM error percentage of threshold
  const errorRatio = lstmError !== null && lstmThreshold > 0
    ? Math.min((lstmError / lstmThreshold) * 100, 200).toFixed(0)
    : 0;

  return (
    <main className="main">
      {/* TOPBAR */}
      <header className="topbar">
        <div>
          <div className="title-row">
            <Cpu size={28} color="#22C55E" />
            <h1>AI Tampering Detection Suite</h1>
          </div>
          <p>Multi-model machine learning architecture & autoencoder reconstruction arbitration</p>
        </div>

        <div className="topbar-right">
          <div className="live-badge">
            <span className="live-dot"></span>
            ACTIVE INFERENCE
          </div>

          <div className="time-display">
            <Clock3 size={17} />
            {lastUpdate ? lastUpdate.toLocaleTimeString() : "--"}
          </div>
        </div>
      </header>

      {/* METER SELECTOR */}
      <section className="meter-toolbar">
        <div className="meter-selector">
          <span>TARGET METER</span>
          <select
            value={meter.meter_id || ""}
            onChange={(e) => setSelectedMeter(e.target.value)}
          >
            {meters.map((item) => (
              <option key={item.meter_id} value={item.meter_id}>
                {item.meter_id} - {item.location?.location_name || "Grid Zone"} ({getStatusText(item)})
              </option>
            ))}
          </select>
        </div>

        <div className={`final-alert ${statusType}`} style={{ margin: 0, padding: "8px 16px", borderRadius: "8px" }}>
          <div>
            <span style={{ fontSize: "10px", color: "var(--sage)" }}>DECISION</span>
            <strong style={{ fontSize: "15px", marginLeft: "6px" }}>{finalStatus}</strong>
          </div>
          <div className="priority" style={{ fontSize: "12px", padding: "2px 8px" }}>Priority: {priority}</div>
        </div>
      </section>

      {/* THREE ML ENGINE CARDS */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(310px, 1fr))",
          gap: "18px",
          marginBottom: "24px",
        }}
      >
        {/* MODEL 1: ISOLATION FOREST */}
        <div className="panel" style={{ position: "relative", overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <span style={{ fontSize: "11px", color: "var(--sage)", letterSpacing: "1.2px", textTransform: "uppercase" }}>
                Model 1 • Unsupervised Baseline
              </span>
              <h3 style={{ margin: "4px 0 0", color: "#FFFFFF", fontSize: "1.25rem" }}>
                Isolation Forest
              </h3>
            </div>
            <div style={{ background: "rgba(10, 41, 71, 0.8)", padding: "8px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.2)" }}>
              <Sliders size={20} color="#F3E4C9" />
            </div>
          </div>

          <p style={{ fontSize: "12.5px", color: "var(--sage)", margin: "10px 0 16px", lineHeight: "1.4" }}>
            Extracts statistical features from daily consumption profiles to detect extreme volumetric anomalies.
          </p>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px" }}>
            <span style={{ fontSize: "13px", color: "var(--cream)" }}>Anomaly Verdict:</span>
            <span
              className={`prediction ${model1Prediction.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
              style={{ fontSize: "13px", fontWeight: "700" }}
            >
              {model1Prediction}
            </span>
          </div>
        </div>

        {/* MODEL 2: RANDOM FOREST HARDWARE FAULT */}
        <div className="panel" style={{ position: "relative", overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <span style={{ fontSize: "11px", color: "var(--sage)", letterSpacing: "1.2px", textTransform: "uppercase" }}>
                Model 2 • Supervised Classifier
              </span>
              <h3 style={{ margin: "4px 0 0", color: "#FFFFFF", fontSize: "1.25rem" }}>
                Random Forest Differential
              </h3>
            </div>
            <div style={{ background: "rgba(10, 41, 71, 0.8)", padding: "8px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.2)" }}>
              <Zap size={20} color="#22C55E" />
            </div>
          </div>

          <p style={{ fontSize: "12.5px", color: "var(--sage)", margin: "10px 0 16px", lineHeight: "1.4" }}>
            Analyzes high-frequency current differentials across pole transformer (T1, T2) and meter (H1).
          </p>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px" }}>
            <span style={{ fontSize: "13px", color: "var(--cream)" }}>
              {faultType ? `Fault: ${faultType.replace("FAULT_", "")}` : "Hardware Status:"}
            </span>
            <span className={`prediction ${model2Prediction.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} style={{ fontSize: "13px", fontWeight: "700" }}>
              {model2Prediction}
            </span>
          </div>
        </div>

        {/* MODEL 3: LSTM AUTOENCODER */}
        <div className="panel" style={{ position: "relative", overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <span style={{ fontSize: "11px", color: "var(--sage)", letterSpacing: "1.2px", textTransform: "uppercase" }}>
                Model 3 • Deep Sequence AE
              </span>
              <h3 style={{ margin: "4px 0 0", color: "#FFFFFF", fontSize: "1.25rem" }}>
                LSTM Autoencoder
              </h3>
            </div>
            <div style={{ background: "rgba(10, 41, 71, 0.8)", padding: "8px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.2)" }}>
              <BarChart3 size={20} color="#4ADE80" />
            </div>
          </div>

          <p style={{ fontSize: "12.5px", color: "var(--sage)", margin: "10px 0 16px", lineHeight: "1.4" }}>
            Reconstructs 30-day temporal kWh sequences. Errors exceeding the 95th percentile indicate theft.
          </p>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", background: "rgba(6, 28, 49, 0.6)", borderRadius: "8px" }}>
            <span style={{ fontSize: "13px", color: "var(--cream)" }}>Sequence Verdict:</span>
            <span
              className={`prediction ${
                lstmStatus === "NORMAL"
                  ? "normal"
                  : lstmStatus === "SUSPICIOUS"
                  ? "suspicious"
                  : "waiting"
              }`}
              style={{ fontSize: "13px", fontWeight: "700" }}
            >
              {lstmStatus}
            </span>
          </div>
        </div>
      </div>

      {/* RECONSTRUCTION ERROR GAUGE & ARBITRATION CARD */}
      <section className="panel" style={{ marginBottom: "24px" }}>
        <div className="panel-header">
          <div>
            <h2>LSTM Reconstruction Error vs. Anomaly Threshold</h2>
            <p>Empirical reconstruction Mean Squared Error (MSE) evaluated against validated 95th% boundary</p>
          </div>
          <TrendingUp size={22} color="#22C55E" />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px", marginTop: "16px", alignItems: "center" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px" }}>
              <span style={{ color: "var(--sage)" }}>
                Reconstruction MSE: <strong style={{ color: "#FFFFFF" }}>{lstmError !== null ? lstmError.toFixed(6) : "Awaiting Sequence"}</strong>
              </span>
              <span style={{ color: "var(--sage)" }}>
                95th% Threshold: <strong style={{ color: "#4ADE80" }}>{lstmThreshold.toFixed(6)}</strong>
              </span>
            </div>

            {/* PROGRESS GAUGE BAR */}
            <div style={{ width: "100%", height: "14px", background: "rgba(6, 28, 49, 0.8)", borderRadius: "7px", overflow: "hidden", border: "1px solid rgba(211, 212, 192, 0.2)", position: "relative" }}>
              <div
                style={{
                  width: `${Math.min(errorRatio, 100)}%`,
                  height: "100%",
                  background:
                    lstmStatus === "SUSPICIOUS"
                      ? "linear-gradient(90deg, #F59E0B, #EF4444)"
                      : "linear-gradient(90deg, #10B981, #22C55E)",
                  borderRadius: "7px",
                  transition: "width 0.4s ease",
                }}
              ></div>
              {/* Threshold Marker at 100% position */}
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  top: 0,
                  bottom: 0,
                  width: "2px",
                  background: "#FFFFFF",
                  opacity: 0.7,
                }}
                title="95th Percentile Threshold Cutoff"
              ></div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px", fontSize: "11px", color: "var(--sage-dark)" }}>
              <span>0.000000 (Nominal Fit)</span>
              <span>Threshold Boundary (0.013009)</span>
              <span>2.0× Scale</span>
            </div>
          </div>

          <div style={{ background: "rgba(6, 28, 49, 0.6)", padding: "16px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {finalStatus === "NORMAL" ? (
                <CheckCircle2 size={20} color="#22C55E" />
              ) : (
                <AlertTriangle size={20} color="#EF4444" />
              )}
              <strong style={{ color: "#FFFFFF", fontSize: "15px" }}>Arbitration Verdict: {finalStatus}</strong>
            </div>
            <p style={{ fontSize: "12.5px", color: "var(--sage)", margin: "8px 0 0", lineHeight: "1.4" }}>
              {decision.message || "All models operating within verified baseline confidence limits."}
            </p>
          </div>
        </div>
      </section>

      {/* 30-DAY CONSUMPTION PROFILE CHART */}
      <section style={{ marginBottom: "24px" }}>
        <LoadProfileChart consumptionData={consumptionData} />
      </section>

      {/* PHASE 3B TAMPERING SIMULATOR BENCH */}
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

      {/* PHASE 3B FORENSIC INVESTIGATION BRIEF & AUDIT PANEL */}
      <InvestigationBriefPanel
        selectedMeterId={meter.meter_id}
        latestReportFromSimulation={latestSimReport}
      />

      {/* FOOTER */}
      <footer>
        <span>MeterGuard AI • Multi-Model Anomaly Arbitration</span>
        <span>Isolation Forest • Random Forest • LSTM Autoencoder • Gemini 3.8 Flash</span>
      </footer>
    </main>
  );
}
