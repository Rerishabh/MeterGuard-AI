import { useEffect } from "react";
import {
  MapPin,
  Clock3,
  Navigation,
  Radio,
  Layers,
} from "lucide-react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getStatusType, getStatusText } from "../services/statusHelpers";

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

export default function MeterLocationsPage({
  dashboard,
  selectedMeter,
  setSelectedMeter,
  lastUpdate,
}) {
  const meters = dashboard?.meters || [];
  let meter = meters.find((m) => m.meter_id === selectedMeter) || meters[0] || {};

  // Filter meters with real coordinates
  const mappedMeters = meters.filter(
    (m) =>
      m.location &&
      m.location.latitude !== null &&
      m.location.latitude !== undefined &&
      m.location.longitude !== null &&
      m.location.longitude !== undefined
  );

  const unmappedMeters = meters.filter(
    (m) =>
      !m.location ||
      m.location.latitude === null ||
      m.location.latitude === undefined ||
      m.location.longitude === null ||
      m.location.longitude === undefined
  );

  const curLat = meter?.location?.latitude;
  const curLng = meter?.location?.longitude;
  const defaultCenter =
    curLat !== null && curLat !== undefined && curLng !== null && curLng !== undefined
      ? [curLat, curLng]
      : mappedMeters.length > 0
      ? [mappedMeters[0].location.latitude, mappedMeters[0].location.longitude]
      : [21.2514, 81.6296];

  return (
    <main className="main">
      {/* TOPBAR */}
      <header className="topbar">
        <div>
          <div className="title-row">
            <MapPin size={28} color="#22C55E" />
            <h1>Meter GIS Locations</h1>
          </div>
          <p>Spatial distribution grid mapping & physical tamper surveillance</p>
        </div>

        <div className="topbar-right">
          <div className="live-badge">
            <span className="live-dot"></span>
            GPS SYNCED
          </div>

          <div className="time-display">
            <Clock3 size={17} />
            {lastUpdate ? lastUpdate.toLocaleTimeString() : "--"}
          </div>
        </div>
      </header>

      {/* SUMMARY STATS BAR */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "20px",
        }}
      >
        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "1px" }}>
            Total Registered Meters
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#FFFFFF", marginTop: "4px" }}>
            {meters.length}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "1px" }}>
            Mapped with GPS Coordinates
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#22C55E", marginTop: "4px" }}>
            {mappedMeters.length}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "1px" }}>
            Current Target Focus
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#F3E4C9", marginTop: "4px" }}>
            {meter.meter_id || "--"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px" }}>
          <div style={{ fontSize: "11px", color: "var(--sage)", textTransform: "uppercase", letterSpacing: "1px" }}>
            Target Coordinates
          </div>
          <div style={{ fontSize: "1.1rem", fontWeight: "600", color: "#FFFFFF", marginTop: "8px" }}>
            {curLat && curLng ? `${curLat.toFixed(4)}°, ${curLng.toFixed(4)}°` : "No GPS Fixed"}
          </div>
        </div>
      </div>

      {/* FULL MAP + SIDE PANEL */}
      <section className="two-column" style={{ gridTemplateColumns: "1fr 340px", alignItems: "stretch" }}>
        {/* LEAFLET MAP PANEL */}
        <div className="panel" style={{ minHeight: "520px", display: "flex", flexDirection: "column" }}>
          <div className="panel-header">
            <div>
              <h2>Interactive Grid GIS Map</h2>
              <p>Click on any marker to inspect telemetry and focus coverage</p>
            </div>
            <Navigation size={22} color="#22C55E" />
          </div>

          <div className="map-wrapper" style={{ flex: 1, minHeight: "440px" }}>
            <MapContainer
              center={defaultCenter}
              zoom={13}
              scrollWheelZoom={true}
              className="map"
              style={{ width: "100%", height: "100%", minHeight: "440px", borderRadius: "10px" }}
            >
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapController meter={meter} />

              {mappedMeters.map((item) => {
                const itemLocation = item.location;
                const type = getStatusType(item);
                let markerColor = "#22C55E";
                if (type === "fault") markerColor = "#EF4444";
                else if (type === "suspicious") markerColor = "#8B5E3C";

                const isSelected = item.meter_id === meter.meter_id;

                return (
                  <CircleMarker
                    key={item.meter_id}
                    center={[itemLocation.latitude, itemLocation.longitude]}
                    radius={isSelected ? 12 : 8}
                    pathOptions={{
                      color: markerColor,
                      fillColor: markerColor,
                      fillOpacity: isSelected ? 0.95 : 0.75,
                      weight: isSelected ? 4 : 2,
                    }}
                    eventHandlers={{
                      click: () => setSelectedMeter(item.meter_id),
                    }}
                  >
                    <Popup>
                      <div className="map-popup">
                        <strong>Meter {item.meter_id}</strong>
                        <span>Status: {getStatusText(item)}</span>
                        {item.location?.location_name && (
                          <small>Zone: {item.location.location_name}</small>
                        )}
                        <small>Lat: {itemLocation.latitude.toFixed(4)}</small>
                        <small>Lng: {itemLocation.longitude.toFixed(4)}</small>
                        <small>{item.online !== false ? "● Online" : "● Offline"}</small>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </MapContainer>

            <div className="map-legend">
              <span>
                <i className="legend-normal"></i>
                Normal Operating
              </span>
              <span>
                <i className="legend-warning"></i>
                Suspicious Load
              </span>
              <span>
                <i className="legend-fault"></i>
                Hardware Tamper
              </span>
            </div>
          </div>
        </div>

        {/* METERS LOCATION LIST SIDE PANEL */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <div className="panel-header">
            <div>
              <h2>Grid Node List</h2>
              <p>Meters with valid spatial telemetry</p>
            </div>
            <Layers size={20} color="#22C55E" />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "14px", overflowY: "auto", maxHeight: "450px" }}>
            {mappedMeters.map((item) => {
              const type = getStatusType(item);
              const isSelected = item.meter_id === meter.meter_id;

              return (
                <button
                  key={item.meter_id}
                  type="button"
                  onClick={() => setSelectedMeter(item.meter_id)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px",
                    borderRadius: "8px",
                    background: isSelected ? "rgba(139, 94, 60, 0.4)" : "rgba(6, 28, 49, 0.6)",
                    border: isSelected ? "1.5px solid var(--cream)" : "1px solid rgba(211, 212, 192, 0.15)",
                    cursor: "pointer",
                    textAlign: "left",
                    color: "inherit",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Radio size={14} color="#22C55E" />
                      <strong style={{ color: "#FFFFFF", fontSize: "14px" }}>{item.meter_id}</strong>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--sage)", marginTop: "4px" }}>
                      {item.location?.location_name || "Distribution Zone"}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--sage-dark)", marginTop: "2px" }}>
                      {item.location.latitude.toFixed(4)}°, {item.location.longitude.toFixed(4)}°
                    </div>
                  </div>

                  <div style={{ textAlign: "right" }}>
                    <span className={`network-status ${type}`} style={{ fontSize: "11px", padding: "3px 8px" }}>
                      {getStatusText(item)}
                    </span>
                    <div style={{ fontSize: "10px", color: "var(--sage-dark)", marginTop: "6px" }}>
                      {item.online !== false ? "● Online" : "● Offline"}
                    </div>
                  </div>
                </button>
              );
            })}

            {unmappedMeters.length > 0 && (
              <div style={{ marginTop: "12px", padding: "10px", background: "rgba(10, 41, 71, 0.4)", borderRadius: "6px", fontSize: "11px", color: "var(--sage)" }}>
                <strong>{unmappedMeters.length} meter(s)</strong> awaiting GPS fix coordinates from field telemetry.
              </div>
            )}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer>
        <span>MeterGuard AI • Spatial GIS Mapping</span>
        <span>OpenStreetMap Leaflet Integration • Verified Coordinates Only</span>
      </footer>
    </main>
  );
}
