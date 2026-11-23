import { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import MeterLogo from "./components/MeterLogo";
import DashboardPage from "./pages/DashboardPage";
import LiveMonitoringPage from "./pages/LiveMonitoringPage";
import AiDetectionPage from "./pages/AiDetectionPage";
import AlertsLogsPage from "./pages/AlertsLogsPage";
import SettingsPage from "./pages/SettingsPage";
import { fetchDashboard, fetchHealth } from "./services/api";
import { Activity, X } from "lucide-react";
import "./App.css";

const backgroundImage = "/tower-background.webp";

const VALID_TABS = [
  "dashboard",
  "live-monitoring",
  "ai-detection",
  "alerts-logs",
];

function getTabFromHash() {
  const hash = window.location.hash.replace(/^#\/?/, "").toLowerCase();
  return VALID_TABS.includes(hash) ? hash : "dashboard";
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [health, setHealth] = useState(null);
  const [selectedMeter, setSelectedMeter] = useState("M001");
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [currentTab, setCurrentTab] = useState(getTabFromHash);
  const [showSettings, setShowSettings] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(() => {
    return Number(localStorage.getItem("meterguard_interval")) || 1000;
  });

  // Keep navigation in sync with browser URL hash
  useEffect(() => {
    const onHashChange = () => {
      const tab = getTabFromHash();
      setCurrentTab(tab);
      setShowSettings(false);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const handleTabChange = useCallback((tabId) => {
    setCurrentTab(tabId);
    setShowSettings(false);
    window.location.hash = `#/${tabId}`;
  }, []);

  const handleOpenSettings = useCallback(() => {
    setShowSettings(true);
  }, []);

  const handleCloseSettings = useCallback(() => {
    setShowSettings(false);
  }, []);

  // Poll dashboard telemetry
  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const [data, healthData] = await Promise.all([
          fetchDashboard(),
          fetchHealth().catch(() => null),
        ]);
        if (isMounted) {
          setDashboard(data);
          if (healthData) {
            setHealth(healthData);
          }
          setError(null);
          setLastUpdate(new Date());

          // If current selected meter not in returned list, select first available
          if (data?.meters?.length > 0) {
            setSelectedMeter((prev) => {
              const exists = data.meters.some((m) => m.meter_id === prev);
              return exists ? prev : data.meters[0].meter_id;
            });
          }
        }
      } catch (err) {
        console.error("Dashboard fetch error:", err);
        if (isMounted) {
          setError("Backend connection lost. Ensure FastAPI server is running on port 5000.");
        }
      }
    }

    loadData();
    const interval = setInterval(loadData, pollingInterval);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [pollingInterval]);

  const renderContent = () => {
    // If backend is not connected and settings not open, show loading screen
    if (!dashboard && !showSettings) {
      return (
        <main className="main" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
          <div className="loading-card" style={{ maxWidth: "440px", textAlign: "center" }}>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}>
              <MeterLogo size={56} glowing={true} />
            </div>
            <h2>MeterGuard AI</h2>
            <p>Connecting to tampering detection backend (FastAPI / MySQL)...</p>

            <div style={{ display: "flex", justifyContent: "center", margin: "16px 0" }}>
              <div className="loading-spinner">
                <Activity size={28} color="#22C55E" />
              </div>
            </div>

            {error && (
              <div className="error-box" style={{ marginTop: "12px", textAlign: "left" }}>
                {error}
              </div>
            )}

            <div style={{ marginTop: "16px" }}>
              <button
                type="button"
                onClick={handleOpenSettings}
                style={{
                  background: "rgba(10, 41, 71, 0.8)",
                  border: "1px solid rgba(211, 212, 192, 0.3)",
                  color: "var(--cream)",
                  padding: "8px 16px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                Inspect Connection Settings
              </button>
            </div>
          </div>
        </main>
      );
    }

    switch (currentTab) {
      case "live-monitoring":
        return (
          <LiveMonitoringPage
            dashboard={dashboard}
            selectedMeter={selectedMeter}
            setSelectedMeter={setSelectedMeter}
            lastUpdate={lastUpdate}
          />
        );
      case "ai-detection":
        return (
          <AiDetectionPage
            dashboard={dashboard}
            selectedMeter={selectedMeter}
            setSelectedMeter={setSelectedMeter}
            lastUpdate={lastUpdate}
          />
        );
      case "alerts-logs":
        return (
          <AlertsLogsPage
            dashboard={dashboard}
            selectedMeter={selectedMeter}
            setSelectedMeter={setSelectedMeter}
            lastUpdate={lastUpdate}
          />
        );
      case "dashboard":
      default:
        return (
          <DashboardPage
            dashboard={dashboard}
            selectedMeter={selectedMeter}
            setSelectedMeter={setSelectedMeter}
            lastUpdate={lastUpdate}
            error={error}
          />
        );
    }
  };

  return (
    <div
      className="app"
      style={{
        "--dashboard-bg": `url(${backgroundImage})`,
      }}
    >
      <div className="background-layer"></div>

      {/* PERSISTENT SIDEBAR NAVIGATION */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={handleTabChange}
        onOpenSettings={handleOpenSettings}
        health={health}
        isBackendOnline={Boolean(dashboard)}
      />

      {/* ACTIVE PAGE CONTENT */}
      {renderContent()}

      {/* SETTINGS OVERLAY PANEL */}
      {showSettings && (
        <div className="settings-overlay">
          {/* Backdrop */}
          <div
            className="settings-backdrop"
            onClick={handleCloseSettings}
            title="Click to close settings"
          />

          {/* Settings Drawer Panel */}
          <div className="settings-drawer">
            {/* Panel close header */}
            <div className="settings-drawer-header">
              <span style={{ color: "var(--cream)", fontWeight: 700, fontSize: "1.05rem", letterSpacing: "0.5px" }}>
                System Settings
              </span>
              <button
                type="button"
                onClick={handleCloseSettings}
                style={{
                  background: "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(211,212,192,0.22)",
                  borderRadius: "6px",
                  color: "var(--cream)",
                  cursor: "pointer",
                  padding: "5px 12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  transition: "background 0.2s, border-color 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(239,68,68,0.2)";
                  e.currentTarget.style.borderColor = "rgba(239,68,68,0.45)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                  e.currentTarget.style.borderColor = "rgba(211,212,192,0.22)";
                }}
              >
                <X size={15} />
                Close
              </button>
            </div>

            {/* Scrollable Content Body */}
            <div className="settings-drawer-body">
              <SettingsPage
                lastUpdate={lastUpdate}
                pollingInterval={pollingInterval}
                setPollingInterval={setPollingInterval}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
