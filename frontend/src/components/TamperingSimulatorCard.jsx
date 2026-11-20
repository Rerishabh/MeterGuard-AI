import { useState } from "react";
import {
  Play,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Sliders,
  Sparkles,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { simulateTampering } from "../services/api";

const SCENARIOS = [
  { id: "sudden_drop", label: "Sudden Consumption Drop (55-65% reduction)" },
  { id: "flatline", label: "Flatline Meter (~0.4 kWh/day stuck/shunt)" },
  { id: "consumption_spike", label: "Consumption Spike (Severe surges >14 kWh)" },
  { id: "abnormally_low_night", label: "Abnormally Low Nighttime / Basal Suppression" },
  { id: "inversion", label: "Weekday/Weekend Inversion (Inverted Profile)" },
  { id: "normal", label: "Normal Baseline Profile (~5.0 kWh/day)" },
];

export default function TamperingSimulatorCard({
  meters = [],
  selectedMeterId = "M001",
  onMeterSelect,
  onSimulationSuccess,
}) {
  const [targetMeter, setTargetMeter] = useState(selectedMeterId);
  const [scenario, setScenario] = useState("sudden_drop");
  const [autoReport, setAutoReport] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);

  // Sync if parent selectedMeter changes
  if (selectedMeterId && targetMeter !== selectedMeterId && meters.some((m) => m.meter_id === selectedMeterId)) {
    // Only update if targetMeter wasn't explicitly changed
  }

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await simulateTampering(targetMeter, scenario, autoReport);
      setSimulationResult(res);
      if (onSimulationSuccess) {
        onSimulationSuccess(res);
      }
    } catch (err) {
      setError(err.message || "Simulation execution failed");
    } finally {
      setLoading(false);
    }
  };

  const chartData = simulationResult?.consumption?.map((kwh, idx) => ({
    day: `D${idx + 1}`,
    consumption: kwh,
  })) || [];

  const lstm = simulationResult?.lstm_result;
  const isAnomaly = lstm?.is_anomaly;

  return (
    <section className="panel simulation-panel">
      <div className="panel-header">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              background: "rgba(243, 228, 201, 0.1)",
              padding: "8px",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Sliders size={22} color="var(--cream)" />
          </div>
          <div>
            <h2>Tampering & Anomaly Simulator</h2>
            <p>Simulate realistic 30-day consumption scenarios and evaluate LSTM Autoencoder</p>
          </div>
        </div>

        <span
          className="badge-simulated"
          style={{
            background: "rgba(139, 94, 60, 0.25)",
            border: "1px solid var(--brown)",
            color: "var(--cream)",
            padding: "4px 10px",
            borderRadius: "16px",
            fontSize: "0.75rem",
            fontWeight: "600",
            letterSpacing: "0.5px",
          }}
        >
          SIMULATOR BENCH
        </span>
      </div>

      {/* CONTROLS */}
      <div
        className="simulator-controls"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginTop: "16px",
          background: "rgba(6, 28, 49, 0.5)",
          padding: "16px",
          borderRadius: "12px",
          border: "1px solid var(--border)",
        }}
      >
        <div>
          <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "6px" }}>
            Target Smart Meter:
          </label>
          <select
            value={targetMeter}
            onChange={(e) => {
              setTargetMeter(e.target.value);
              if (onMeterSelect) onMeterSelect(e.target.value);
            }}
            style={{
              width: "100%",
              padding: "10px",
              borderRadius: "8px",
              background: "var(--navy-light)",
              color: "#FFF",
              border: "1px solid var(--border)",
              fontSize: "0.9rem",
            }}
          >
            {meters.map((m) => (
              <option key={m.meter_id} value={m.meter_id}>
                {m.meter_id} {m.location?.name ? `(${m.location.name})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "6px" }}>
            Tampering / Anomaly Scenario:
          </label>
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            style={{
              width: "100%",
              padding: "10px",
              borderRadius: "8px",
              background: "var(--navy-light)",
              color: "#FFF",
              border: "1px solid var(--border)",
              fontSize: "0.9rem",
            }}
          >
            {SCENARIOS.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.label}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "0.85rem",
              color: "var(--cream)",
              cursor: "pointer",
              marginBottom: "10px",
            }}
          >
            <input
              type="checkbox"
              checked={autoReport}
              onChange={(e) => setAutoReport(e.target.checked)}
              style={{ accentColor: "var(--green)", width: "16px", height: "16px" }}
            />
            <Sparkles size={16} color="var(--cream)" />
            Auto-generate forensic report
          </label>

          <button
            onClick={handleSimulate}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              padding: "11px 20px",
              borderRadius: "8px",
              background: loading ? "var(--navy-light)" : "linear-gradient(135deg, #22C55E 0%, #15803D 100%)",
              color: "#FFFFFF",
              fontWeight: "700",
              border: "none",
              cursor: loading ? "not-allowed" : "pointer",
              boxShadow: "0 4px 15px rgba(34, 197, 94, 0.3)",
              transition: "all 0.2s ease",
            }}
          >
            {loading ? (
              <>
                <RefreshCw size={18} className="spin-icon" />
                SIMULATING & EVALUATING...
              </>
            ) : (
              <>
                <Play size={18} />
                SIMULATE & ANALYZE
              </>
            )}
          </button>
        </div>
      </div>

      {/* ERROR FEEDBACK */}
      {error && (
        <div
          style={{
            marginTop: "12px",
            padding: "12px 16px",
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
          <AlertTriangle size={18} color="#EF4444" />
          <span>{error}</span>
        </div>
      )}

      {/* SIMULATION VISUALIZATION */}
      {simulationResult && (
        <div style={{ marginTop: "20px" }}>
          {/* BADGE & STATS HEADER */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "12px",
              padding: "12px 16px",
              background: "rgba(10, 41, 71, 0.7)",
              borderRadius: "10px",
              border: "1px solid var(--border)",
              marginBottom: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span
                style={{
                  background: isAnomaly ? "rgba(239, 68, 68, 0.2)" : "rgba(34, 197, 94, 0.2)",
                  border: `1px solid ${isAnomaly ? "var(--red)" : "var(--green)"}`,
                  color: isAnomaly ? "#F87171" : "#4ADE80",
                  padding: "4px 12px",
                  borderRadius: "20px",
                  fontSize: "0.8rem",
                  fontWeight: "700",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                {isAnomaly ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
                ML CLASSIFICATION: {lstm?.status || (isAnomaly ? "SUSPICIOUS" : "NORMAL")}
              </span>

              <span
                style={{
                  background: "rgba(243, 228, 201, 0.15)",
                  border: "1px solid var(--cream-soft)",
                  color: "var(--cream)",
                  padding: "4px 10px",
                  borderRadius: "20px",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                }}
              >
                ● SIMULATED DATA ({simulationResult.scenario_name})
              </span>
            </div>

            <div style={{ display: "flex", gap: "16px", fontSize: "0.85rem" }}>
              <div>
                <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", display: "block" }}>
                  RECONSTRUCTION MSE
                </span>
                <strong style={{ color: isAnomaly ? "#F87171" : "var(--cream)" }}>
                  {lstm?.reconstruction_error}
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", display: "block" }}>
                  ACTIVE THRESHOLD (95%)
                </span>
                <strong style={{ color: "var(--sage)" }}>{lstm?.threshold}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", display: "block" }}>
                  MEAN CONSUMPTION
                </span>
                <strong style={{ color: "var(--cream)" }}>{simulationResult.stats?.mean_kwh} kWh/d</strong>
              </div>
            </div>
          </div>

          {/* 30-DAY CHART */}
          <div className="large-chart" style={{ height: "260px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(211, 212, 192, 0.15)" />
                <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={11} interval={2} />
                <YAxis
                  stroke="var(--text-muted)"
                  fontSize={11}
                  unit=" kWh"
                  domain={[0, "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(6, 28, 49, 0.95)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    color: "#FFF",
                  }}
                  formatter={(val) => [`${Number(val).toFixed(2)} kWh`, "Daily Consumption"]}
                />
                <ReferenceLine
                  y={5.0}
                  stroke="var(--cream-soft)"
                  strokeDasharray="4 4"
                  label={{ value: "Baseline (~5.0 kWh)", fill: "var(--cream-soft)", fontSize: 10, position: "insideTopLeft" }}
                />
                <Line
                  type="monotone"
                  dataKey="consumption"
                  name="Consumption (kWh)"
                  stroke={isAnomaly ? "#EF4444" : "#22C55E"}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: isAnomaly ? "#EF4444" : "#22C55E" }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </section>
  );
}
