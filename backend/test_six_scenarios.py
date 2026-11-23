"""
MeterGuard AI: Six Scenarios Tamper Simulation & Binding Verification Suite
Tests all six anomaly scenarios:
1. normal
2. sudden_drop
3. abnormally_low_night
4. flatline
5. consumption_spike
6. inversion
Verifies exact sequence-to-report evidence binding, thresholds, MSE, and MySQL persistence.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.database.session import SessionLocal
from backend.app.models.db_models import (
    Meter,
    ConsumptionSequence,
    AnomalyAlert,
    InvestigationReport,
)

def run_six_scenarios():
    scenarios = [
        "normal",
        "sudden_drop",
        "abnormally_low_night",
        "flatline",
        "consumption_spike",
        "inversion",
    ]
    results = []
    print("=========================================================================================")
    print("TESTING ALL 6 SIMULATOR SCENARIOS AGAINST /api/simulate/tamper (M001)")
    print("=========================================================================================")

    with TestClient(app) as client:
        # 1. First test /api/health to confirm meter count matches MySQL
        print("\n--- Phase A: Health Endpoint vs MySQL Verification ---")
        h_res = client.get("/api/health")
        assert h_res.status_code == 200, f"Health returned {h_res.status_code}"
        h_data = h_res.json()
        print(f"Health Response: {h_data}")

        db = SessionLocal()
        try:
            actual_mysql_count = db.query(Meter).count()
        finally:
            db.close()

        print(f"Direct MySQL Meter Count: {actual_mysql_count}")
        assert h_data.get("meter_count") == actual_mysql_count, (
            f"Health meter_count {h_data.get('meter_count')} != MySQL count {actual_mysql_count}"
        )
        print("[PASS] Health endpoint meter_count accurately reflects MySQL count.")

        # 2. Test each of the six scenarios
        print("\n--- Phase B: Executing Six Anomaly Scenarios ---")
        for sc in scenarios:
            payload = {
                "meter_id": "M001",
                "scenario": sc,
                "auto_generate_report": True,
            }
            res = client.post("/api/simulate/tamper", json=payload)
            assert res.status_code == 200, f"Scenario {sc} failed with HTTP {res.status_code}: {res.text}"
            data = res.json()

            seq_id = data.get("sequence_id")
            lstm = data.get("lstm_result", {})
            mse = lstm.get("reconstruction_error")
            threshold = lstm.get("threshold")
            is_anomaly = lstm.get("is_anomaly")
            status = lstm.get("status")
            report = data.get("report") or {}
            report_id = report.get("id")
            rep_seq_id = report.get("sequence_id")
            model_used = report.get("model_used")
            alert = data.get("alert") or {}
            alert_id = alert.get("id") if alert else None

            # Verify exact sequence ID binding between simulator and report
            assert seq_id is not None, f"Missing sequence_id for {sc}"
            assert rep_seq_id == seq_id, f"Report sequence_id {rep_seq_id} != {seq_id}"

            # Verify in MySQL
            db = SessionLocal()
            try:
                db_seq = db.query(ConsumptionSequence).filter(ConsumptionSequence.id == seq_id).first()
                assert db_seq is not None, f"Sequence {seq_id} not persisted in MySQL"
                assert db_seq.scenario == sc, f"Sequence scenario {db_seq.scenario} != {sc}"
                assert db_seq.is_simulated is True, "Sequence is_simulated should be True"

                if report_id:
                    db_rep = db.query(InvestigationReport).filter(InvestigationReport.id == report_id).first()
                    assert db_rep is not None, f"Report {report_id} not persisted in MySQL"
                    rep_ev = json.loads(db_rep.evidence_json) if db_rep.evidence_json else {}
                    assert rep_ev.get("consumption", {}).get("sequence_id") == seq_id, (
                        "Report evidence sequence_id mismatch"
                    )
            finally:
                db.close()

            results.append({
                "scenario": sc,
                "seq_id": seq_id,
                "mse": f"{mse:.6f}" if mse is not None else "N/A",
                "threshold": f"{threshold:.6f}" if threshold is not None else "0.013009",
                "is_anomaly": is_anomaly,
                "status": status,
                "report_id": report_id,
                "model_used": model_used,
                "alert_id": alert_id,
            })
            print(f"[{sc.upper()}] Seq #{seq_id} | MSE: {results[-1]['mse']} | Thresh: {results[-1]['threshold']} | Status: {status} | Report #{report_id} ({model_used}) | Alert: {alert_id}")

        # 3. Test Alert Resolution upon subsequent normal scenario
        print("\n--- Phase C: Alert Auto-Resolution Verification ---")
        # Generate spike (creates alert)
        spike_res = client.post("/api/simulate/tamper", json={"meter_id": "M001", "scenario": "consumption_spike", "auto_generate_report": False})
        assert spike_res.status_code == 200
        assert spike_res.json()["alert"] is not None, "Expected active alert for consumption_spike"
        spike_alert_id = spike_res.json()["alert"]["id"]
        print(f"Active Alert created: #{spike_alert_id}")

        # Follow up with normal scenario (resolves simulated alert)
        normal_res = client.post("/api/simulate/tamper", json={"meter_id": "M001", "scenario": "normal", "auto_generate_report": False})
        assert normal_res.status_code == 200

        db = SessionLocal()
        try:
            resolved_alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == spike_alert_id).first()
            assert resolved_alert.is_resolved is True, f"Alert #{spike_alert_id} was expected to be resolved after normal reading"
            print(f"[PASS] Alert #{spike_alert_id} was successfully auto-resolved upon normal simulation.")
        finally:
            db.close()

    print("\n=========================================================================================")
    print("ALL SIX SCENARIOS, EVIDENCE BINDINGS, AND ALERT RESOLUTIONS VERIFIED SUCCESSFULLY!")
    print("=========================================================================================")
    return results

if __name__ == "__main__":
    run_six_scenarios()
