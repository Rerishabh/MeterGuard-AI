import os
import sys
import time
import requests
from datetime import datetime

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database.session import SessionLocal
from backend.app.models.db_models import AnomalyAlert, ConsumptionSequence, HardwareReading, Meter

BASE_URL = "http://127.0.0.1:5000"
METER_A = "M_ALERT_TEST_A"
METER_B = "M_ALERT_TEST_B"


def fresh_db():
    return SessionLocal()


def run_tests():
    print("=" * 70)
    print("METERGUARD AI - ALERT LIFECYCLE 10-POINT VERIFICATION SUITE")
    print("=" * 70)

    # 0. Check Backend Connectivity
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        print("[INIT] FastAPI Backend online and healthy at", BASE_URL)
    except Exception as e:
        print(f"[FATAL] Backend is not reachable at {BASE_URL}: {e}")
        sys.exit(1)

    # Clean any stale test fixtures first
    db = fresh_db()
    try:
        db.query(AnomalyAlert).filter(AnomalyAlert.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.query(ConsumptionSequence).filter(ConsumptionSequence.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.query(HardwareReading).filter(HardwareReading.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.query(Meter).filter(Meter.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.commit()

        # Record Baseline
        initial_alerts = db.query(AnomalyAlert).all()
        baseline_tuples = [
            (a.id, a.meter_id, a.source_model, a.fault_type, a.is_resolved)
            for a in initial_alerts
        ]
        initial_count = len(baseline_tuples)
        active_count = sum(1 for a in initial_alerts if not a.is_resolved)
        resolved_count = sum(1 for a in initial_alerts if a.is_resolved)
        print(f"[BASELINE] Existing MySQL Alert Records: {initial_count} total "
              f"({active_count} active, {resolved_count} resolved)")
    finally:
        db.close()

    try:
        # Seed test meters
        db = fresh_db()
        now = datetime.now()
        meter_a = Meter(
            meter_id=METER_A,
            location_name="Test Substation A",
            latitude=28.6139,
            longitude=77.2090,
            status="MONITORING",
            priority="LOW",
            is_online=True,
            last_seen=now,
        )
        meter_b = Meter(
            meter_id=METER_B,
            location_name="Test Substation B",
            latitude=28.6140,
            longitude=77.2091,
            status="MONITORING",
            priority="LOW",
            is_online=True,
            last_seen=now,
        )
        db.add(meter_a)
        db.add(meter_b)
        db.commit()
        db.close()

        # -------------------------------------------------------------
        # TEST 1: 5 normal RF readings resolve RF alert
        # TEST 2: RF normal readings do NOT resolve LSTM alert
        # TEST 3: RF resolution for Meter A does NOT affect Meter B
        # -------------------------------------------------------------
        print("\n--- Running Tests 1, 2, 3: Random Forest Resolution & Isolation ---")

        # 1. Send 7 fault readings to Meter A to confirm FAULT_S2
        fault_payload_a = {
            "meter_id": METER_A,
            "T1_CS": 3120.0,
            "T1_VS": 500.0,
            "T2_CS": 3110.0,
            "T2_VS": 498.0,
            "H1_CS": 2800.0,
            "H1_VS": 230.0,
            "time_ms": 100,
        }
        for _ in range(7):
            res_f = requests.post(f"{BASE_URL}/api/meter-data", json=fault_payload_a, timeout=5)
            assert res_f.status_code == 200

        # Verify active RF alert exists for Meter A
        db = fresh_db()
        rf_alert_a = (
            db.query(AnomalyAlert)
            .filter(
                AnomalyAlert.meter_id == METER_A,
                AnomalyAlert.source_model == "RandomForest",
                AnomalyAlert.is_resolved == False,
            )
            .first()
        )
        assert rf_alert_a is not None, "Failed to confirm active RF alert on Meter A"
        rf_alert_a_id = rf_alert_a.id

        # Insert active LSTM alert for Meter A and active RF alert for Meter B
        lstm_alert_a = AnomalyAlert(
            meter_id=METER_A,
            source_model="LSTM_Autoencoder",
            fault_type="SIMULATED_CONSUMPTION_SPIKE",
            severity="HIGH",
            message="Test LSTM Alert A",
            is_resolved=False,
            created_at=datetime.now(),
        )
        rf_alert_b = AnomalyAlert(
            meter_id=METER_B,
            source_model="RandomForest",
            fault_type="FAULT_S1",
            severity="HIGH",
            message="Test RF Alert B",
            is_resolved=False,
            created_at=datetime.now(),
        )
        db.add_all([lstm_alert_a, rf_alert_b])
        db.commit()
        lstm_alert_a_id = lstm_alert_a.id
        rf_alert_b_id = rf_alert_b.id
        db.close()

        # 2. Send 6 consecutive normal readings to Meter A to trigger CLEARED status
        normal_payload_a = {
            "meter_id": METER_A,
            "T1_CS": 3000.0,
            "T1_VS": 500.0,
            "T2_CS": 3000.0,
            "T2_VS": 500.0,
            "H1_CS": 3000.0,
            "H1_VS": 230.0,
            "time_ms": 2500,
        }
        for _ in range(6):
            res_n = requests.post(f"{BASE_URL}/api/meter-data", json=normal_payload_a, timeout=5)
            assert res_n.status_code == 200

        # Query state with fresh db session
        db = fresh_db()
        check_rf_a = db.query(AnomalyAlert).filter(AnomalyAlert.id == rf_alert_a_id).first()
        check_lstm_a = db.query(AnomalyAlert).filter(AnomalyAlert.id == lstm_alert_a_id).first()
        check_rf_b = db.query(AnomalyAlert).filter(AnomalyAlert.id == rf_alert_b_id).first()

        # TEST 1 Verification:
        assert check_rf_a.is_resolved is True, f"Test 1 FAILED: RF alert {rf_alert_a_id} was not resolved"
        print("[PASS] Test 1: 5 normal RF readings successfully resolved the RF alert.")

        # TEST 2 Verification:
        assert check_lstm_a.is_resolved is False, f"Test 2 FAILED: LSTM alert {lstm_alert_a_id} was mistakenly resolved"
        print("[PASS] Test 2: Normal RF readings did NOT resolve the LSTM alert (Isolated by source_model).")

        # TEST 3 Verification:
        assert check_rf_b.is_resolved is False, f"Test 3 FAILED: RF alert {rf_alert_b_id} on Meter B was mistakenly resolved"
        print("[PASS] Test 3: RF resolution on Meter A did NOT resolve Meter B's alert (Isolated by meter_id).")
        db.close()

        # -------------------------------------------------------------
        # TEST 4: Repeated active sequence anomaly does not create duplicate active alerts
        # -------------------------------------------------------------
        print("\n--- Running Test 4: Sequence Anomaly Deduplication ---")
        anomalous_sequence = [999.0] * 30  # Extreme daily consumption
        seq_payload = {
            "meter_id": METER_A,
            "sequence_type": "daily",
            "consumption": anomalous_sequence,
            "is_simulated": True,
        }
        # First call
        res_seq1 = requests.post(f"{BASE_URL}/api/evaluate-sequence", json=seq_payload, timeout=5)
        assert res_seq1.status_code == 200, f"evaluate-sequence 1 failed: {res_seq1.text}"
        data1 = res_seq1.json()
        assert data1.get("is_anomaly") is True, "Expected anomaly from extreme consumption"

        db = fresh_db()
        seq_alerts_1 = (
            db.query(AnomalyAlert)
            .filter(
                AnomalyAlert.meter_id == METER_A,
                AnomalyAlert.source_model == "Daily_LSTM_AE",
                AnomalyAlert.fault_type == "CONSUMPTION_ANOMALY",
                AnomalyAlert.is_resolved == False,
            )
            .all()
        )
        assert len(seq_alerts_1) == 1, f"Expected 1 active sequence alert, found {len(seq_alerts_1)}"
        first_alert_id = seq_alerts_1[0].id
        db.close()

        # Second call with anomalous sequence
        res_seq2 = requests.post(f"{BASE_URL}/api/evaluate-sequence", json=seq_payload, timeout=5)
        assert res_seq2.status_code == 200, f"evaluate-sequence 2 failed: {res_seq2.text}"

        db = fresh_db()
        seq_alerts_2 = (
            db.query(AnomalyAlert)
            .filter(
                AnomalyAlert.meter_id == METER_A,
                AnomalyAlert.source_model == "Daily_LSTM_AE",
                AnomalyAlert.fault_type == "CONSUMPTION_ANOMALY",
                AnomalyAlert.is_resolved == False,
            )
            .all()
        )
        assert len(seq_alerts_2) == 1, f"Test 4 FAILED: Duplicate active sequence alert created (count={len(seq_alerts_2)})"
        assert seq_alerts_2[0].id == first_alert_id, "Test 4 FAILED: Alert ID changed on repeated evaluation"
        print(f"[PASS] Test 4: Repeated sequence anomaly evaluation updated Alert #{first_alert_id} without duplicate insertion.")
        db.close()

        # -------------------------------------------------------------
        # TEST 5: Normal sequence evaluation resolves only its corresponding sequence alert
        # -------------------------------------------------------------
        print("\n--- Running Test 5: Normal Sequence Auto-Resolution ---")
        # Ensure an RF alert is also active on Meter A
        db = fresh_db()
        rf_control = AnomalyAlert(
            meter_id=METER_A,
            source_model="RandomForest",
            fault_type="FAULT_S1",
            severity="HIGH",
            message="Control RF Alert",
            is_resolved=False,
            created_at=datetime.now(),
        )
        db.add(rf_control)
        db.commit()
        rf_control_id = rf_control.id
        db.close()

        # Generate normal 30-day sequence (typical daily 4.5 kWh)
        normal_sequence = [4.5 + 0.1 * (i % 5) for i in range(30)]
        normal_seq_payload = {
            "meter_id": METER_A,
            "sequence_type": "daily",
            "consumption": normal_sequence,
            "is_simulated": True,
        }
        res_seq_norm = requests.post(f"{BASE_URL}/api/evaluate-sequence", json=normal_seq_payload, timeout=5)
        assert res_seq_norm.status_code == 200, f"evaluate-sequence normal failed: {res_seq_norm.text}"
        data_norm = res_seq_norm.json()
        assert data_norm.get("is_anomaly") is False, f"Expected normal result, got: {data_norm}"

        db = fresh_db()
        db_seq_a = db.query(AnomalyAlert).filter(AnomalyAlert.id == first_alert_id).first()
        db_rf_ctrl = db.query(AnomalyAlert).filter(AnomalyAlert.id == rf_control_id).first()

        assert db_seq_a.is_resolved is True, "Test 5 FAILED: Daily sequence alert was not auto-resolved on normal evaluation"
        assert db_rf_ctrl.is_resolved is False, "Test 5 FAILED: RF alert was mistakenly resolved by normal sequence evaluation"
        print("[PASS] Test 5: Normal sequence evaluation auto-resolved the sequence alert while leaving RF alert intact.")
        db.close()

        # -------------------------------------------------------------
        # TEST 6: Two distinct LSTM scenarios on same meter create separate alerts
        # -------------------------------------------------------------
        print("\n--- Running Test 6: LSTM Scenario Distinct Alert Creation ---")
        # Seed an existing simulated alert for sudden_drop
        db = fresh_db()
        existing_drop_alert = AnomalyAlert(
            meter_id=METER_A,
            source_model="LSTM_Autoencoder",
            fault_type="SIMULATED_SUDDEN_DROP",
            severity="HIGH",
            message="Initial sudden_drop alert",
            is_resolved=False,
            created_at=datetime.now(),
        )
        db.add(existing_drop_alert)
        db.commit()
        drop_alert_id = existing_drop_alert.id
        db.close()

        # Simulate a distinct scenario: consumption_spike (generates anomaly)
        res_scen1 = requests.post(
            f"{BASE_URL}/api/simulate/tamper",
            json={"meter_id": METER_A, "scenario": "consumption_spike", "sequence_type": "daily"},
            timeout=30,
        )
        assert res_scen1.status_code == 200, f"simulate-tampering spike failed: {res_scen1.text}"

        db = fresh_db()
        spike_alert = (
            db.query(AnomalyAlert)
            .filter(
                AnomalyAlert.meter_id == METER_A,
                AnomalyAlert.source_model == "LSTM_Autoencoder",
                AnomalyAlert.fault_type == "SIMULATED_CONSUMPTION_SPIKE",
                AnomalyAlert.is_resolved == False,
            )
            .first()
        )
        drop_alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == drop_alert_id).first()

        assert spike_alert is not None, "Test 6 FAILED: SIMULATED_CONSUMPTION_SPIKE alert missing"
        assert drop_alert is not None, "Test 6 FAILED: SIMULATED_SUDDEN_DROP alert missing"
        assert drop_alert.fault_type == "SIMULATED_SUDDEN_DROP", "Test 6 FAILED: Prior scenario fault_type was overwritten!"
        assert spike_alert.id != drop_alert.id, "Test 6 FAILED: Both scenarios shared the exact same alert row"
        print(f"[PASS] Test 6: Distinct scenarios created distinct active alerts (Drop #{drop_alert.id}, Spike #{spike_alert.id}).")
        spike_alert_id_before = spike_alert.id
        db.close()

        # -------------------------------------------------------------
        # TEST 7: Repeated evaluation of same active LSTM scenario updates without duplication
        # -------------------------------------------------------------
        print("\n--- Running Test 7: LSTM Scenario Repeated Evaluation Deduplication ---")
        res_scen1_repeat = requests.post(
            f"{BASE_URL}/api/simulate/tamper",
            json={"meter_id": METER_A, "scenario": "consumption_spike", "sequence_type": "daily"},
            timeout=30,
        )
        assert res_scen1_repeat.status_code == 200, f"simulate-tampering spike repeat failed: {res_scen1_repeat.text}"

        db = fresh_db()
        active_spike_alerts = (
            db.query(AnomalyAlert)
            .filter(
                AnomalyAlert.meter_id == METER_A,
                AnomalyAlert.source_model == "LSTM_Autoencoder",
                AnomalyAlert.fault_type == "SIMULATED_CONSUMPTION_SPIKE",
                AnomalyAlert.is_resolved == False,
            )
            .all()
        )
        assert len(active_spike_alerts) == 1, f"Test 7 FAILED: Duplicate active alert spawned (count={len(active_spike_alerts)})"
        assert active_spike_alerts[0].id == spike_alert_id_before, "Test 7 FAILED: Alert ID changed on repeat"
        print(f"[PASS] Test 7: Repeated consumption_spike evaluation updated existing Alert #{spike_alert_id_before} without duplicating.")
        db.close()

        # -------------------------------------------------------------
        # TEST 8: Normal LSTM simulation resolves relevant LSTM alert only
        # -------------------------------------------------------------
        print("\n--- Running Test 8: Normal LSTM Simulation Isolation ---")
        res_norm_sim = requests.post(
            f"{BASE_URL}/api/simulate/tamper",
            json={"meter_id": METER_A, "scenario": "normal", "sequence_type": "daily"},
            timeout=30,
        )
        assert res_norm_sim.status_code == 200, f"simulate-tampering normal failed: {res_norm_sim.text}"

        db = fresh_db()
        active_lstm_after_norm = (
            db.query(AnomalyAlert)
            .filter(
                AnomalyAlert.meter_id == METER_A,
                AnomalyAlert.source_model == "LSTM_Autoencoder",
                AnomalyAlert.is_resolved == False,
            )
            .all()
        )
        db_rf_after_norm = db.query(AnomalyAlert).filter(AnomalyAlert.id == rf_control_id).first()

        assert len(active_lstm_after_norm) == 0, f"Test 8 FAILED: Simulated LSTM alerts still open: {active_lstm_after_norm}"
        assert db_rf_after_norm.is_resolved is False, "Test 8 FAILED: RF alert was mistakenly resolved by normal LSTM simulation"
        print("[PASS] Test 8: Normal LSTM simulation resolved all simulated LSTM alerts while preserving RF alert.")
        db.close()

        # -------------------------------------------------------------
        # TEST 9: Historical resolved alerts remain queryable via /api/alerts
        # -------------------------------------------------------------
        print("\n--- Running Test 9: Query Historical Resolved Alerts via API ---")
        res_alerts = requests.get(f"{BASE_URL}/api/alerts?meter_id={METER_A}", timeout=10)
        assert res_alerts.status_code == 200, f"GET /api/alerts failed: {res_alerts.text}"
        alerts_data = res_alerts.json()
        items = alerts_data.get("alerts", alerts_data.get("items", alerts_data if isinstance(alerts_data, list) else []))
        assert len(items) > 0, f"Test 9 FAILED: No alerts returned for {METER_A}"

        resolved_items = [it for it in items if it.get("is_resolved") is True]
        active_items = [it for it in items if it.get("is_resolved") is False]
        assert len(resolved_items) >= 2, f"Test 9 FAILED: Expected historical resolved alerts in API response, got {len(resolved_items)}"
        print(f"[PASS] Test 9: API returns complete history for {METER_A} ({len(active_items)} active, {len(resolved_items)} resolved).")

        # -------------------------------------------------------------
        # TEST 10: Verify API returns exact SIMULATED_ prefix
        # -------------------------------------------------------------
        print("\n--- Running Test 10: Verify SIMULATED_ Prefix Preservation ---")
        fault_types_in_api = [it.get("fault_type") for it in items]
        simulated_types = [ft for ft in fault_types_in_api if ft and ft.startswith("SIMULATED_")]
        assert len(simulated_types) >= 2, f"Test 10 FAILED: Expected exact SIMULATED_ prefix in API response, found {fault_types_in_api}"
        print(f"[PASS] Test 10: API preserves exact SIMULATED_ prefix: {simulated_types}")

        print("\n" + "=" * 70)
        print("ALL 10 TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        # CLEANUP FIXTURE & PRESERVE BASELINE
        print("\n[CLEANUP] Purging test fixtures (METER_A, METER_B)...")
        db = fresh_db()
        db.query(AnomalyAlert).filter(AnomalyAlert.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.query(ConsumptionSequence).filter(ConsumptionSequence.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.query(HardwareReading).filter(HardwareReading.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.query(Meter).filter(Meter.meter_id.in_([METER_A, METER_B])).delete(synchronize_session=False)
        db.commit()

        # VERIFY DATABASE BASELINE PRESERVATION
        current_alerts = db.query(AnomalyAlert).all()
        current_tuples = [
            (a.id, a.meter_id, a.source_model, a.fault_type, a.is_resolved)
            for a in current_alerts
        ]
        assert len(current_tuples) == len(baseline_tuples), (
            f"BASELINE VIOLATION: Count mismatch! Expected {len(baseline_tuples)}, found {len(current_tuples)}"
        )
        assert set(current_tuples) == set(baseline_tuples), (
            "BASELINE VIOLATION: Historical alert records were modified or corrupted!"
        )
        print(f"[VERIFIED] Database baseline completely preserved: exactly {len(current_tuples)} historical alerts untouched.")
        db.close()


if __name__ == "__main__":
    run_tests()
