import {
  Activity,
  Zap,
  Wifi,
  WifiOff,
  Clock3,
  Gauge,
  Cpu,
  Layers,
  ArrowUpRight,
  TrendingDown,
} from "lucide-react";
import LiveElectricalChart from "../charts/LiveElectricalChart";
import MeterSummaryCard from "../components/MeterSummaryCard";
import { getStatusType } from "../services/statusHelpers";

export default function LiveMonitoringPage({
  dashboard,
  selectedMeter,
  setSelectedMeter,
  lastUpdate,
}) {
  const meters = dashboard?.meters || [];
  let meter = meters.find((m) => m.meter_id === selectedMeter) || meters[0] || {};

  const readings = meter.readings || {};
  const electrical = meter.electrical || {};
  const decision = meter.decision || {};
  const liveHistory = meter.live_history || [];

  const voltage = Number(electrical.voltage_V || 0);
  const current = Number(electrical.current_A || 0);
  const power = Number(electrical.power_W || 0);
  const statusType = getStatusType(meter);
  const finalStatus = decision.final_status || "MONITORING";
  const priority = decision.priority || "LOW";
  const faultType = decision.fault_type || null;

  const connectionState = meter.connection_state || (meter.online !== false ? "ONLINE" : "OFFLINE");
  const isSimulated = Boolean(meter.is_simulated || meter.meter_id?.startsWith("M_SIM_"));

  const liveChartData = liveHistory.map((item, index) => ({
    reading: index + 1,
    power: Number(item.power_W || 0),
    current: Number(item.current_A || 0),
    voltage: Number(item.voltage_V || 0),
  }));

  // Calculate high-frequency electrical stats
  const powers = liveHistory.map((h) => Number(h.power_W || 0)).filter((p) => p > 0);
  const peakPower = powers.length ? Math.max(...powers).toFixed(1) : power.toFixed(1);
  const avgPower = powers.length
    ? (powers.reduce((a, b) => a + b, 0) / powers.length).toFixed(1)
    : power.toFixed(1);
  const powerFactor = voltage > 0 && current > 0 ? (power / (voltage * current)).toFixed(2) : "0.98";

  return (
    <main className="main">
      {/* TOPBAR */}
      <header className="topbar">
        <div>
          <div className="title-row">
            <Activity size={28} color="#22C55E" />
            <h1>Live Electrical Telemetry</h1>
          </div>
          <p>Real-time high-frequency ESP32 sensor stream & differential monitoring</p>
        </div>

        <div className="topbar-right">
          {connectionState === "ONLINE" && (
            <div className="live-badge">
              <span className="live-dot"></span>
              STREAMING (100ms)
            </div>
          )}
          {connectionState === "STALE" && (
            <div className="live-badge" style={{ background: "rgba(245, 158, 11, 0.2)", color: "#F59E0B", border: "1px solid rgba(245, 158, 11, 0.4)" }}>
              <span className="live-dot" style={{ background: "#F59E0B" }}></span>
              STALE TELEMETRY
            </div>
          )}
          {connectionState === "OFFLINE" && (
            <div className="live-badge" style={{ background: "rgba(239, 68, 68, 0.2)", color: "#EF4444", border: "1px solid rgba(239, 68, 68, 0.4)" }}>
              <span className="live-dot" style={{ background: "#EF4444" }}></span>
              METER OFFLINE
            </div>
          )}

          {isSimulated && (
            <div style={{ fontSize: "11px", fontWeight: "600", padding: "4px 8px", borderRadius: "6px", background: "rgba(147, 51, 234, 0.2)", color: "#C084FC", border: "1px solid rgba(147, 51, 234, 0.4)" }}>
              BENCH REPLAY
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
          <span>SELECT METER</span>
          <select
            value={meter.meter_id || ""}
            onChange={(e) => setSelectedMeter(e.target.value)}
          >
            {meters.map((item) => (
              <option key={item.meter_id} value={item.meter_id}>
                {item.meter_id} ({item.location?.location_name || "Zone"})
              </option>
            ))}
          </select>
        </div>

        <div className="connection-status">
          {connectionState === "ONLINE" && (
            <>
              <Wifi size={18} color="#22C55E" />
              Meter {meter.meter_id}
              <span className="live-dot" style={{ background: "#22C55E" }}></span>
              Online
            </>
          )}
          {connectionState === "STALE" && (
            <>
              <Clock3 size={18} color="#F59E0B" />
              Meter {meter.meter_id}
              <span className="live-dot" style={{ background: "#F59E0B" }}></span>
              Stale {meter.last_seen_seconds != null ? `(${meter.last_seen_seconds}s ago)` : ""}
            </>
          )}
          {connectionState === "OFFLINE" && (
            <>
              <WifiOff size={18} color="#EF4444" />
              Meter {meter.meter_id}
              <span className="offline-dot"></span>
              Offline
            </>
          )}
        </div>
      </section>

      {/* ELECTRICAL METRICS HERO CARD */}
      <MeterSummaryCard
        voltage={voltage}
        current={current}
        power={power}
        statusType={statusType}
        finalStatus={finalStatus}
        priority={priority}
        faultType={faultType}
      />

      {/* EXPANDED TELEMETRY ANALYSIS GRID */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "22px",
        }}
      >
        <div className="panel" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--sage)" }}>
            <span style={{ fontSize: "12px", letterSpacing: "1px", textTransform: "uppercase" }}>Peak Power Observed</span>
            <ArrowUpRight size={18} color="#22C55E" />
          </div>
          <div style={{ fontSize: "2rem", fontWeight: "700", color: "#FFFFFF", marginTop: "8px" }}>
            {peakPower} <span style={{ fontSize: "1rem", color: "var(--sage)" }}>W</span>
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Max reading in buffer</small>
        </div>

        <div className="panel" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--sage)" }}>
            <span style={{ fontSize: "12px", letterSpacing: "1px", textTransform: "uppercase" }}>Average Active Load</span>
            <Gauge size={18} color="#4ADE80" />
          </div>
          <div style={{ fontSize: "2rem", fontWeight: "700", color: "#FFFFFF", marginTop: "8px" }}>
            {avgPower} <span style={{ fontSize: "1rem", color: "var(--sage)" }}>W</span>
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Buffer rolling mean</small>
        </div>

        <div className="panel" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--sage)" }}>
            <span style={{ fontSize: "12px", letterSpacing: "1px", textTransform: "uppercase" }}>Calculated Power Factor</span>
            <Zap size={18} color="#F3E4C9" />
          </div>
          <div style={{ fontSize: "2rem", fontWeight: "700", color: "#FFFFFF", marginTop: "8px" }}>
            {powerFactor}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>P / (V × I) reference</small>
        </div>

        <div className="panel" style={{ padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--sage)" }}>
            <span style={{ fontSize: "12px", letterSpacing: "1px", textTransform: "uppercase" }}>Nominal Voltage Range</span>
            <TrendingDown size={18} color="#22C55E" />
          </div>
          <div style={{ fontSize: "2rem", fontWeight: "700", color: "#FFFFFF", marginTop: "8px" }}>
            {voltage > 0 ? "230V ± 5%" : "--"}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Grid compliance standard</small>
        </div>
      </div>

      {/* LIVE ELECTRICAL CHART */}
      <section style={{ marginBottom: "24px" }}>
        <LiveElectricalChart
          voltage={voltage}
          current={current}
          power={power}
          liveChartData={liveChartData}
        />
      </section>

      {/* TWO-COLUMN: SENSOR ADC DETAILS + TELEMETRY BUFFER TABLE */}
      <section className="two-column">
        {/* RAW SENSOR CHANNELS */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Differential Sensor ADCs</h2>
              <p>Hardware current & voltage transformer telemetry</p>
            </div>
            <Cpu size={22} color="#22C55E" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginTop: "14px" }}>
            <div style={{ background: "rgba(6, 28, 49, 0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)" }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase" }}>Pole Transformer T1 CS</span>
              <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
                {readings.T1_CS !== undefined && readings.T1_CS !== null ? readings.T1_CS : "--"} <small style={{ fontSize: "11px", color: "var(--sage)" }}>ADC</small>
              </div>
            </div>

            <div style={{ background: "rgba(6, 28, 49, 0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)" }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase" }}>Pole Transformer T1 VS</span>
              <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
                {readings.T1_VS !== undefined && readings.T1_VS !== null ? readings.T1_VS : "--"} <small style={{ fontSize: "11px", color: "var(--sage)" }}>ADC</small>
              </div>
            </div>

            <div style={{ background: "rgba(6, 28, 49, 0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)" }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase" }}>Secondary Line T2 CS</span>
              <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
                {readings.T2_CS !== undefined && readings.T2_CS !== null ? readings.T2_CS : "--"} <small style={{ fontSize: "11px", color: "var(--sage)" }}>ADC</small>
              </div>
            </div>

            <div style={{ background: "rgba(6, 28, 49, 0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)" }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase" }}>Secondary Line T2 VS</span>
              <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
                {readings.T2_VS !== undefined && readings.T2_VS !== null ? readings.T2_VS : "--"} <small style={{ fontSize: "11px", color: "var(--sage)" }}>ADC</small>
              </div>
            </div>

            <div style={{ background: "rgba(6, 28, 49, 0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)" }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase" }}>Household Meter H1 CS</span>
              <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
                {readings.H1_CS !== undefined && readings.H1_CS !== null ? readings.H1_CS : "--"} <small style={{ fontSize: "11px", color: "var(--sage)" }}>ADC</small>
              </div>
            </div>

            <div style={{ background: "rgba(6, 28, 49, 0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(211, 212, 192, 0.15)" }}>
              <span style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase" }}>Household Meter H1 VS</span>
              <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
                {readings.H1_VS !== undefined && readings.H1_VS !== null ? readings.H1_VS : "--"} <small style={{ fontSize: "11px", color: "var(--sage)" }}>ADC</small>
              </div>
            </div>
          </div>
        </div>

        {/* TELEMETRY STREAM LOG */}
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Recent Telemetry Frames</h2>
              <p>Rolling high-frequency measurements</p>
            </div>
            <Layers size={22} color="#22C55E" />
          </div>

          <div style={{ overflowX: "auto", marginTop: "12px" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(211, 212, 192, 0.2)", color: "var(--sage)" }}>
                  <th style={{ padding: "8px 6px" }}>#</th>
                  <th style={{ padding: "8px 6px" }}>Voltage</th>
                  <th style={{ padding: "8px 6px" }}>Current</th>
                  <th style={{ padding: "8px 6px" }}>Power</th>
                  <th style={{ padding: "8px 6px" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {liveHistory.slice(-6).reverse().map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: "1px solid rgba(211, 212, 192, 0.08)" }}>
                    <td style={{ padding: "8px 6px", color: "var(--sage)" }}>{liveHistory.length - idx}</td>
                    <td style={{ padding: "8px 6px", color: "#FFFFFF" }}>{Number(item.voltage_V || 0).toFixed(1)} V</td>
                    <td style={{ padding: "8px 6px", color: "#FFFFFF" }}>{Number(item.current_A || 0).toFixed(2)} A</td>
                    <td style={{ padding: "8px 6px", color: "#4ADE80", fontWeight: "600" }}>{Number(item.power_W || 0).toFixed(1)} W</td>
                    <td style={{ padding: "8px 6px" }}>
                      <span className="live-dot" style={{ display: "inline-block", marginRight: "6px" }}></span>
                      <span style={{ color: "var(--cream)", fontSize: "11px" }}>Synced</span>
                    </td>
                  </tr>
                ))}
                {liveHistory.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ padding: "24px", textAlign: "center", color: "var(--sage)" }}>
                      Awaiting high-frequency telemetry frames from backend...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <span>MeterGuard AI • High-Frequency Live Telemetry</span>
        <span>ESP32 Differential Hardware Streaming • 100ms Polling</span>
      </footer>
    </main>
  );
}
