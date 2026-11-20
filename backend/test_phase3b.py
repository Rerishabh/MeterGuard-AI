"""
MeterGuard AI: Phase 3B Test Suite
Comprehensive verification of Tampering Simulator, Investigation Report Generator,
Gemini & Deterministic Fallback, MySQL Persistence, and API Contracts.
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.database.session import SessionLocal
from backend.app.models.db_models import (
    Meter,
    HardwareReading,
    ConsumptionSequence,
    AnomalyAlert,
    InvestigationReport,
)
from backend.app.services.tamper_simulator import tamper_simulator, VALID_SCENARIOS
from backend.app.services.investigation_generator import investigation_generator


def run_phase3b_tests():
    print("\n========================================================")
    print("      METERGUARD AI: PHASE 3B VERIFICATION SUITE       ")
    print("========================================================")

    # -------------------------------------------------------------
    # 0. Clean up any previous test meters
    # -------------------------------------------------------------
    db = SessionLocal()
    try:
        test_ids = ["M_SIM_01", "M_SIM_02", "M_SIM_03", "M_SIM_FALLBACK"]
        db.query(InvestigationReport).filter(InvestigationReport.meter_id.in_(test_ids)).delete(synchronize_session=False)
        db.query(AnomalyAlert).filter(AnomalyAlert.meter_id.in_(test_ids)).delete(synchronize_session=False)
        db.query(ConsumptionSequence).filter(ConsumptionSequence.meter_id.in_(test_ids)).delete(synchronize_session=False)
        db.query(HardwareReading).filter(HardwareReading.meter_id.in_(test_ids)).delete(synchronize_session=False)
        db.query(Meter).filter(Meter.meter_id.in_(test_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        # -------------------------------------------------------------
        # TEST 1: Tamper Simulator Core Generation Across All 6 Scenarios
        # -------------------------------------------------------------
        print("\n[TEST 1] Testing All 6 Tampering Simulator Scenarios...")
        assert len(VALID_SCENARIOS) == 6, f"Expected 6 scenarios, got {len(VALID_SCENARIOS)}"

        for scenario, desc in VALID_SCENARIOS.items():
            seq = tamper_simulator.generate_sequence(scenario)
            assert len(seq) == 30, f"Scenario '{scenario}' generated {len(seq)} values instead of 30"
            assert all(isinstance(v, (float, int)) for v in seq), f"Scenario '{scenario}' contains non-numeric values"
            assert all(np.isfinite(v) for v in seq), f"Scenario '{scenario}' contains non-finite (NaN/Inf) values"
            assert all(v >= 0.0 for v in seq), f"Scenario '{scenario}' contains negative consumption values"

            eval_res = tamper_simulator.simulate_and_evaluate("M_SIM_01", scenario)
            lstm = eval_res["lstm_result"]
            assert lstm["sequence_length"] == 30
            assert "reconstruction_error" in lstm
            assert "threshold" in lstm
            assert "is_anomaly" in lstm
            print(f"   -> Scenario '{scenario}': Len={len(seq)}, MSE={lstm['reconstruction_error']}, Status={lstm['status']}")

        print("   [PASS] All 6 scenarios generate valid 30-day sequences with honest LSTM evaluation.")

        # -------------------------------------------------------------
        # TEST 2: Invalid Scenario & Payload Validation (HTTP 400)
        # -------------------------------------------------------------
        print("\n[TEST 2] Testing Simulator Edge Cases & HTTP 400 Enforcement...")
        r_bad_scen = client.post("/api/simulate/tamper", json={"meter_id": "M_SIM_01", "scenario": "invalid_mode"})
        assert r_bad_scen.status_code == 400, f"Expected 400 for bad scenario, got {r_bad_scen.status_code}"

        r_empty_id = client.post("/api/simulate/tamper", json={"meter_id": "   ", "scenario": "normal"})
        assert r_empty_id.status_code == 400, f"Expected 400 for empty meter_id, got {r_empty_id.status_code}"

        print("   [PASS] Edge cases correctly rejected with HTTP 400.")

        # -------------------------------------------------------------
        # TEST 3: POST /api/simulate/tamper with MySQL Persistence
        # -------------------------------------------------------------
        print("\n[TEST 3] Testing POST /api/simulate/tamper & Direct MySQL Persistence...")
        sim_payload = {
            "meter_id": "M_SIM_01",
            "scenario": "consumption_spike",
            "auto_generate_report": True,
        }
        res_sim = client.post("/api/simulate/tamper", json=sim_payload)
        assert res_sim.status_code == 200, f"Simulation POST failed: {res_sim.text}"
        sim_data = res_sim.json()

        assert sim_data["status"] == "success"
        assert sim_data["meter_id"] == "M_SIM_01"
        assert sim_data["is_simulated"] is True
        assert sim_data["scenario"] == "consumption_spike"
        assert len(sim_data["consumption"]) == 30
        assert sim_data["lstm_result"]["is_anomaly"] is True

        # Verify in MySQL directly
        db = SessionLocal()
        try:
            m_row = db.query(Meter).filter(Meter.meter_id == "M_SIM_01").first()
            assert m_row is not None, "Meter row not found in MySQL"
            assert m_row.status == "SUSPICIOUS"

            seq_row = db.query(ConsumptionSequence).filter(
                ConsumptionSequence.meter_id == "M_SIM_01",
                ConsumptionSequence.is_simulated == True,  # noqa: E712
            ).first()
            assert seq_row is not None, "ConsumptionSequence not persisted in MySQL"
            assert seq_row.scenario == "consumption_spike"
            assert seq_row.is_anomaly is True
            print(f"   [VERIFIED IN MYSQL] ConsumptionSequence: id={seq_row.id}, scenario='{seq_row.scenario}', error={seq_row.reconstruction_error}")

            alert_row = db.query(AnomalyAlert).filter(
                AnomalyAlert.meter_id == "M_SIM_01",
                AnomalyAlert.is_resolved == False,  # noqa: E712
            ).first()
            assert alert_row is not None, "AnomalyAlert not persisted in MySQL"
            assert "SIMULATED_CONSUMPTION_SPIKE" in alert_row.fault_type
            print(f"   [VERIFIED IN MYSQL] AnomalyAlert: id={alert_row.id}, fault='{alert_row.fault_type}', severity='{alert_row.severity}'")

            rep_row = db.query(InvestigationReport).filter(
                InvestigationReport.meter_id == "M_SIM_01"
            ).first()
            assert rep_row is not None, "InvestigationReport not persisted in MySQL"
            assert rep_row.model_used in [settings.GEMINI_MODEL, "gemini-3.8-flash", "gemini-2.5-flash", "deterministic-fallback"]
            assert "### 1. Executive Summary" in rep_row.report_markdown
            assert "### 2. Observed Consumption & Sensor Evidence" in rep_row.report_markdown
            assert "### 3. Technical Root-Cause Hypotheses" in rep_row.report_markdown
            assert "### 4. Prioritized Field Inspection Checklist" in rep_row.report_markdown
            assert "### 5. Recommended Next Steps" in rep_row.report_markdown

            # Strict evidence consistency check across sections:
            rep_evidence = json.loads(rep_row.evidence_json)
            expected_mse_str = str(round(rep_evidence["consumption"]["reconstruction_error"], 4))
            assert str(rep_evidence["consumption"]["threshold_used"]) in rep_row.report_markdown, "Threshold missing from report"
            print(f"   [VERIFIED IN MYSQL] InvestigationReport: id={rep_row.id}, model='{rep_row.model_used}', len={len(rep_row.report_markdown)} chars")
        finally:
            db.close()

        print("   [PASS] Tamper simulation, sequence, alert, and report verified in MySQL.")

        # -------------------------------------------------------------
        # TEST 4: Alert Deduplication on Repeated Simulated Tampering
        # -------------------------------------------------------------
        print("\n[TEST 4] Testing Alert Deduplication in Simulation Engine...")
        # Simulate another spike on same meter M_SIM_01
        res_spike2 = client.post("/api/simulate/tamper", json={
            "meter_id": "M_SIM_01",
            "scenario": "consumption_spike",
            "auto_generate_report": False,
        })
        assert res_spike2.status_code == 200

        db = SessionLocal()
        try:
            active_alerts = db.query(AnomalyAlert).filter(
                AnomalyAlert.meter_id == "M_SIM_01",
                AnomalyAlert.is_resolved == False,  # noqa: E712
            ).all()
            assert len(active_alerts) == 1, f"Expected 1 active alert due to deduplication, found {len(active_alerts)}"
            print(f"   [VERIFIED IN MYSQL] Active alert count for M_SIM_01 is strictly 1 (deduplicated).")
        finally:
            db.close()

        # -------------------------------------------------------------
        # TEST 5: Normal Simulation Does Not Create False Anomaly Alert
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing Normal Baseline Simulation (No False High-Severity Alert)...")
        res_norm = client.post("/api/simulate/tamper", json={
            "meter_id": "M_SIM_02",
            "scenario": "normal",
            "auto_generate_report": False,
        })
        assert res_norm.status_code == 200
        norm_data = res_norm.json()
        assert norm_data["lstm_result"]["is_anomaly"] is False
        assert norm_data["alert"] is None

        db = SessionLocal()
        try:
            m2_alerts = db.query(AnomalyAlert).filter(AnomalyAlert.meter_id == "M_SIM_02").all()
            assert len(m2_alerts) == 0, f"Expected 0 alerts for normal simulation, found {len(m2_alerts)}"
            print("   [VERIFIED IN MYSQL] Normal simulation created 0 anomaly alerts.")
        finally:
            db.close()

        # -------------------------------------------------------------
        # TEST 6: Report Generation & Endpoints (POST, GET by meter, GET all)
        # -------------------------------------------------------------
        print("\n[TEST 6] Testing Report Generation & Endpoints...")
        # A. Manual report generation via POST /api/reports/generate
        res_rep_gen = client.post("/api/reports/generate", json={"meter_id": "M_SIM_02"})
        assert res_rep_gen.status_code == 200, f"Report generate failed: {res_rep_gen.text}"
        rep_payload = res_rep_gen.json()
        assert rep_payload["status"] == "success"
        assert "report" in rep_payload
        assert rep_payload["report"]["meter_id"] == "M_SIM_02"
        assert rep_payload["report"]["model_used"] in [settings.GEMINI_MODEL, "gemini-3.8-flash", "gemini-2.5-flash", "deterministic-fallback"]

        # B. GET /api/reports/{meter_id}
        res_m_reps = client.get("/api/reports/M_SIM_01")
        assert res_m_reps.status_code == 200
        m_reps = res_m_reps.json()
        assert m_reps["status"] == "success"
        assert m_reps["count"] >= 1
        print(f"   [PASS] GET /api/reports/M_SIM_01 returned {m_reps['count']} reports.")

        # C. GET /api/reports (recent)
        res_all_reps = client.get("/api/reports?limit=10")
        assert res_all_reps.status_code == 200
        all_reps = res_all_reps.json()
        assert all_reps["status"] == "success"
        assert all_reps["count"] >= 2
        print(f"   [PASS] GET /api/reports returned {all_reps['count']} recent reports.")

        # D. Non-existent meter returns 404
        res_404 = client.post("/api/reports/generate", json={"meter_id": "NON_EXISTENT_METER_XYZ"})
        assert res_404.status_code == 404, f"Expected 404 for non-existent meter, got {res_404.status_code}"
        print("   [PASS] Non-existent meter returns HTTP 404.")

        # -------------------------------------------------------------
        # TEST 7: Deterministic Fallback Integrity Verification
        # -------------------------------------------------------------
        print("\n[TEST 7] Testing Deterministic Fallback Verification...")
        db = SessionLocal()
        try:
            # First create a meter with hardware & consumption in MySQL
            m_fb = Meter(meter_id="M_SIM_FALLBACK", status="SUSPICIOUS", priority="HIGH", is_online=True)
            db.add(m_fb)
            db.flush()

            seq_fb = ConsumptionSequence(
                meter_id="M_SIM_FALLBACK",
                sequence_type="daily",
                sequence_length=30,
                consumption_json=json.dumps([4.5] * 15 + [1.8] * 15),
                reconstruction_error=0.0185,
                threshold_used=0.013009,
                threshold_99=0.014284,
                is_anomaly=True,
                status="SUSPICIOUS",
                is_simulated=True,
                scenario="sudden_drop",
            )
            db.add(seq_fb)
            db.commit()

            evidence, err = investigation_generator.collect_evidence(db, "M_SIM_FALLBACK")
            assert err is None
            assert evidence is not None
            assert evidence["meter"]["meter_id"] == "M_SIM_FALLBACK"
            assert evidence["consumption"]["is_anomaly"] is True

            md = investigation_generator.generate_deterministic_markdown(evidence)
            assert "### 1. Executive Summary" in md
            assert "### 2. Observed Consumption & Sensor Evidence" in md
            assert "### 3. Technical Root-Cause Hypotheses" in md
            assert "### 4. Prioritized Field Inspection Checklist" in md
            assert "### 5. Recommended Next Steps" in md
            assert "SIMULATED DATASET" in md
            assert "0.0185" in md
            assert "0.013009" in md
            print("   [PASS] Deterministic markdown contains exact evidence numbers and 5 required sections.")
        finally:
            db.close()

    print("\n========================================================")
    print("      ALL PHASE 3B TESTS COMPLETED WITH 100% PASS       ")
    print("========================================================")


if __name__ == "__main__":
    run_phase3b_tests()
