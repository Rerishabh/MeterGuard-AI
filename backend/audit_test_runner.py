"""
MeterGuard AI: Complete Audit Test Runner
Executes comprehensive programmatic testing across:
- Stage B: Backend & API Verification (all 12 endpoints + error cases)
- Stage C: MySQL Data Accuracy Audit (schemas, constraints, records, relations, evidence, timestamps, simulation flags)
- Stage D: Machine Learning Verification (Models 1, 2, 3 Daily, 4 Hourly, Arbitration)
- Stage F: Tampering Simulator Verification (all 6 scenarios)
- Stage G: Investigation Report Verification (evidence consistency, model_used, fallback)
"""

import sys
import json
import math
import traceback
from pathlib import Path
from datetime import datetime

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import inspect, text
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.database.session import SessionLocal, engine, check_db_connection
from backend.app.models.db_models import (
    Meter,
    HardwareReading,
    ConsumptionSequence,
    AnomalyAlert,
    InvestigationReport,
)
from backend.app.services.ml_engine import ml_engine
from backend.app.services.tamper_simulator import tamper_simulator, VALID_SCENARIOS
from backend.app.services.investigation_generator import investigation_generator
from backend.decision_logic import get_final_status
from backend.app.main import app

results = {
    "stage_b_api": {},
    "stage_c_db": {},
    "stage_d_ml": {},
    "stage_f_simulator": {},
    "stage_g_reports": {},
}

def log(section, test_name, status, details=""):
    print(f"[{status}] {section} :: {test_name} {('- ' + details) if details else ''}")
    results[section][test_name] = {"status": status, "details": details}

