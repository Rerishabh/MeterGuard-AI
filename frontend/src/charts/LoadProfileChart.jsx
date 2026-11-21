import { Activity, Clock } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export default function LoadProfileChart({ consumptionData = [] }) {
  const hasData = Array.isArray(consumptionData) && consumptionData.length > 0;

  return (
    <section className="panel consumption-panel">
      <div className="panel-header">
        <div>
          <h2>30-Day Consumption Profile</h2>
          <p>Model 1 prototype daily consumption history (kWh)</p>
        </div>
        <Activity size={23} />
      </div>

      <div className="large-chart">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={consumptionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(211, 212, 192, 0.15)" />
              <XAxis dataKey="day" interval={1} stroke="var(--sage)" />
              <YAxis stroke="var(--sage)" unit=" kWh" />
              <Tooltip
                contentStyle={{
                  background: "rgba(6, 28, 49, 0.95)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  color: "#FFFFFF",
                }}
                formatter={(val) => [`${Number(val).toFixed(2)} kWh`, "Daily Consumption"]}
              />
              <Bar
                dataKey="consumption"
                name="Consumption"
                fill="#8B5E3C"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div
            className="empty-chart"
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              padding: "30px 20px",
              textAlign: "center",
              background: "rgba(6, 28, 49, 0.4)",
              borderRadius: "8px",
              border: "1px dashed rgba(211, 212, 192, 0.2)",
            }}
          >
            <Clock size={36} color="var(--sage)" style={{ marginBottom: "12px" }} />
            <strong style={{ color: "var(--cream)", fontSize: "14px", marginBottom: "6px" }}>
              Awaiting 30-Day Daily Consumption Sequence
            </strong>
            <p style={{ color: "var(--sage)", fontSize: "12px", maxWidth: "440px", margin: 0, lineHeight: "1.5" }}>
              Model 1 (Isolation Forest) requires 30 daily kWh observations to construct statistical baseline features (mean, median, trend, spike ratio). Ingest a sequence via the Tampering Simulator or streaming telemetry to display the load profile.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
