import { useState } from "react";
import {
  Network,
  Clock3,
  Search,
  Filter,
  Radio,
  Wifi,
  WifiOff,
  Zap,
  Activity,
  ShieldAlert,
} from "lucide-react";
import { getStatusType, getStatusText } from "../services/statusHelpers";

export default function MeterNetworkPage({
  dashboard,
  selectedMeter,
  setSelectedMeter,
  lastUpdate,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const meters = dashboard?.meters || [];
  let currentMeter = meters.find((m) => m.meter_id === selectedMeter) || meters[0] || {};

  // Filter meters based on search and status
  const filteredMeters = meters.filter((m) => {
    const matchesSearch =
      m.meter_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (m.location?.location_name || "").toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (statusFilter === "ALL") return true;
    if (statusFilter === "ONLINE") return m.online !== false;
    if (statusFilter === "OFFLINE") return m.online === false;

    const type = getStatusType(m);
    if (statusFilter === "NORMAL") return type === "normal";
    if (statusFilter === "SUSPICIOUS") return type === "suspicious";
    if (statusFilter === "FAULT") return type === "fault";

    return true;
  });

  const totalCount = meters.length;
  const onlineCount = meters.filter((m) => m.online !== false).length;
  const suspiciousCount = meters.filter((m) => getStatusType(m) === "suspicious").length;
  const faultCount = meters.filter((m) => getStatusType(m) === "fault").length;

  return (
    <main className="main">
      {/* TOPBAR */}
      <header className="topbar">
        <div>
          <div className="title-row">
            <Network size={28} color="#22C55E" />
            <h1>Connected Meter Network</h1>
          </div>
          <p>Distribution grid infrastructure inventory & connection status directory</p>
        </div>

        <div className="topbar-right">
          <div className="live-badge">
            <span className="live-dot"></span>
            {onlineCount}/{totalCount} ONLINE
          </div>

          <div className="time-display">
            <Clock3 size={17} />
            {lastUpdate ? lastUpdate.toLocaleTimeString() : "--"}
          </div>
        </div>
      </header>

      {/* METRIC OVERVIEW CARDS */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "20px",
        }}
      >
        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>Total Smart Meters</span>
            <Network size={16} color="var(--cream)" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
            {totalCount}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Registered in database</small>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>Online Connections</span>
            <Wifi size={16} color="#22C55E" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#22C55E", marginTop: "4px" }}>
            {onlineCount}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Actively polling telemetry</small>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>Theft / Suspicious</span>
            <ShieldAlert size={16} color="#F59E0B" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#F59E0B", marginTop: "4px" }}>
            {suspiciousCount}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>LSTM or IF anomalous</small>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--sage)", fontSize: "11px", textTransform: "uppercase" }}>
            <span>Hardware Faults</span>
            <Zap size={16} color="#EF4444" />
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: "700", color: "#EF4444", marginTop: "4px" }}>
            {faultCount}
          </div>
          <small style={{ color: "var(--sage-dark)", fontSize: "11px" }}>Model 2 differential breaches</small>
        </div>
      </div>

      {/* SEARCH AND FILTER BAR */}
      <section className="panel" style={{ padding: "14px 18px", marginBottom: "22px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "14px", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ position: "relative", flex: "1 1 280px" }}>
            <Search size={18} color="var(--sage)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
            <input
              type="text"
              placeholder="Search by Meter ID (e.g. M001) or Sector/Location..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px 10px 38px",
                borderRadius: "8px",
                border: "1px solid rgba(211, 212, 192, 0.25)",
                background: "rgba(6, 28, 49, 0.8)",
                color: "#FFFFFF",
                fontSize: "13.5px",
                outline: "none",
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <Filter size={16} color="var(--sage)" />
            <span style={{ fontSize: "12px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "1px" }}>Filter:</span>
            {["ALL", "ONLINE", "NORMAL", "SUSPICIOUS", "FAULT", "OFFLINE"].map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setStatusFilter(tab)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: statusFilter === tab ? "1px solid #22C55E" : "1px solid rgba(211, 212, 192, 0.2)",
                  background: statusFilter === tab ? "rgba(34, 197, 94, 0.2)" : "rgba(10, 41, 71, 0.5)",
                  color: statusFilter === tab ? "#FFFFFF" : "var(--sage)",
                  fontSize: "12px",
                  fontWeight: statusFilter === tab ? "600" : "400",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* METERS GRID */}
      <section className="network-grid" style={{ marginBottom: "24px" }}>
        {filteredMeters.map((item) => {
          const type = getStatusType(item);
          const fault = item?.decision?.fault_type;
          const isSelected = item.meter_id === currentMeter.meter_id;

          return (
            <button
              key={item.meter_id}
              type="button"
              className={`network-meter ${isSelected ? "selected" : ""}`}
              onClick={() => setSelectedMeter(item.meter_id)}
              style={{
                cursor: "pointer",
                textAlign: "left",
                fontFamily: "inherit",
              }}
            >
              <div className="network-top">
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Radio size={18} color="#22C55E" />
                  <strong>{item.meter_id}</strong>
                  {item.location?.location_name && (
                    <span style={{ fontSize: "11px", color: "var(--sage)" }}>({item.location.location_name})</span>
                  )}
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
                  <strong>{Number(item?.electrical?.power_W || 0).toFixed(1)} W</strong>
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

              <div className="network-bottom" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  {item.online !== false ? (
                    <>
                      <Wifi size={13} color="#22C55E" /> Online
                    </>
                  ) : (
                    <>
                      <WifiOff size={13} color="#EF4444" /> Offline
                    </>
                  )}
                </span>
                <span>Priority: {item?.decision?.priority || "LOW"}</span>
              </div>
            </button>
          );
        })}

        {filteredMeters.length === 0 && (
          <div style={{ gridColumn: "1 / -1", padding: "48px 24px", textAlign: "center", background: "rgba(6, 28, 49, 0.6)", borderRadius: "10px", color: "var(--sage)" }}>
            <Activity size={36} color="var(--sage-dark)" style={{ margin: "0 auto 12px" }} />
            <h3 style={{ color: "#FFFFFF", margin: "0 0 8px" }}>No Meters Match Filter</h3>
            <p style={{ margin: 0, fontSize: "13px" }}>Try adjusting your search query or status filter buttons above.</p>
          </div>
        )}
      </section>

      {/* FOOTER */}
      <footer>
        <span>MeterGuard AI • Grid Network Infrastructure</span>
        <span>Registered Smart Meters • Real-Time Heartbeat Synchronization</span>
      </footer>
    </main>
  );
}
