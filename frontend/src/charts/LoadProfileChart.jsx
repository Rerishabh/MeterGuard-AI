import { Activity } from "lucide-react";
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
  return (
    <section className="panel consumption-panel">
      <div className="panel-header">
        <div>
          <h2>30-Day Consumption Profile</h2>
          <p>Model 1 prototype consumption history</p>
        </div>
        <Activity size={23} />
      </div>

      <div className="large-chart">
        {consumptionData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={consumptionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" interval={1} />
              <YAxis />
              <Tooltip />
              <Bar
                dataKey="consumption"
                name="Consumption"
                fill="#8B5E3C"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-chart">
            Model 1 is collecting consumption history...
          </div>
        )}
      </div>
    </section>
  );
}
