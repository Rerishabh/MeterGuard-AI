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
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="reading" />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="power"
                name="Power (W)"
                stroke="#D3D4C0"
                strokeWidth={3}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-chart">Waiting for live readings...</div>
        )}
      </div>
    </div>
  );
}