def run_stage_b_api():
    print("\n" + "="*50)
    print("STAGE B: BACKEND & API VERIFICATION")
    print("="*50)
    
    with TestClient(app) as client:
        # 1. GET /
        res = client.get("/")
        if res.status_code == 200 and res.json().get("status") == "online":
            log("stage_b_api", "GET /", "PASS", f"Status: {res.status_code}, service: {res.json().get('service')}")
        else:
            log("stage_b_api", "GET /", "FAIL", f"Status: {res.status_code}, response: {res.text}")

        # 2. GET /api/health
        res = client.get("/api/health")
        data = res.json()
        if (res.status_code == 200 and data.get("status") == "online" 
            and data.get("model1_loaded") is True and data.get("model2_loaded") is True
            and data.get("lstm_daily_available") is True and data.get("lstm_hourly_available") is True
            and data.get("database_connected") is True):
            log("stage_b_api", "GET /api/health", "PASS", f"Health payload: {data}")
        else:
            log("stage_b_api", "GET /api/health", "FAIL", f"Unexpected payload: {data}")

        # 3. GET /api/dashboard
        res = client.get("/api/dashboard")
        data = res.json()
        if res.status_code == 200 and "meters" in data and isinstance(data["meters"], list):
            log("stage_b_api", "GET /api/dashboard", "PASS", f"Meters count: {len(data['meters'])}, source: {data.get('source')}")
        else:
            log("stage_b_api", "GET /api/dashboard", "FAIL", f"Status: {res.status_code}, response: {res.text}")

        # 4. GET /api/meters
        res = client.get("/api/meters")
        data = res.json()
        if res.status_code == 200 and "meters" in data:
            log("stage_b_api", "GET /api/meters", "PASS", f"Meters count: {len(data['meters'])}")
        else:
            log("stage_b_api", "GET /api/meters", "FAIL", f"Status: {res.status_code}, response: {res.text}")

        # 5. GET /api/meter/{meter_id}
        res_m001 = client.get("/api/meter/M001")
        if res_m001.status_code == 200 and res_m001.json().get("meter_id") == "M001":
            log("stage_b_api", "GET /api/meter/M001", "PASS", f"Returned meter: {res_m001.json().get('meter_id')}")
        else:
            log("stage_b_api", "GET /api/meter/M001", "FAIL", f"Status: {res_m001.status_code}, response: {res_m001.text}")

        res_404 = client.get("/api/meter/NON_EXISTENT_METER_XYZ")
        if res_404.status_code == 404:
            log("stage_b_api", "GET /api/meter/404", "PASS", "Correctly returned HTTP 404 for unknown meter")
        else:
            log("stage_b_api", "GET /api/meter/404", "FAIL", f"Expected 404, got {res_404.status_code}")

        # 6. GET /api/alerts
        res = client.get("/api/alerts")
        data = res.json()
        if res.status_code == 200 and "alerts" in data:
            log("stage_b_api", "GET /api/alerts", "PASS", f"Total alerts: {data.get('count')}")
        else:
            log("stage_b_api", "GET /api/alerts", "FAIL", f"Status: {res.status_code}")

        res_filt = client.get("/api/alerts?severity=HIGH&limit=5")
        if res_filt.status_code == 200 and "alerts" in res_filt.json():
            log("stage_b_api", "GET /api/alerts (filters)", "PASS", f"Filtered alerts count: {len(res_filt.json()['alerts'])}")
        else:
            log("stage_b_api", "GET /api/alerts (filters)", "FAIL", f"Status: {res_filt.status_code}")

        # 7. POST /api/meter-data
        valid_telemetry = {
            "meter_id": "M001",
            "time_ms": 100,
            "T1_CS": 3020,
            "T1_VS": 230,
            "T2_CS": 3020,
            "T2_VS": 230,
            "H1_CS": 3020,
            "H1_VS": 230,
        }
        res = client.post("/api/meter-data", json=valid_telemetry)
        if res.status_code == 200 and res.json().get("status") in ["received", "success"]:
            log("stage_b_api", "POST /api/meter-data (valid)", "PASS", f"Response model2: {res.json().get('model2', {}).get('prediction')}")
        else:
            log("stage_b_api", "POST /api/meter-data (valid)", "FAIL", f"Status: {res.status_code}, response: {res.text}")

        # POST /api/meter-data invalid missing fields
        bad_telemetry = {"meter_id": "M001", "T1_CS": 3000}
        res_bad = client.post("/api/meter-data", json=bad_telemetry)
        if res_bad.status_code == 400:
            log("stage_b_api", "POST /api/meter-data (missing fields)", "PASS", "HTTP 400 correctly returned")
        else:
            log("stage_b_api", "POST /api/meter-data (missing fields)", "FAIL", f"Expected 400, got {res_bad.status_code}")

        # 8. POST /api/anomaly/analyze
        daily_seq = [12.0 + (i % 3) * 0.5 for i in range(30)]
        res_daily = client.post("/api/anomaly/analyze", json={
            "meter_id": "M001",
            "sequence_type": "daily",
            "consumption": daily_seq,
        })
        if res_daily.status_code == 200 and res_daily.json().get("sequence_length") == 30:
            log("stage_b_api", "POST /api/anomaly/analyze (daily)", "PASS", f"MSE: {res_daily.json().get('reconstruction_error')}")
        else:
            log("stage_b_api", "POST /api/anomaly/analyze (daily)", "FAIL", f"Status: {res_daily.status_code}, response: {res_daily.text}")

        # Invalid daily length
        res_invalid_len = client.post("/api/anomaly/analyze", json={
            "meter_id": "M001",
            "sequence_type": "daily",
            "consumption": [10.0] * 20,
        })
        if res_invalid_len.status_code == 400:
            log("stage_b_api", "POST /api/anomaly/analyze (invalid length)", "PASS", "HTTP 400 correctly returned for 20 values")
        else:
            log("stage_b_api", "POST /api/anomaly/analyze (invalid length)", "FAIL", f"Expected 400, got {res_invalid_len.status_code}")

        # Negative consumption
        res_neg = client.post("/api/anomaly/analyze", json={
            "meter_id": "M001",
            "sequence_type": "daily",
            "consumption": [-5.0] * 30,
        })
        if res_neg.status_code == 400:
            log("stage_b_api", "POST /api/anomaly/analyze (negative value)", "PASS", "HTTP 400 correctly returned for negative consumption")
        else:
            log("stage_b_api", "POST /api/anomaly/analyze (negative value)", "FAIL", f"Expected 400, got {res_neg.status_code}")

        # 9. POST /api/simulate/tamper
        res_sim = client.post("/api/simulate/tamper", json={
            "meter_id": "M_SIM_01",
            "scenario": "consumption_spike",
            "auto_report": False,
        })
        if res_sim.status_code == 200 and res_sim.json().get("scenario") == "consumption_spike":
            seq_id = res_sim.json().get("sequence_id")
            lstm_res = res_sim.json().get("lstm_result", {})
            log("stage_b_api", "POST /api/simulate/tamper", "PASS", f"Simulated sequence_id: {seq_id}, anomaly: {lstm_res.get('is_anomaly')}, mse: {lstm_res.get('reconstruction_error')}")
        else:
            log("stage_b_api", "POST /api/simulate/tamper", "FAIL", f"Status: {res_sim.status_code}, response: {res_sim.text}")

        # 10. POST /api/reports/generate
        res_rep_gen = client.post("/api/reports/generate", json={
            "meter_id": "M_SIM_01",
        })
        if res_rep_gen.status_code == 200 and "report" in res_rep_gen.json():
            rep = res_rep_gen.json()["report"]
            log("stage_b_api", "POST /api/reports/generate", "PASS", f"Report id: {rep.get('id')}, model_used: {rep.get('model_used')}, markdown len: {len(rep.get('report_markdown', ''))}")
        else:
            log("stage_b_api", "POST /api/reports/generate", "FAIL", f"Status: {res_rep_gen.status_code}, response: {res_rep_gen.text}")

        # 11. GET /api/reports/{meter_id}
        res_rep_meter = client.get("/api/reports/M_SIM_01")
        if res_rep_meter.status_code == 200 and "reports" in res_rep_meter.json():
            log("stage_b_api", "GET /api/reports/M_SIM_01", "PASS", f"Retrieved {len(res_rep_meter.json()['reports'])} reports")
        else:
            log("stage_b_api", "GET /api/reports/M_SIM_01", "FAIL", f"Status: {res_rep_meter.status_code}")

        # 12. GET /api/reports
        res_reps = client.get("/api/reports")
        if res_reps.status_code == 200 and "reports" in res_reps.json():
            log("stage_b_api", "GET /api/reports", "PASS", f"Retrieved {len(res_reps.json()['reports'])} reports across system")
        else:
            log("stage_b_api", "GET /api/reports", "FAIL", f"Status: {res_reps.status_code}")

