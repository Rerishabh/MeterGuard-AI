import {
  Gauge,
  Activity,
  ShieldCheck,
  MapPin,
  Network,
  Bell,
  Settings,
} from "lucide-react";
import MeterLogo from "./MeterLogo";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: Gauge },
  { id: "live-monitoring", label: "Live Monitoring", icon: Activity },
  { id: "ai-detection", label: "AI Detection", icon: ShieldCheck },
  { id: "meter-locations", label: "Meter Locations", icon: MapPin },
  { id: "meter-network", label: "Meter Network", icon: Network },
  { id: "alerts-logs", label: "Alerts & Logs", icon: Bell },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function Sidebar({
  currentTab = "dashboard",
  onSelectTab,
  health = null,
  isBackendOnline = true,
}) {
  return (
    <aside className="sidebar" style={{ userSelect: "none", WebkitUserSelect: "none" }}>
      <div
        className="brand"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "16px",
          borderBottom: "1px solid rgba(211, 212, 192, 0.12)",
        }}
      >
        <div
          style={{
            background: "rgba(10, 41, 71, 0.8)",
            borderRadius: "10px",
            padding: "4px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "1px solid rgba(34, 197, 94, 0.3)",
          }}
        >
          <MeterLogo size={34} glowing={true} />
        </div>
        <div>
          <div
            style={{
              fontSize: "1.08rem",
              fontWeight: "700",
              color: "#FFFFFF",
              letterSpacing: "0.5px",
              lineHeight: 1.2,
            }}
          >
            MeterGuard AI
          </div>
          <div
            style={{
              fontSize: "0.68rem",
              color: "#4ADE80",
              textTransform: "uppercase",
              letterSpacing: "1.2px",
              fontWeight: "600",
              marginTop: "2px",
            }}
          >
            TAMPERING DETECTOR
          </div>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Main Navigation">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${isActive ? "active" : ""}`}
              onClick={() => onSelectTab && onSelectTab(item.id)}
              style={{
                width: "100%",
                background: isActive
                  ? "linear-gradient(90deg, rgba(139, 94, 60, 0.82), rgba(139, 94, 60, 0.36))"
                  : "transparent",
                border: "none",
                textAlign: "left",
                fontFamily: "inherit",
                cursor: "pointer",
                userSelect: "none",
                WebkitUserSelect: "none",
                WebkitTapHighlightColor: "transparent",
                outline: "none",
              }}
              title={item.label}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon size={20} color={isActive ? "var(--cream)" : "var(--sage)"} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-bottom">
        <div className="backend-card">
          <div className="backend-status">
            <span
              className={
                !isBackendOnline
                  ? "offline-dot"
                  : health?.database_connected === false
                  ? "live-dot"
                  : "live-dot"
              }
              style={{
                background:
                  !isBackendOnline
                    ? "#EF4444"
                    : health?.database_connected === false
                    ? "#F59E0B"
                    : "#22C55E",
              }}
            ></span>
            {!isBackendOnline
              ? "Backend Offline"
              : health?.database_connected === false
              ? "API Online • DB Offline"
              : "Backend & DB Online"}
          </div>
          <div className="backend-text">
            {!isBackendOnline
              ? "FastAPI & MySQL Disconnected"
              : health?.database_connected === false
              ? "FastAPI Active • MySQL Disconnected"
              : "FastAPI • MySQL Connected"}
          </div>
        </div>

        <div className="sidebar-footer-text">
          MeterGuard AI Monitoring v1.0
        </div>
      </div>
    </aside>
  );
}
