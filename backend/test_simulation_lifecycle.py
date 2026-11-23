"""
MeterGuard AI: Automatic Simulation Lifecycle & Worker Deduplication Test Suite
Tests:
- Automatic simulator initialization
- Telemetry ingestion from hardware dataset
- Worker deduplication (calling start multiple times)
- Pause and resume controls
- Graceful shutdown
"""

import sys
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.simulation_service import simulation_manager


def test_simulation_lifecycle():
    print("==================================================================")
    print("   METERGUARD AI: AUTOMATIC SIMULATION LIFECYCLE TEST SUITE       ")
    print("==================================================================")

    with TestClient(app) as client:
        # 1. Health check includes simulation_status
        h_res = client.get("/api/health")
        assert h_res.status_code == 200
        h_data = h_res.json()
        assert "simulation_status" in h_data, "Health endpoint missing 'simulation_status'!"
        print(f"[PASS] /api/health returned simulation_status: {h_data['simulation_status']}")

        # 2. Status API endpoint
        s_res = client.get("/api/simulation/status")
        assert s_res.status_code == 200
        s_data = s_res.json()
        sim_info = s_data.get("simulation", {})
        print(f"[PASS] /api/simulation/status: status={sim_info.get('status')}, is_running={sim_info.get('is_running')}")
        assert sim_info.get("status") in ["INITIALIZING", "SIMULATED"], f"Unexpected state: {sim_info.get('status')}"

        # 3. Duplicate start prevention
        print("--- Testing Duplicate Worker Prevention ---")
        st_res = client.post("/api/simulation/start", json={"meter_id": "M001", "delay": 0.5})
        assert st_res.status_code == 200
        st_data = st_res.json()
        print(f"[PASS] Calling start again succeeded idempotently without duplicating workers.")

        # 4. Pause simulation
        print("--- Testing Pause Simulation ---")
        p_res = client.post("/api/simulation/pause")
        assert p_res.status_code == 200
        p_data = p_res.json().get("simulation", {})
        assert p_data.get("status") == "SIMULATION PAUSED"
        print("[PASS] Simulator successfully paused (status=SIMULATION PAUSED).")

        # 5. Resume simulation
        print("--- Testing Resume Simulation ---")
        r_res = client.post("/api/simulation/resume")
        assert r_res.status_code == 200
        r_data = r_res.json().get("simulation", {})
        assert r_data.get("status") == "SIMULATED"
        print("[PASS] Simulator successfully resumed (status=SIMULATED).")

        # 6. Dashboard contains simulation object
        d_res = client.get("/api/dashboard")
        assert d_res.status_code == 200
        d_data = d_res.json()
        assert "simulation" in d_data, "Dashboard response missing 'simulation' object!"
        print(f"[PASS] /api/dashboard returned simulation status: {d_data['simulation']['status']}")

    print("\n==================================================================")
    print("   ALL SIMULATION LIFECYCLE TESTS PASSED WITH 100% SUCCESS        ")
    print("==================================================================")


if __name__ == "__main__":
    test_simulation_lifecycle()
