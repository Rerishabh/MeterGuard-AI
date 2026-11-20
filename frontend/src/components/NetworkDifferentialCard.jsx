import { Radio } from "lucide-react";

export default function NetworkDifferentialCard({ readings = {}, statusType = "normal" }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>Transmission Monitoring</h2>
          <p>T1 / T2 / House sensor values</p>
        </div>
        <Radio size={23} />
      </div>

      <div className="transmission-table">
        <div className="table-row table-head">
          <span>POINT</span>
          <span>CURRENT</span>
          <span>VOLTAGE</span>
          <span>STATUS</span>
        </div>

        <div className="table-row">
          <strong>T1</strong>
          <span>{readings.T1_CS ?? 0}</span>
          <span>{readings.T1_VS ?? 0}</span>
          <span className="normal-text">NORMAL</span>
        </div>

        <div className="table-row">
          <strong>T2</strong>
          <span>{readings.T2_CS ?? 0}</span>
          <span>{readings.T2_VS ?? 0}</span>
          <span className="normal-text">NORMAL</span>
        </div>

        <div className="table-row">
          <strong>H1</strong>
          <span>{readings.H1_CS ?? 0}</span>
          <span>{readings.H1_VS ?? 0}</span>
          <span className={statusType === "fault" ? "fault-text" : "normal-text"}>
            {statusType === "fault" ? "FAULT" : "NORMAL"}
          </span>
        </div>
      </div>
    </div>
  );
}
