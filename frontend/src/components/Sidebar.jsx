import {
  Gauge,
  Activity,
  ShieldCheck,
  MapPin,
  Network,
  Bell,
  Settings,
  Shield,
} from "lucide-react";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand" style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px 16px" }}>
        <div style={{ background: "var(--navy-light)", borderRadius: "8px", padding: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Shield size={24} color="#22C55E" />
        </div>
        <div>
          <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#FFFFFF", letterSpacing: "0.5px" }}>
            MeterGuard AI
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "1px" }}>
            Tampering Detector
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-item active">
          <Gauge size={20} />
          <span>Dashboard</span>
        </div>

        <div className="nav-item">
          <Activity size={20} />
          <span>Live Monitoring</span>
        </div>

        <div className="nav-item">
          <ShieldCheck size={20} />
          <span>AI Detection</span>
        </div>

        <div className="nav-item">
          <MapPin size={20} />
          <span>Meter Locations</span>
        </div>

        <div className="nav-item">
          <Network size={20} />
          <span>Meter Network</span>
        </div>

        <div className="nav-item">
          <Bell size={20} />
          <span>Alerts & Logs</span>
        </div>

        <div className="nav-item">
          <Settings size={20} />
          <span>Settings</span>
        </div>
      </nav>

      <div className="sidebar-bottom">
        <div className="backend-card">
          <div className="backend-status">
            <span className="live-dot"></span>
            Backend Online
          </div>
          <div className="backend-text">
            ESP32 • Flask • AI
          </div>
        </div>

        <div className="sidebar-footer-text">
          MeterGuard AI Monitoring
        </div>
      </div>
    </aside>
  );
}