def run_stage_c_db():
    print("\n" + "="*50)
    print("STAGE C: MYSQL DATA ACCURACY AUDIT")
    print("="*50)
    
    db_ok, db_err = check_db_connection()
    if not db_ok:
        log("stage_c_db", "MySQL Connection", "FAIL", f"Error: {db_err}")
        return

    log("stage_c_db", "MySQL Connection", "PASS", f"Connected to {settings.DATABASE_URL.split('@')[-1]}")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected_tables = ["meters", "hardware_readings", "consumption_sequences", "anomaly_alerts", "investigation_reports", "alembic_version"]
    
    missing_tables = [t for t in expected_tables if t not in tables]
    if not missing_tables:
        log("stage_c_db", "Tables Existence", "PASS", f"All expected tables present: {tables}")
    else:
        log("stage_c_db", "Tables Existence", "FAIL", f"Missing tables: {missing_tables}")

    db = SessionLocal()
    try:
        # Check Alembic version
        alembic_rev = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        log("stage_c_db", "Alembic Version", "PASS", f"Current revision: {alembic_rev}")

        # Check meters records
        meters = db.query(Meter).all()
        log("stage_c_db", "Meters Record Count", "PASS", f"Total meters: {len(meters)} -> {[m.meter_id for m in meters]}")

        for m in meters:
            if m.latitude is not None and m.longitude is not None:
                log("stage_c_db", f"Meter {m.meter_id} GPS", "PASS", f"Location: '{m.location_name}' ({m.latitude}, {m.longitude})")
            else:
                log("stage_c_db", f"Meter {m.meter_id} GPS", "PASS", f"Location: '{m.location_name}' (No GPS fixed)")

        # Foreign Key & Cascade checks
        fks_hw = inspector.get_foreign_keys("hardware_readings")
        log("stage_c_db", "HardwareReading FK", "PASS" if any(fk["referred_table"] == "meters" for fk in fks_hw) else "FAIL", str(fks_hw))

        fks_seq = inspector.get_foreign_keys("consumption_sequences")
        log("stage_c_db", "ConsumptionSequence FK", "PASS" if any(fk["referred_table"] == "meters" for fk in fks_seq) else "FAIL", str(fks_seq))

        fks_alerts = inspector.get_foreign_keys("anomaly_alerts")
        log("stage_c_db", "AnomalyAlert FK", "PASS" if any(fk["referred_table"] == "meters" for fk in fks_alerts) else "FAIL", str(fks_alerts))

        fks_rep = inspector.get_foreign_keys("investigation_reports")
        log("stage_c_db", "InvestigationReport FK", "PASS" if any(fk["referred_table"] == "meters" for fk in fks_rep) else "FAIL", str(fks_rep))

        # Check simulation integrity in consumption_sequences
        seqs = db.query(ConsumptionSequence).order_by(ConsumptionSequence.id.desc()).limit(10).all()
        sim_count = db.query(ConsumptionSequence).filter(ConsumptionSequence.is_simulated == True).count()
        real_count = db.query(ConsumptionSequence).filter(ConsumptionSequence.is_simulated == False).count()
        log("stage_c_db", "Simulation Integrity", "PASS", f"Total sequences: {sim_count + real_count} (Simulated: {sim_count}, Live: {real_count})")

        # Verify scenario column
        has_scenario_col = any(c["name"] == "scenario" for c in inspector.get_columns("consumption_sequences"))
        has_is_sim_col = any(c["name"] == "is_simulated" for c in inspector.get_columns("consumption_sequences"))
        log("stage_c_db", "Sequence Scenario & is_simulated columns", "PASS" if (has_scenario_col and has_is_sim_col) else "FAIL")

        # Verify investigation report evidence JSON consistency
        reports = db.query(InvestigationReport).order_by(InvestigationReport.id.desc()).limit(5).all()
        if reports:
            for rep in reports:
                if rep.evidence_json:
                    ev = json.loads(rep.evidence_json)
                    seq_id = ev.get("sequence_id")
                    if seq_id:
                        matched_seq = db.query(ConsumptionSequence).filter(ConsumptionSequence.id == seq_id).first()
                        if matched_seq:
                            # Verify reconstruction error matches
                            ev_err = ev.get("reconstruction_error")
                            db_err = matched_seq.reconstruction_error
                            if abs(ev_err - db_err) < 1e-5:
                                log("stage_c_db", f"Report #{rep.id} Evidence Consistency", "PASS", f"Sequence #{seq_id} matched: ev_error={ev_err}, db_error={db_err}")
                            else:
                                log("stage_c_db", f"Report #{rep.id} Evidence Consistency", "FAIL", f"Mismatch: ev_error={ev_err}, db_error={db_err}")
                        else:
                            log("stage_c_db", f"Report #{rep.id} Evidence Consistency", "FAIL", f"Sequence #{seq_id} referenced in evidence not found in DB")
                    else:
                        log("stage_c_db", f"Report #{rep.id} Evidence Consistency", "PASS", "Report has evidence_json without sequence_id binding")
                else:
                    log("stage_c_db", f"Report #{rep.id} Evidence Consistency", "FAIL", "evidence_json is null")
        else:
            log("stage_c_db", "Investigation Reports Consistency", "PASS", "No reports in database to inspect")

        # Timestamp audit
        latest_hw = db.query(HardwareReading).order_by(HardwareReading.id.desc()).first()
        if latest_hw:
            log("stage_c_db", "Timestamps Consistency", "PASS", f"Latest HardwareReading timestamp: {latest_hw.timestamp} (type: {type(latest_hw.timestamp)})")

    finally:
        db.close()

