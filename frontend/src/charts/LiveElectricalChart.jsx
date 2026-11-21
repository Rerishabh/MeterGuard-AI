import { Activity } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export default function LiveElectricalChart({
  voltage = 0,
  current = 0,
  power = 0,
  liveChartData = [],
}) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>Live Electrical Readings</h2>
          <p>Real-time sensor monitoring</p>
        </div>
        <Activity size={23} />
      </div>

      <div className="live-stats">
        <div>
          <span>VOLTAGE</span>
          <strong>{Number(voltage).toFixed(1)} V</strong>
        </div>

        <div>
          <span>CURRENT</span>
          <strong>{Number(current).toFixed(3)} A</strong>
        </div>

        <div>
          <span>POWER</span>
          <strong>{Number(power).toFixed(1)} W</strong>
        </div>
      </div>

      <div className="chart-container">
        {liveChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={liveChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(211, 212, 192, 0.1)" />
              <XAxis dataKey="reading" stroke="var(--sage)" fontSize={11} />
              <YAxis
                stroke="var(--sage)"
                fontSize={11}
                unit=" W"
                domain={[(dataMin) => Math.max(0, Math.floor(dataMin - 5)), (dataMax) => Math.ceil(dataMax + 5)]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(6, 28, 49, 0.95)",
                  border: "1px solid rgba(211, 212, 192, 0.2)",
                  borderRadius: "8px",
                  color: "#FFFFFF",
                }}
                formatter={(val) => [`${Number(val).toFixed(2)} W`, "Power"]}
                labelFormatter={(label) => `Reading #${label}`}
              />
              <Line
                type="monotone"
                dataKey="power"
                name="Power (W)"
                stroke="#22C55E"
                strokeWidth={2.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div
            style={{
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              color: "var(--sage)",
              textAlign: "center",
              padding: "20px",
            }}
          >
            <Activity size={28} color="var(--sage-dark)" />
            <span style={{ fontSize: "13px", fontWeight: "600", color: "#FFFFFF" }}>
              Awaiting Live Hardware Telemetry
            </span>
            <small style={{ fontSize: "11px", color: "var(--sage-dark)", maxWidth: "340px" }}>
              No live electrical stream frames received for this meter. Start the telemetry stream or replay script to view real-time power fluctuations.
            </small>
          </div>
        )}
      </div>
    </div>
  );
}
