import { Radio } from "lucide-react";

export default function NetworkDifferentialCard({ readings = {}, statusType = "normal" }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>Simulated Line Monitoring</h2>
          <p>T1 / T2 / House simulated channel values</p>
        </div>
        <Radio size={23} />
      </div>

      <div className="transmission-table">
        <div className="table-row table-head">
          <span>POINT</span>
          <span>CURRENT (ADC)</span>
          <span>VOLTAGE (V)</span>
          <span>STATUS</span>
        </div>

        <div className="table-row">
          <strong>T1</strong>
          <span>{readings.T1_CS !== undefined && readings.T1_CS !== null ? readings.T1_CS : "--"}</span>
          <span>{readings.T1_VS !== undefined && readings.T1_VS !== null ? readings.T1_VS : "--"}</span>
          <span className="normal-text">NORMAL</span>
        </div>

        <div className="table-row">
          <strong>T2</strong>
          <span>{readings.T2_CS !== undefined && readings.T2_CS !== null ? readings.T2_CS : "--"}</span>
          <span>{readings.T2_VS !== undefined && readings.T2_VS !== null ? readings.T2_VS : "--"}</span>
          <span className="normal-text">NORMAL</span>
        </div>

        <div className="table-row">
          <strong>H1</strong>
          <span>{readings.H1_CS !== undefined && readings.H1_CS !== null ? readings.H1_CS : "--"}</span>
          <span>{readings.H1_VS !== undefined && readings.H1_VS !== null ? readings.H1_VS : "--"}</span>
          <span className={statusType === "fault" ? "fault-text" : "normal-text"}>
            {statusType === "fault" ? "FAULT" : "NORMAL"}
          </span>
        </div>
      </div>
    </div>
  );
}