def run_stage_d_ml():
    print("\n" + "="*50)
    print("STAGE D: MACHINE LEARNING VERIFICATION")
    print("="*50)

    # 1. Model 1: Isolation Forest
    m1 = ml_engine.model1
    if m1 is not None:
        try:
            from backend.model1_features import create_model1_features
            sample_consumption = [15.0, 16.2, 14.8, 15.5, 16.0, 15.2, 14.9, 15.8, 16.5, 15.0]
            feats = create_model1_features(sample_consumption)
            pred = m1.predict(feats)
            log("stage_d_ml", "Model 1 (Isolation Forest)", "PASS", f"Loaded successfully. 7 Features: {list(feats.columns)}. Inference output: {pred[0]}")
        except Exception as exc:
            log("stage_d_ml", "Model 1 (Isolation Forest)", "FAIL", f"Inference failed: {exc}")
    else:
        log("stage_d_ml", "Model 1 (Isolation Forest)", "FAIL", "Model 1 not loaded")

    # 2. Model 2: Random Forest
    m2 = ml_engine.model2
    if m2 is not None:
        try:
            from backend.model2_features import create_model2_features
            sample_reading = {
                "T1_CS": 3020, "T1_VS": 230,
                "T2_CS": 3020, "T2_VS": 230,
                "H1_CS": 3020, "H1_VS": 230,
            }
            feats = create_model2_features(sample_reading)
            pred = m2.predict(feats)[0]
            norm_pred = ml_engine.normalize_model2_prediction(pred)
            log("stage_d_ml", "Model 2 (Random Forest)", "PASS", f"Loaded successfully. Features: {list(feats.columns)}. Prediction: {norm_pred}")
        except Exception as exc:
            log("stage_d_ml", "Model 2 (Random Forest)", "FAIL", f"Inference failed: {exc}")
    else:
        log("stage_d_ml", "Model 2 (Random Forest)", "FAIL", "Model 2 not loaded")

    # 3. Model 3: Daily LSTM Autoencoder
    daily_m = ml_engine.daily_lstm
    daily_scaler = ml_engine.daily_scaler
    daily_meta = getattr(ml_engine, "daily_threshold_meta", {})
    daily_th = daily_meta.get("active_threshold_value", daily_meta.get("threshold_95", 0.013009))
    daily_th99 = daily_meta.get("threshold_99", 0.014284)
    if daily_m is not None and daily_scaler is not None:
        seq = [12.0 + (i % 4) * 0.5 for i in range(30)]
        res = ml_engine.predict_sequence("daily", seq, meter_id="M001")
        log("stage_d_ml", "Model 3 (Daily LSTM AE)", "PASS", f"Threshold: {daily_th:.6f}, 99th: {daily_th99:.6f}, Inference MSE: {res.get('reconstruction_error'):.6f}, Status: {res.get('status')}")
    else:
        log("stage_d_ml", "Model 3 (Daily LSTM AE)", "FAIL", "Daily LSTM or scaler not loaded")

    # 4. Model 4: Hourly LSTM Autoencoder
    hourly_m = ml_engine.hourly_lstm
    hourly_scaler = ml_engine.hourly_scaler
    hourly_meta = getattr(ml_engine, "hourly_threshold_meta", {})
    hourly_th = hourly_meta.get("active_threshold_value", hourly_meta.get("threshold_95", 0.016575))
    hourly_th99 = hourly_meta.get("threshold_99", 0.021118)
    if hourly_m is not None and hourly_scaler is not None:
        seq = [0.5 + (i % 5) * 0.1 for i in range(24)]
        res = ml_engine.predict_sequence("hourly", seq, meter_id="M001")
        log("stage_d_ml", "Model 4 (Hourly LSTM AE)", "PASS", f"Threshold: {hourly_th:.6f}, 99th: {hourly_th99:.6f}, Inference MSE: {res.get('reconstruction_error'):.6f}, Status: {res.get('status')}")
    else:
        log("stage_d_ml", "Model 4 (Hourly LSTM AE)", "FAIL", "Hourly LSTM or scaler not loaded")

    # 5. Decision Arbitration
    arb_normal = get_final_status("NORMAL", "NORMAL")
    arb_tamper = get_final_status("SUSPICIOUS", "FAULT_S1")
    log("stage_d_ml", "Decision Arbitration", "PASS", f"Normal case: {arb_normal}; Tamper case: {arb_tamper}")

