"""
MeterGuard AI: Complete Backend Verification & Regression Suite
Tests:
1. Health endpoint (all model flags)
2. Daily LSTM valid inference
3. Hourly LSTM valid inference
4. 10 edge-case invalid input rejections (HTTP 400)
5. Existing hardware telemetry (Model 1 & Model 2 preserved, LSTM reports AWAITING without time mismatch)
6. Dashboard aggregation and single meter retrieval
"""

import sys
import math
from pathlib import Path

# Add backend to path and explicitly load Flask app from backend/app.py
import importlib.util

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))
spec = importlib.util.spec_from_file_location("flask_app_module", str(backend_dir / "app.py"))
flask_app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flask_app_module)
app = flask_app_module.app

client = app.test_client()

print("====================================================")
print("   TASK 5: BACKEND VERIFICATION & REGRESSION SUITE  ")
print("====================================================")

# 1. Health Endpoint
res = client.get("/api/health")
print("1. GET /api/health:", res.status_code, res.get_json())
assert res.status_code == 200
h = res.get_json()
assert h["status"] == "online"
assert h["model1_loaded"] is True
assert h["model2_loaded"] is True
assert h["lstm_daily_available"] is True
assert h["lstm_hourly_available"] is True
print("   -> PASS: Health endpoint verified.")

# 2. Daily LSTM Valid Inference (30 values)
valid_daily = [
    5.1, 4.8, 5.3, 5.0, 4.9, 5.2, 5.4, 5.1, 4.7, 5.0,
    5.3, 5.1, 4.8, 5.2, 5.0, 5.4, 5.1, 4.9, 5.2, 5.0,
    5.3, 5.1, 4.8, 5.2, 5.0, 5.4, 5.1, 4.9, 5.2, 5.0
]
res = client.post("/api/anomaly/analyze", json={
    "meter_id": "M001",
    "sequence_type": "daily",
    "consumption": valid_daily
})
print("\n2. POST /api/anomaly/analyze (Daily Valid):", res.status_code, res.get_json())
assert res.status_code == 200
d_res = res.get_json()
assert d_res["status"] in ["NORMAL", "SUSPICIOUS"]
assert d_res["sequence_type"] == "daily"
assert d_res["sequence_length"] == 30
assert isinstance(d_res["reconstruction_error"], float)
assert isinstance(d_res["threshold"], float)
print("   -> PASS: Valid daily inference succeeded.")

# 3. Hourly LSTM Valid Inference (24 values)
valid_hourly = [
    0.2, 0.1, 0.1, 0.1, 0.2, 0.3, 0.5, 0.8,
    0.6, 0.4, 0.3, 0.3, 0.4, 0.5, 0.6, 0.7,
    0.9, 1.2, 1.4, 1.1, 0.8, 0.6, 0.4, 0.3
]
res = client.post("/api/anomaly/analyze", json={
    "meter_id": "M002",
    "sequence_type": "hourly",
    "consumption": valid_hourly
})
print("\n3. POST /api/anomaly/analyze (Hourly Valid):", res.status_code, res.get_json())
assert res.status_code == 200
h_res = res.get_json()
assert h_res["status"] in ["NORMAL", "SUSPICIOUS"]
assert h_res["sequence_type"] == "hourly"
assert h_res["sequence_length"] == 24
assert isinstance(h_res["reconstruction_error"], float)
print("   -> PASS: Valid hourly inference succeeded.")

# 4. Invalid Input Tests (All must return HTTP 400)
invalid_cases = [
    ("Incorrect daily length (29 values)", {"meter_id": "M001", "sequence_type": "daily", "consumption": valid_daily[:29]}),
    ("Incorrect hourly length (23 values)", {"meter_id": "M001", "sequence_type": "hourly", "consumption": valid_hourly[:23]}),
    ("Invalid sequence type (monthly)", {"meter_id": "M001", "sequence_type": "monthly", "consumption": valid_daily}),
    ("Missing consumption field", {"meter_id": "M001", "sequence_type": "daily"}),
    ("Non-numeric string value in array", {"meter_id": "M001", "sequence_type": "daily", "consumption": ["bad"] + valid_daily[1:]}),
    ("NaN value in array", {"meter_id": "M001", "sequence_type": "daily", "consumption": [float("nan")] + valid_daily[1:]}),
    ("Infinity value in array", {"meter_id": "M001", "sequence_type": "daily", "consumption": [float("inf")] + valid_daily[1:]}),
    ("Negative consumption value (-2.5)", {"meter_id": "M001", "sequence_type": "daily", "consumption": [-2.5] + valid_daily[1:]}),
    ("Empty meter_id", {"meter_id": "   ", "sequence_type": "daily", "consumption": valid_daily}),
    ("Empty JSON payload", {})
]

print("\n4. Invalid Input Edge-Case Tests:")
for desc, payload in invalid_cases:
    res = client.post("/api/anomaly/analyze", json=payload)
    msg = res.get_json().get("message")
    print(f"   - {desc}: HTTP {res.status_code} -> {msg}")
    assert res.status_code == 400

print("   -> PASS: All 10 invalid input cases correctly rejected with HTTP 400.")

# 5. Existing Endpoint Regression Tests
print("\n5. Existing Telemetry Endpoints & Dashboard Regression:")
# Post hardware sensor data for M003 (never analyzed via /api/anomaly/analyze)
hw_payload = {
    "meter_id": "M003",
    "T1_CS": 3015.0, "T1_VS": 230.0,
    "T2_CS": 3015.0, "T2_VS": 230.0,
    "H1_CS": 3015.0, "H1_VS": 230.0,
    "time_ms": 500
}
res_hw = client.post("/api/meter-data", json=hw_payload)
assert res_hw.status_code == 200
hw_res = res_hw.get_json()
print("   - POST /api/meter-data for M003:")
print("     Model 1:", hw_res["model1"]["prediction"])
print("     Model 2:", hw_res["model2"]["prediction"])
print("     LSTM status:", hw_res["lstm"]["status"])
assert hw_res["lstm"]["status"] == "AWAITING SUFFICIENT HISTORY"
assert hw_res["lstm"]["reconstruction_error"] is None

# Verify dashboard contains M001 (has analyzed LSTM), M002 (has analyzed LSTM), and M003 (awaiting)
res_dash = client.get("/api/dashboard")
assert res_dash.status_code == 200
dash_meters = {m["meter_id"]: m for m in res_dash.get_json()["meters"]}
print("   - GET /api/dashboard meter count:", len(dash_meters))
assert "M001" in dash_meters and dash_meters["M001"]["lstm"]["status"] in ["NORMAL", "SUSPICIOUS"]
assert "M002" in dash_meters and dash_meters["M002"]["lstm"]["status"] in ["NORMAL", "SUSPICIOUS"]
assert "M003" in dash_meters and dash_meters["M003"]["lstm"]["status"] == "AWAITING SUFFICIENT HISTORY"

# Verify single meter endpoint
res_m1 = client.get("/api/meter/M001")
assert res_m1.status_code == 200
assert res_m1.get_json()["meter_id"] == "M001"

# Verify /api/meters list
res_list = client.get("/api/meters")
assert res_list.status_code == 200
assert len(res_list.get_json()["meters"]) >= 3

print("   -> PASS: Existing endpoints and dashboard reactivity fully verified without regressions.")
print("\n====================================================")
print("  ALL VERIFICATION TESTS COMPLETED WITH 100% PASS   ")
print("====================================================")
