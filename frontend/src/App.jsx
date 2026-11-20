import { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import MeterLogo from "./components/MeterLogo";
import DashboardPage from "./pages/DashboardPage";
import LiveMonitoringPage from "./pages/LiveMonitoringPage";
import AiDetectionPage from "./pages/AiDetectionPage";
import MeterLocationsPage from "./pages/MeterLocationsPage";
import MeterNetworkPage from "./pages/MeterNetworkPage";
import AlertsLogsPage from "./pages/AlertsLogsPage";
import SettingsPage from "./pages/SettingsPage";
import { fetchDashboard } from "./services/api";
import { Activity } from "lucide-react";
import "./App.css";

const backgroundImage = "/background.jpg";

const VALID_TABS = [
  "dashboard",
  "live-monitoring",
  "ai-detection",
  "meter-locations",
  "meter-network",
  "alerts-logs",
  "settings",
];

function getTabFromHash() {
  const hash = window.location.hash.replace(/^#\/?/, "").toLowerCase();
  return VALID_TABS.includes(hash) ? hash : "dashboard";
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [selectedMeter, setSelectedMeter] = useState("M001");
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [currentTab, setCurrentTab] = useState(getTabFromHash);
  const [pollingInterval, setPollingInterval] = useState(() => {
    return Number(localStorage.getItem("meterguard_interval")) || 1000;
  });

  // Keep navigation in sync with browser URL hash
  useEffect(() => {
    const onHashChange = () => {
      setCurrentTab(getTabFromHash());
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const handleTabChange = useCallback((tabId) => {
    setCurrentTab(tabId);
    window.location.hash = `#/${tabId}`;
  }, []);

  // Poll dashboard telemetry
  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const data = await fetchDashboard();
        if (isMounted) {
          setDashboard(data);
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
    // If backend is not connected and user is not on settings, show loading screen
    if (!dashboard && currentTab !== "settings") {
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
                onClick={() => handleTabChange("settings")}
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
      case "meter-locations":
        return (
          <MeterLocationsPage
            dashboard={dashboard}
            selectedMeter={selectedMeter}
            setSelectedMeter={setSelectedMeter}
            lastUpdate={lastUpdate}
          />
        );
      case "meter-network":
        return (
          <MeterNetworkPage
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
      case "settings":
        return (
          <SettingsPage
            lastUpdate={lastUpdate}
            pollingInterval={pollingInterval}
            setPollingInterval={setPollingInterval}
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
      <Sidebar currentTab={currentTab} onSelectTab={handleTabChange} />

      {/* ACTIVE PAGE CONTENT */}
      {renderContent()}
    </div>
  );
}

export default App;