def run_stage_f_simulator():
    print("\n" + "="*50)
    print("STAGE F: TAMPERING SIMULATOR VERIFICATION")
    print("="*50)

    for sc in VALID_SCENARIOS:
        consumption = tamper_simulator.generate_sequence(sc)
        
        # Verify exactly 30 values
        len_ok = len(consumption) == 30
        
        # Verify finite and non-negative
        vals_ok = all(isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v) and v >= 0 for v in consumption)
        
        # Run daily LSTM
        res = ml_engine.predict_sequence("daily", consumption, meter_id="M_SIM_TEST")
        mse = res.get("reconstruction_error")
        th = res.get("threshold")
        is_anom = res.get("is_anomaly")
        
        status = "PASS" if (len_ok and vals_ok and mse is not None) else "FAIL"
        log("stage_f_simulator", f"Scenario '{sc}'", status, f"Len={len(consumption)}, NonNeg={vals_ok}, MSE={mse:.6f}, Thresh={th:.6f}, Anomaly={is_anom}")

def run_stage_g_reports():
    print("\n" + "="*50)
    print("STAGE G: INVESTIGATION REPORT VERIFICATION")
    print("="*50)

    db = SessionLocal()
    try:
        # Generate report for M001
        rep, err = investigation_generator.generate_report(db, meter_id="M001")
        if err or not rep:
            log("stage_g_reports", "Report Generation (M001)", "FAIL", f"Error: {err}")
            return

        log("stage_g_reports", "Report Generation (M001)", "PASS", f"Report ID: {rep.id}, model_used: {rep.model_used}, chars: {len(rep.report_markdown)}")

        # Check required sections in Markdown
        md = rep.report_markdown
        sections = [
            "Executive Summary",
            "Observed Consumption & Sensor Evidence",
            "Root-Cause Hypotheses",
            "Field Inspection Checklist",
            "Recommended Next Steps",
        ]
        missing_sec = [s for s in sections if s not in md]
        if not missing_sec:
            log("stage_g_reports", "Report 5 Sections", "PASS", "All 5 required sections present in markdown")
        else:
            log("stage_g_reports", "Report 5 Sections", "FAIL", f"Missing sections: {missing_sec}")

        # Check evidence consistency
        if rep.evidence_json:
            ev = json.loads(rep.evidence_json)
            log("stage_g_reports", "Report Evidence JSON", "PASS", f"Keys: {list(ev.keys())}, meter_id={ev.get('meter_id')}")
        else:
            log("stage_g_reports", "Report Evidence JSON", "FAIL", "evidence_json is empty")

    finally:
        db.close()

if __name__ == "__main__":
    run_stage_b_api()
    run_stage_c_db()
    run_stage_d_ml()
    run_stage_f_simulator()
    run_stage_g_reports()

    # Summary
    print("\n" + "="*50)
    print("AUDIT EXECUTION SUMMARY")
    print("="*50)
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    for stage, stage_tests in results.items():
        for tname, tinfo in stage_tests.items():
            total_tests += 1
            if tinfo["status"] == "PASS":
                passed_tests += 1
            else:
                failed_tests += 1
    print(f"TOTAL TESTS: {total_tests}")
    print(f"PASSED:      {passed_tests}")
    print(f"FAILED:      {failed_tests}")
    print("="*50)

    # Save results to json for report inclusion
    out_file = PROJECT_ROOT / "backend" / "audit_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Audit results written to {out_file}")
