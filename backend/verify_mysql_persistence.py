"""
MeterGuard AI: Actual MySQL Persistence & Deduplication Verification
Uses FastAPI TestClient to invoke endpoints and queries MySQL directly via SQLAlchemy
to verify database tables, foreign keys, record persistence, and alert deduplication.
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from backend.app.main import app
from backend.database.session import engine, SessionLocal
from backend.app.models.db_models import (
    Meter,
    HardwareReading,
    ConsumptionSequence,
    AnomalyAlert,
)


def run_actual_persistence_tests():
    print("==================================================================")
    print("      METERGUARD AI: ACTUAL MYSQL PERSISTENCE VERIFICATION        ")
    print("==================================================================")

    # 1. Direct Engine & Database Verification
    print("\n[STEP 1] Direct MySQL Database Verification...")
    db = SessionLocal()
    try:
        # Clean up any previous test meters
        test_meter_ids = ["M_TEST_01", "M_TEST_02", "M_TEST_03"]
        db.query(Meter).filter(Meter.meter_id.in_(test_meter_ids)).delete(synchronize_session=False)
        db.commit()
        print("   -> Cleaned up any existing test meter artifacts in MySQL.")
    except Exception as exc:
        print(f"   -> DB Prep Exception: {exc}")
    finally:
        db.close()

    with TestClient(app) as client:
        # -------------------------------------------------------------
        # TEST 1 & 2: Meter and Hardware Reading Persistence
        # -------------------------------------------------------------
        print("\n[STEP 2] Testing Telemetry Ingestion & Hardware Reading Persistence...")
        hw_payload = {
            "meter_id": "M_TEST_01",
            "T1_CS": 3010.5,
            "T1_VS": 499.2,
            "T2_CS": 3008.1,
            "T2_VS": 498.7,
            "H1_CS": 3025.4,
            "H1_VS": 230.1,
            "time_ms": 1500,
        }
        res_hw = client.post("/api/meter-data", json=hw_payload)
        assert res_hw.status_code == 200, f"Hardware POST failed: {res_hw.text}"
        print("   -> POST /api/meter-data returned 200 OK.")

        # Query MySQL directly for Meter
        db = SessionLocal()
        try:
            meter_row = db.query(Meter).filter(Meter.meter_id == "M_TEST_01").first()
            assert meter_row is not None, "Meter 'M_TEST_01' NOT FOUND in MySQL!"
            print(f"   [VERIFIED IN MYSQL] Meter row created: id={meter_row.id}, meter_id='{meter_row.meter_id}', status='{meter_row.status}'")

            # Query MySQL directly for HardwareReading
            hw_row = (
                db.query(HardwareReading)
                .filter(HardwareReading.meter_id == "M_TEST_01")
                .first()
            )
            assert hw_row is not None, "HardwareReading NOT FOUND in MySQL!"
            print(f"   [VERIFIED IN MYSQL] Hardware reading persisted: id={hw_row.id}, h1_cs={hw_row.h1_cs}, power_w={hw_row.power_w}")
        finally:
            db.close()

        # -------------------------------------------------------------
        # TEST 3: Valid Daily Consumption Sequence Persistence
        # -------------------------------------------------------------
        print("\n[STEP 3] Testing Valid Daily Consumption Sequence Persistence...")
        daily_seq = [4.5 + 0.2 * np.sin(i / 2.0) for i in range(30)]
        daily_req = {
            "meter_id": "M_TEST_01",
            "sequence_type": "daily",
            "consumption": daily_seq,
            "is_simulated": True,
        }
        res_daily = client.post("/api/anomaly/analyze", json=daily_req)
        assert res_daily.status_code == 200, f"Daily analyze failed: {res_daily.text}"
        print("   -> POST /api/anomaly/analyze (daily) returned 200 OK.")

        db = SessionLocal()
        try:
            seq_row = (
                db.query(ConsumptionSequence)
                .filter(
                    ConsumptionSequence.meter_id == "M_TEST_01",
                    ConsumptionSequence.sequence_type == "daily",
                )
                .first()
            )
            assert seq_row is not None, "Daily ConsumptionSequence NOT FOUND in MySQL!"
            print(f"   [VERIFIED IN MYSQL] Daily sequence persisted: id={seq_row.id}, type='{seq_row.sequence_type}', error={seq_row.reconstruction_error}, is_anomaly={seq_row.is_anomaly}")
        finally:
            db.close()

        # -------------------------------------------------------------
        # TEST 4: Valid Hourly Consumption Sequence Persistence
        # -------------------------------------------------------------
        print("\n[STEP 4] Testing Valid Hourly Consumption Sequence Persistence...")
        hourly_seq = [0.35 + 0.05 * np.cos(i / 2.0) for i in range(24)]
        hourly_req = {
            "meter_id": "M_TEST_01",
            "sequence_type": "hourly",
            "consumption": hourly_seq,
            "is_simulated": True,
        }
        res_hourly = client.post("/api/anomaly/analyze", json=hourly_req)
        assert res_hourly.status_code == 200, f"Hourly analyze failed: {res_hourly.text}"
        print("   -> POST /api/anomaly/analyze (hourly) returned 200 OK.")

        db = SessionLocal()
        try:
            h_row = (
                db.query(ConsumptionSequence)
                .filter(
                    ConsumptionSequence.meter_id == "M_TEST_01",
                    ConsumptionSequence.sequence_type == "hourly",
                )
                .first()
            )
            assert h_row is not None, "Hourly ConsumptionSequence NOT FOUND in MySQL!"
            print(f"   [VERIFIED IN MYSQL] Hourly sequence persisted: id={h_row.id}, type='{h_row.sequence_type}', error={h_row.reconstruction_error}, is_anomaly={h_row.is_anomaly}")
        finally:
            db.close()

        # -------------------------------------------------------------
        # TEST 5: Anomaly Detection & Anomaly Alert Persistence
        # -------------------------------------------------------------
        print("\n[STEP 5] Testing Anomaly Detection & Alert Persistence...")
        # Extreme anomaly sequence (huge spike) to guarantee error exceeds 0.013 threshold
        anom_seq = [50.0] * 30
        anom_req = {
            "meter_id": "M_TEST_02",
            "sequence_type": "daily",
            "consumption": anom_seq,
            "is_simulated": True,
        }
        res_anom = client.post("/api/anomaly/analyze", json=anom_req)
        assert res_anom.status_code == 200
        anom_json = res_anom.json()
        assert anom_json["is_anomaly"] is True, "Expected is_anomaly=True for extreme spike!"
        print(f"   -> Anomaly confirmed by LSTM: reconstruction_error={anom_json['reconstruction_error']}, threshold={anom_json['threshold']}")

        db = SessionLocal()
        try:
            alert_row = (
                db.query(AnomalyAlert)
                .filter(AnomalyAlert.meter_id == "M_TEST_02")
                .first()
            )
            assert alert_row is not None, "AnomalyAlert NOT FOUND in MySQL for M_TEST_02!"
            print(f"   [VERIFIED IN MYSQL] Anomaly alert persisted: id={alert_row.id}, source='{alert_row.source_model}', severity='{alert_row.severity}', message='{alert_row.message}'")
        finally:
            db.close()

        # -------------------------------------------------------------
        # TEST 6: Alert Deduplication & Resolution
        # -------------------------------------------------------------
        print("\n[STEP 6] Testing Alert Deduplication Across Repeated Fault Readings...")
        fault_payload = {
            "meter_id": "M_TEST_03",
            "T1_CS": 3120.0,
            "T1_VS": 500.0,
            "T2_CS": 3110.0,
            "T2_VS": 498.0,
            "H1_CS": 2800.0,
            "H1_VS": 230.0,
            "time_ms": 100,
        }

        # Send 7 readings to trigger and confirm fault (FAULT_CONFIRM_COUNT = 6)
        for i in range(7):
            client.post("/api/meter-data", json=fault_payload)

        db = SessionLocal()
        try:
            alerts_count_initial = (
                db.query(AnomalyAlert)
                .filter(
                    AnomalyAlert.meter_id == "M_TEST_03",
                    AnomalyAlert.is_resolved == False,
                )
                .count()
            )
            assert alerts_count_initial == 1, f"Expected exactly 1 active alert, got {alerts_count_initial}!"
            print(f"   -> Fault confirmed. Unresolved alerts count in MySQL = {alerts_count_initial}")
        finally:
            db.close()

        # Send 15 MORE fault readings (simulating continuous 100ms hardware streaming)
        print("   -> Streaming 15 additional continuous fault readings...")
        for i in range(15):
            client.post("/api/meter-data", json=fault_payload)

        db = SessionLocal()
        try:
            alerts_count_after = (
                db.query(AnomalyAlert)
                .filter(
                    AnomalyAlert.meter_id == "M_TEST_03",
                    AnomalyAlert.is_resolved == False,
                )
                .count()
            )
            assert alerts_count_after == 1, f"DEDUPLICATION FAILED! Found {alerts_count_after} alerts instead of 1!"
            print(f"   [VERIFIED DEDUPLICATION IN MYSQL] After 22 total fault readings, active alert count is still {alerts_count_after} (NO duplicate rows created).")
        finally:
            db.close()

        # Now send 6 consecutive NORMAL readings to verify auto-clearing and alert resolution
        print("   -> Sending 6 consecutive normal readings to test hysteresis fault clearing...")
        normal_payload = {
            "meter_id": "M_TEST_03",
            "T1_CS": 3000.0,
            "T1_VS": 500.0,
            "T2_CS": 3000.0,
            "T2_VS": 500.0,
            "H1_CS": 3000.0,
            "H1_VS": 230.0,
            "time_ms": 2500,
        }
        for i in range(6):
            client.post("/api/meter-data", json=normal_payload)

        db = SessionLocal()
        try:
            active_after_clear = (
                db.query(AnomalyAlert)
                .filter(
                    AnomalyAlert.meter_id == "M_TEST_03",
                    AnomalyAlert.is_resolved == False,
                )
                .count()
            )
            assert active_after_clear == 0, f"Expected 0 active alerts after clear, got {active_after_clear}!"
            resolved_count = (
                db.query(AnomalyAlert)
                .filter(
                    AnomalyAlert.meter_id == "M_TEST_03",
                    AnomalyAlert.is_resolved == True,
                )
                .count()
            )
            assert resolved_count == 1, "Expected alert to be marked is_resolved=True!"
            print(f"   [VERIFIED RESOLUTION IN MYSQL] Alert for M_TEST_03 was cleanly marked is_resolved=True (Active count: {active_after_clear}, Resolved count: {resolved_count}).")
        finally:
            db.close()

        # -------------------------------------------------------------
        # TEST 7: Dashboard Verification from MySQL
        # -------------------------------------------------------------
        print("\n[STEP 7] Dashboard Verification (Retrieval from MySQL)...")
        r_dash = client.get("/api/dashboard")
        assert r_dash.status_code == 200
        dash = r_dash.json()
        assert dash.get("source") == "mysql", f"Expected source='mysql', got {dash.get('source')}"
        assert dash.get("meter_count") >= 3
        print(f"   [VERIFIED IN MYSQL] GET /api/dashboard returns source='{dash.get('source')}' with {dash.get('meter_count')} meters.")

        r_meters = client.get("/api/meters")
        assert r_meters.status_code == 200
        m_list = r_meters.json()
        assert m_list.get("source") == "mysql", f"Expected source='mysql', got {m_list.get('source')}"
        print(f"   [VERIFIED IN MYSQL] GET /api/meters returns source='{m_list.get('source')}' with {len(m_list.get('meters', []))} meters.")

        r_single = client.get("/api/meter/M_TEST_01")
        assert r_single.status_code == 200
        single_data = r_single.json()
        assert single_data["meter_id"] == "M_TEST_01"
        assert single_data["electrical"]["voltage_V"] == 230.1
        print(f"   [VERIFIED IN MYSQL] GET /api/meter/M_TEST_01 retrieved from MySQL records (voltage={single_data['electrical']['voltage_V']} V).")

        r_alerts = client.get("/api/alerts")
        assert r_alerts.status_code == 200
        alerts_res = r_alerts.json()
        assert alerts_res.get("source") == "mysql"
        assert alerts_res.get("count") >= 2
        print(f"   [VERIFIED IN MYSQL] GET /api/alerts returns source='{alerts_res.get('source')}' with {alerts_res.get('count')} total alerts.")

    print("\n==================================================================")
    print("      ALL ACTUAL MYSQL PERSISTENCE TESTS PASSED WITH 100% SUCCESS  ")
    print("==================================================================")


if __name__ == "__main__":
    run_actual_persistence_tests()

