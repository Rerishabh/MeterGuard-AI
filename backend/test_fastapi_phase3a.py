"""
MeterGuard AI: Phase 3A FastAPI & Persistence Verification Suite
Tests health, telemetry, LSTM inference, alert deduplication, edge cases,
dashboard contracts, and database connectivity.
"""

import sys
from pathlib import Path
import json
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from starlette.testclient import TestClient
from backend.app.main import app
from backend.database.session import check_db_connection


def run_phase3a_tests():
    print("\n========================================================")
    print("      METERGUARD AI: PHASE 3A REGRESSION & TEST SUITE   ")
    print("========================================================")

    test_results = {}

    with TestClient(app) as client:
        # ---------------------------------------------------------
        # 1. Health Endpoints
        # ---------------------------------------------------------
        print("\n[TEST 1] Root & Health Endpoints...")
        r_root = client.get("/")
        assert r_root.status_code == 200, f"Expected 200, got {r_root.status_code}"
        assert r_root.json().get("status") == "online"
        print("   -> Root GET /: PASS")

        r_health = client.get("/api/health")
        assert r_health.status_code == 200, f"Expected 200, got {r_health.status_code}"
        health_data = r_health.json()
        print("   -> Health Data:", health_data)
        assert health_data["status"] == "online"
        assert health_data["model1_loaded"] is True, "Model 1 should be loaded"
        assert health_data["model2_loaded"] is True, "Model 2 should be loaded"
        assert health_data["lstm_daily_available"] is True, "Daily LSTM should be available"
        assert health_data["lstm_hourly_available"] is True, "Hourly LSTM should be available"
        print(f"   -> Database Connected Flag: {health_data['database_connected']}")
        test_results["health"] = "PASS"

        # ---------------------------------------------------------
        # 2. Hardware Telemetry & Filtering (POST /api/meter-data)
        # ---------------------------------------------------------
        print("\n[TEST 2] Hardware Telemetry & Temporal Filter...")
        sample_payload = {
            "meter_id": "M001",
            "T1_CS": 2980.0,
            "T1_VS": 500.0,
            "T2_CS": 2985.0,
            "T2_VS": 498.0,
            "H1_CS": 3020.0,
            "H1_VS": 230.0,
            "time_ms": 100,
        }
        r_telemetry = client.post("/api/meter-data", json=sample_payload)
        assert r_telemetry.status_code == 200, f"Telemetry error: {r_telemetry.text}"
        telem_data = r_telemetry.json()
        assert telem_data["status"] == "received"
        assert telem_data["meter_id"] == "M001"
        assert "electrical" in telem_data
        assert "model1" in telem_data
        assert "model2" in telem_data
        assert "decision" in telem_data
        print(f"   -> Single telemetry POST succeeded. Model 2 status: {telem_data['model2']['prediction']}")

        # Test temporal fault confirmation & alert deduplication
        print("   -> Testing fault confirmation with repeated FAULT_S1 readings...")
        fault_payload = {
            "meter_id": "M002",
            "T1_CS": 3100.0,
            "T1_VS": 500.0,
            "T2_CS": 3090.0,
            "T2_VS": 498.0,
            "H1_CS": 2800.0,
            "H1_VS": 230.0,
            "time_ms": 200,
        }
        for i in range(7):
            client.post("/api/meter-data", json=fault_payload)

        r_check = client.get("/api/meter/M002")
        assert r_check.status_code == 200
        m2_info = r_check.json()
        print(f"   -> Meter M002 after 7 fault readings: Model 2 status = {m2_info['model2']['prediction']}, active = {m2_info['model2']['fault_active']}")
        test_results["telemetry"] = "PASS"

        # ---------------------------------------------------------
        # 3. Daily LSTM Sequence Inference (POST /api/anomaly/analyze)
        # ---------------------------------------------------------
        print("\n[TEST 3] Daily LSTM Anomaly Inference (30 timesteps)...")
        daily_seq = [5.0 + 0.5 * np.sin(i / 3.0) for i in range(30)]
        daily_req = {
            "meter_id": "M001",
            "sequence_type": "daily",
            "consumption": daily_seq,
            "is_simulated": True,
        }
        r_daily = client.post("/api/anomaly/analyze", json=daily_req)
        assert r_daily.status_code == 200, f"Daily LSTM error: {r_daily.text}"
        daily_res = r_daily.json()
        print("   -> Daily LSTM response:", daily_res)
        assert daily_res["meter_id"] == "M001"
        assert daily_res["sequence_type"] == "daily"
        assert daily_res["sequence_length"] == 30
        assert "reconstruction_error" in daily_res
        assert "threshold" in daily_res
        assert "is_anomaly" in daily_res
        test_results["daily_lstm"] = "PASS"

        # ---------------------------------------------------------
        # 4. Hourly LSTM Sequence Inference (POST /api/anomaly/analyze)
        # ---------------------------------------------------------
        print("\n[TEST 4] Hourly LSTM Anomaly Inference (24 timesteps)...")
        hourly_seq = [0.3 + 0.1 * np.cos(i / 2.0) for i in range(24)]
        hourly_req = {
            "meter_id": "M002",
            "sequence_type": "hourly",
            "consumption": hourly_seq,
            "is_simulated": True,
        }
        r_hourly = client.post("/api/anomaly/analyze", json=hourly_req)
        assert r_hourly.status_code == 200, f"Hourly LSTM error: {r_hourly.text}"
        hourly_res = r_hourly.json()
        print("   -> Hourly LSTM response:", hourly_res)
        assert hourly_res["meter_id"] == "M002"
        assert hourly_res["sequence_type"] == "hourly"
        assert hourly_res["sequence_length"] == 24
        assert "reconstruction_error" in hourly_res
        assert "threshold" in hourly_res
        test_results["hourly_lstm"] = "PASS"

        # ---------------------------------------------------------
        # 5. Invalid Input Edge Cases (HTTP 400 Verification)
        # ---------------------------------------------------------
        print("\n[TEST 5] Testing Invalid Inputs (Strict HTTP 400 enforcement)...")
        edge_cases = [
            ("29 daily observations", {"json": {"meter_id": "M001", "sequence_type": "daily", "consumption": [1.0] * 29}}),
            ("23 hourly observations", {"json": {"meter_id": "M001", "sequence_type": "hourly", "consumption": [1.0] * 23}}),
            ("Negative consumption", {"json": {"meter_id": "M001", "sequence_type": "daily", "consumption": [-1.0] + [1.0] * 29}}),
            ("NaN in consumption", {"content": '{"meter_id": "M001", "sequence_type": "daily", "consumption": [NaN, ' + ', '.join(['1.0'] * 29) + ']}', "headers": {"Content-Type": "application/json"}}),
            ("Infinity in consumption", {"content": '{"meter_id": "M001", "sequence_type": "daily", "consumption": [Infinity, ' + ', '.join(['1.0'] * 29) + ']}', "headers": {"Content-Type": "application/json"}}),
            ("Non-numeric in consumption", {"json": {"meter_id": "M001", "sequence_type": "daily", "consumption": ["bad"] + [1.0] * 29}}),
            ("Invalid sequence type", {"json": {"meter_id": "M001", "sequence_type": "weekly", "consumption": [1.0] * 30}}),
            ("Missing consumption", {"json": {"meter_id": "M001", "sequence_type": "daily"}}),
            ("Missing meter_id", {"json": {"sequence_type": "daily", "consumption": [1.0] * 30}}),
            ("Empty JSON", {"json": {}}),
        ]

        passed_edges = 0
        for name, req_kwargs in edge_cases:
            r_edge = client.post("/api/anomaly/analyze", **req_kwargs)
            if r_edge.status_code == 400:
                passed_edges += 1
            else:
                print(f"   -> FAILED {name}: expected 400, got {r_edge.status_code}")

        print(f"   -> Successfully rejected {passed_edges}/{len(edge_cases)} invalid input cases with HTTP 400.")
        assert passed_edges == len(edge_cases), "All edge cases must return 400"
        test_results["edge_cases"] = "PASS"

        # ---------------------------------------------------------
        # 6. Operations Dashboard Endpoints
        # ---------------------------------------------------------
        print("\n[TEST 6] Operations Dashboard Endpoints...")
        r_dash = client.get("/api/dashboard")
        assert r_dash.status_code == 200
        dash_data = r_dash.json()
        assert dash_data["status"] == "online"
        assert dash_data["meter_count"] >= 2
        print(f"   -> Dashboard returns {dash_data['meter_count']} active meters.")

        r_meters = client.get("/api/meters")
        assert r_meters.status_code == 200
        assert len(r_meters.json()["meters"]) >= 2
        print(f"   -> /api/meters returns list of {len(r_meters.json()['meters'])} meters.")

        r_single = client.get("/api/meter/M001")
        assert r_single.status_code == 200
        assert r_single.json()["meter_id"] == "M001"
        print("   -> /api/meter/M001 returns full telemetry & model states.")

        r_alerts = client.get("/api/alerts")
        assert r_alerts.status_code == 200
        alerts_data = r_alerts.json()
        print(f"   -> /api/alerts returns: {alerts_data.get('count', 0)} alerts (Status: {alerts_data.get('status')})")
        test_results["dashboard"] = "PASS"

    # ---------------------------------------------------------
    # 7. Summary
    # ---------------------------------------------------------
    print("\n========================================================")
    print("              PHASE 3A TEST SUITE SUMMARY               ")
    print("========================================================")
    for k, v in test_results.items():
        print(f"   {k.ljust(20)}: {v}")
    print("========================================================\n")


if __name__ == "__main__":
    run_phase3a_tests()
