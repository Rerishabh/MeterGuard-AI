import { Zap, Activity, Gauge, CheckCircle2, AlertTriangle } from "lucide-react";

export default function MeterSummaryCard({
  voltage = 0,
  current = 0,
  power = 0,
  statusType = "normal",
  finalStatus = "MONITORING",
  priority = "LOW",
  faultType = null,
}) {
  return (
    <section className="cards-grid">
      {/* VOLTAGE */}
      <div className="metric-card voltage-card">
        <div className="metric-header">
          <span>Voltage</span>
          <div className="metric-icon cream-icon">
            <Zap size={21} />
          </div>
        </div>
        <div className="metric-value">
          {Number(voltage).toFixed(1)}
          <small>V</small>
        </div>
        <div className="metric-label">Simulated supply voltage</div>
      </div>

      {/* CURRENT */}
      <div className="metric-card current-card">
        <div className="metric-header">
          <span>Current</span>
          <div className="metric-icon sage-icon">
            <Activity size={21} />
          </div>
        </div>
        <div className="metric-value">
          {Number(current).toFixed(3)}
          <small>A</small>
        </div>
        <div className="metric-label">Simulated RMS current</div>
      </div>

      {/* POWER */}
      <div className="metric-card power-card">
        <div className="metric-header">
          <span>Power</span>
          <div className="metric-icon brown-icon">
            <Gauge size={21} />
          </div>
        </div>
        <div className="metric-value">
          {Number(power).toFixed(1)}
          <small>W</small>
        </div>
        <div className="metric-label">Simulated electrical load</div>
      </div>

      {/* SYSTEM STATUS */}
      <div className={`metric-card status-card ${statusType}`}>
        <div className="metric-header">
          <span>System Status</span>
          {statusType === "normal" ? (
            <CheckCircle2 size={23} />
          ) : (
            <AlertTriangle size={23} />
          )}
        </div>

        <div className="status-value">{finalStatus}</div>

        {faultType && (
          <div className="fault-type-main">
            FAULT TYPE:
            <strong>{faultType.replace("FAULT_", "")}</strong>
          </div>
        )}

        <div className="metric-label">Priority: {priority}</div>
      </div>
    </section>
  );
}
