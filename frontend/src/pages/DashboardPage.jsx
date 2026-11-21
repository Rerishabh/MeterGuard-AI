import { useEffect, useState } from "react";
import {
  Clock3,
  Wifi,
  WifiOff,
  Cpu,
  MapPin,
  Radio,
  Network,
  Activity,
} from "lucide-react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

import MeterLogo from "../components/MeterLogo";
import MeterSummaryCard from "../components/MeterSummaryCard";
import NetworkDifferentialCard from "../components/NetworkDifferentialCard";
import TamperingSimulatorCard from "../components/TamperingSimulatorCard";
import InvestigationBriefPanel from "../components/InvestigationBriefPanel";
import LiveElectricalChart from "../charts/LiveElectricalChart";
import LoadProfileChart from "../charts/LoadProfileChart";
import { getStatusType, getStatusText } from "../services/statusHelpers";

const backgroundImage = "/background.jpg";

function MapController({ meter }) {
  const map = useMap();

  useEffect(() => {
    const latitude = meter?.location?.latitude;
    const longitude = meter?.location?.longitude;

    if (
      latitude !== null &&
      latitude !== undefined &&
      longitude !== null &&
      longitude !== undefined
    ) {
      map.flyTo([latitude, longitude], 13, {
        duration: 0.8,
      });
    }
  }, [meter, map]);

  return null;
}

