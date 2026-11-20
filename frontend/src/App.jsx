import { useEffect, useState } from "react";
import DashboardPage from "./pages/DashboardPage";
import { fetchDashboard } from "./services/api";
import "./App.css";

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [selectedMeter, setSelectedMeter] = useState("M001");
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const data = await fetchDashboard();
        if (isMounted) {
          setDashboard(data);
          setError(null);
          setLastUpdate(new Date());
        }
      } catch (err) {
        console.error("Dashboard fetch error:", err);
        if (isMounted) {
          setError("Backend connection lost. Ensure Flask server is running on port 5000.");
        }
      }
    }

    loadData();
    const interval = setInterval(loadData, 1000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

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

export default App;