export default function DashboardPage({
  dashboard,
  selectedMeter,
  setSelectedMeter,
  lastUpdate,
  error,
}) {
  const [latestSimReport, setLatestSimReport] = useState(null);

  /* =======================================================
     LOADING SCREEN (NO BACKEND CONNECTION YET)
  ======================================================= */
  if (!dashboard) {
    return (
      <div
        className="loading-screen"
        style={{
          backgroundImage: `linear-gradient(
            rgba(10,41,71,.76),
            rgba(6,28,49,.96)
          ), url(${backgroundImage})`,
        }}
      >
        <div className="loading-card">
          <div className="loading-spinner">
            <Activity size={32} />
          </div>

          <h2>MeterGuard AI</h2>
          <p>Connecting to tampering detection backend...</p>

          {error && <div className="error-box">{error}</div>}
        </div>
      </div>
    );
  }

  /* =======================================================
     WAITING FOR TELEMETRY
  ======================================================= */
  const meters = dashboard.meters || [];

  if (meters.length === 0) {
    return (
      <div className="loading-screen">
        <div className="loading-card">
          <Radio size={42} />

          <h2>Waiting for Meter Telemetry</h2>
          <p>No meter readings received yet.</p>
          <small style={{ color: "var(--sage)", marginTop: "12px", display: "block" }}>
            Run the hardware simulator: <code>python backend/replay_hardware_dataset.py --loop</code>
          </small>
        </div>
      </div>
    );
  }

  /* =======================================================
     RESOLVE SELECTED METER DATA
  ======================================================= */
  let meter = meters.find((item) => item.meter_id === selectedMeter);
  if (!meter) {
    meter = meters[0];
  }

  const readings = meter.readings || {};
  const electrical = meter.electrical || {};
  const model1 = meter.model1 || {};
  const model2 = meter.model2 || {};
  const lstm = meter.lstm || {};
  const decision = meter.decision || {};
  const liveHistory = meter.live_history || [];
  const location = meter.location || {};

  const voltage = Number(electrical.voltage_V || 0);
  const current = Number(electrical.current_A || 0);
  const power = Number(electrical.power_W || 0);

  const model1Prediction = model1.prediction || "WAITING";
  const model2Prediction = model2.prediction || "WAITING";
  const lstmStatus = lstm.status || "WAITING";
  const lstmError =
    lstm.reconstruction_error !== null && lstm.reconstruction_error !== undefined
      ? Number(lstm.reconstruction_error).toFixed(5)
      : null;
  const lstmThreshold =
    lstm.threshold !== null && lstm.threshold !== undefined
      ? Number(lstm.threshold).toFixed(5)
      : null;
  const finalStatus = decision.final_status || "MONITORING";
  const priority = decision.priority || "LOW";
  const faultType = decision.fault_type || model2.fault_type || null;
  const statusType = getStatusType(meter);

  const liveChartData = liveHistory.map((item, index) => ({
    reading: index + 1,
    power: Number(item.power_W || 0),
    current: Number(item.current_A || 0),
    voltage: Number(item.voltage_V || 0),
  }));

  const consumptionHistory = model1.consumption_history || meter.consumption_history || [];
  const consumptionData = consumptionHistory.map((value, index) => ({
    day: `D${index + 1}`,
    consumption: Number(value),
  }));

  const connectionState = meter.connection_state || (meter.online !== false ? "ONLINE" : "OFFLINE");
  const isOnline = connectionState === "ONLINE";
  const isStale = connectionState === "STALE";

  const latitude = location.latitude;
  const longitude = location.longitude;
  const mapCenter =
    latitude !== null &&
    latitude !== undefined &&
    longitude !== null &&
    longitude !== undefined
      ? [latitude, longitude]
      : [21.2514, 81.6296];

  return (
    <main className="main">
      {/* TOPBAR */}
      <header className="topbar">
        <div>
          <div className="title-row">
            <MeterLogo size={32} />
            <h1>MeterGuard AI Dashboard</h1>
          </div>
          <p>Real-time intelligent utility meter tampering detection</p>
        </div>

          <div className="topbar-right">
            {isOnline ? (
              <div className="live-badge">
                <span className="live-dot"></span>
                LIVE TELEMETRY
              </div>
            ) : isStale ? (
              <div
                className="live-badge"
                style={{
                  background: "rgba(245, 158, 11, 0.2)",
                  border: "1px solid #F59E0B",
                  color: "#FCD34D",
                }}
              >
                <span style={{ background: "#F59E0B", width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" }}></span>
                STALE TELEMETRY
              </div>
            ) : (
              <div
                className="live-badge"
                style={{
                  background: "rgba(239, 68, 68, 0.2)",
                  border: "1px solid #EF4444",
                  color: "#FCA5A5",
                }}
              >
                <span className="offline-dot" style={{ background: "#EF4444", width: "8px", height: "8px", borderRadius: "50%", display: "inline-block" }}></span>
                METER OFFLINE
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
              value={meter.meter_id}
              onChange={(e) => setSelectedMeter(e.target.value)}
            >
              {meters.map((item) => (
                <option key={item.meter_id} value={item.meter_id}>
                  {item.meter_id} {item.is_simulated ? "(Simulated)" : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="connection-status">
            {isOnline ? (
              <>
                <Wifi size={18} color="#22C55E" />
                Meter {meter.meter_id}
                <span className="live-dot"></span>
                <span style={{ color: "#4ADE80", fontWeight: "600" }}>ONLINE</span>
              </>
            ) : isStale ? (
              <>
                <Wifi size={18} color="#F59E0B" />
                Meter {meter.meter_id}
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#F59E0B", display: "inline-block" }}></span>
                <span style={{ color: "#FCD34D", fontWeight: "600" }}>STALE</span>
              </>
            ) : (
              <>
                <WifiOff size={18} color="#EF4444" />
                Meter {meter.meter_id}
                <span className="offline-dot"></span>
                <span style={{ color: "#FCA5A5", fontWeight: "600" }}>OFFLINE</span>
              </>
            )}
          </div>
        </section>

        {/* ELECTRICAL & STATUS METRICS */}
        <MeterSummaryCard
          voltage={voltage}
          current={current}
          power={power}
          statusType={statusType}
          finalStatus={finalStatus}
          priority={priority}
          faultType={faultType}
        />

        {/* TWO-COLUMN: LIVE READINGS + AI DETECTION */}
        <section className="two-column">
          <LiveElectricalChart
            voltage={voltage}
            current={current}
            power={power}
            liveChartData={liveChartData}
          />

          {/* AI DETECTION PANEL */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>AI Detection</h2>
                <p>Multi-model intelligent analysis</p>
              </div>
              <Cpu size={23} />
            </div>

            <div className="ai-results">
              {/* MODEL 1 */}
              <div className="ai-row">
                <div className="ai-name">
                  <div className="ai-number">01</div>
                  <div>
                    <strong>Consumption Model</strong>
                    <small>Isolation Forest baseline</small>
                  </div>
                </div>

                <span className={`prediction ${model1Prediction.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
                  {model1Prediction}
                </span>
              </div>

              {/* MODEL 2 */}
              <div className="ai-row">
                <div className="ai-name">
                  <div className="ai-number">02</div>
                  <div>
                    <strong>Fault Detection Model</strong>
                    <small>Real-time transformer differential</small>
                  </div>
                </div>

                <span className={`prediction ${model2Prediction.toLowerCase()}`}>
                  {model2Prediction}
                </span>
              </div>

              {/* MODEL 3 */}
              <div className="ai-row">
                <div className="ai-name">
                  <div className="ai-number">03</div>
                  <div>
                    <strong>LSTM Autoencoder</strong>
                    <small>
                      {lstmError !== null && lstmThreshold !== null
                        ? `MSE: ${lstmError} | Thresh: ${lstmThreshold}`
                        : "Time-series sequence reconstruction"}
                    </small>
                  </div>
                </div>

                <span
                  className={`prediction ${
                    lstmStatus === "NORMAL"
                      ? "normal"
                      : lstmStatus === "SUSPICIOUS"
                      ? "suspicious"
                      : "waiting"
                  }`}
                  title={lstm.message || lstmStatus}
                >
                  {lstmStatus}
                </span>
              </div>


              {/* FAULT DETAILS (IF ACTIVE) */}
              {faultType && (
                <div className="fault-details">
                  <div>
                    <span>DETECTED FAULT</span>
                    <strong>{faultType.replace("FAULT_", "")}</strong>
                  </div>
                  <div>
                    <span>DETECTED BY</span>
                    <strong>MODEL 2</strong>
                  </div>
                  <div>
                    <span>PRIORITY</span>
                    <strong>{priority}</strong>
                  </div>
                </div>
              )}

              {/* FINAL DECISION BADGE */}
              <div className={`final-alert ${statusType}`}>
                <div>
                  <span>FINAL DECISION</span>
                  <strong>{finalStatus}</strong>
                  {faultType && (
                    <small>Fault Type: {faultType.replace("FAULT_", "")}</small>
                  )}
                </div>
                <div className="priority">{priority}</div>
              </div>

              <div className="decision-message">
                {decision.message || "System monitoring active."}
              </div>
            </div>
          </div>
        </section>

        {/* 30-DAY CONSUMPTION PROFILE */}
        <LoadProfileChart consumptionData={consumptionData} />

        {/* PHASE 3B: TAMPERING SIMULATOR BENCH */}
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

        {/* PHASE 3B: FORENSIC INVESTIGATION BRIEF & AUDIT PANEL */}
        <InvestigationBriefPanel
          selectedMeterId={meter.meter_id}
          latestReportFromSimulation={latestSimReport}
        />

        {/* TRANSMISSION & GIS MAP */}
        <section className="two-column bottom-section">
          <NetworkDifferentialCard
            readings={readings}
            statusType={statusType}
          />

          {/* GIS MAP PANEL */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Meter Location</h2>
                <p>Geographic monitoring</p>
              </div>
              <MapPin size={23} />
            </div>

            <div className="map-wrapper">
              <MapContainer
                center={mapCenter}
                zoom={13}
                scrollWheelZoom={true}
                className="map"
              >
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <MapController meter={meter} />

                {meters.map((item) => {
                  const itemLocation = item.location;
                  if (
                    !itemLocation ||
                    itemLocation.latitude === null ||
                    itemLocation.longitude === null
                  ) {
                    return null;
                  }

                  const type = getStatusType(item);
                  let markerColor = "#22C55E";
                  if (type === "fault") markerColor = "#EF4444";
                  else if (type === "suspicious") markerColor = "#8B5E3C";

                  return (
                    <CircleMarker
                      key={item.meter_id}
                      center={[itemLocation.latitude, itemLocation.longitude]}
                      radius={item.meter_id === meter.meter_id ? 11 : 8}
                      pathOptions={{
                        color: markerColor,
                        fillColor: markerColor,
                        fillOpacity: 0.85,
                        weight: 3,
                      }}
                      eventHandlers={{
                        click: () => setSelectedMeter(item.meter_id),
                      }}
                    >
                      <Popup>
                        <div className="map-popup">
                          <strong>{item.meter_id}</strong>
                          <span>{getStatusText(item)}</span>
                          {item?.decision?.fault_type && (
                            <small>
                              Fault: {item.decision.fault_type.replace("FAULT_", "")}
                            </small>
                          )}
                          <small>{item.online !== false ? "Online" : "Offline"}</small>
                        </div>
                      </Popup>
                    </CircleMarker>
                  );
                })}
              </MapContainer>

              <div className="map-legend">
                <span>
                  <i className="legend-normal"></i>
                  Normal
                </span>
                <span>
                  <i className="legend-warning"></i>
                  Suspicious
                </span>
                <span>
                  <i className="legend-fault"></i>
                  Fault
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* CONNECTED METERS GRID */}
        <section className="panel network-panel">
          <div className="panel-header">
            <div>
              <h2>Connected Meter Network</h2>
              <p>Smart meters connected to the backend</p>
            </div>
            <Network size={23} />
          </div>

          <div className="network-grid">
            {meters.map((item) => {
              const type = getStatusType(item);
              const fault = item?.decision?.fault_type;

              return (
                <button
                  key={item.meter_id}
                  className={`network-meter ${
                    item.meter_id === meter.meter_id ? "selected" : ""
                  }`}
                  onClick={() => setSelectedMeter(item.meter_id)}
                >
                  <div className="network-top">
                    <div>
                      <Radio size={17} />
                      <strong>{item.meter_id}</strong>
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
                      <strong>
                        {Number(item?.electrical?.power_W || 0).toFixed(1)} W
                      </strong>
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

                  <div className="network-bottom">
                    <span>{item.online !== false ? "● Online" : "● Offline"}</span>
                    <span>Priority: {item?.decision?.priority || "LOW"}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* FOOTER */}
        <footer>
          <span>MeterGuard AI • Utility Meter Tampering Detector</span>
          <span>ESP32 • AI • IoT • Real-Time Monitoring</span>
        </footer>
      </main>
  );
}
