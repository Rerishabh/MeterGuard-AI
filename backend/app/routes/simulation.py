"""
MeterGuard AI: Simulation Management Routes
Exposes API endpoints to inspect simulation status, pause, resume, and restart replay streams.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.services.simulation_service import simulation_manager

router = APIRouter(tags=["Simulation"])


class StartSimulationRequest(BaseModel):
    meter_id: Optional[str] = "M001"
    delay: Optional[float] = 1.0


@router.get("/api/simulation/status")
def get_simulation_status():
    """Returns single source-of-truth status of the managed background replay simulator."""
    return {
        "status": "online",
        "simulation": simulation_manager.get_status(),
    }


@router.post("/api/simulation/start")
async def start_simulation(payload: Optional[StartSimulationRequest] = None):
    """Starts or restarts the background dataset replay simulation."""
    meter_id = payload.meter_id if payload and payload.meter_id else "M001"
    delay = payload.delay if payload and payload.delay is not None else 1.0
    ok = await simulation_manager.start_default_simulation(meter_id=meter_id, delay=delay)
    return {
        "status": "success" if ok else "error",
        "simulation": simulation_manager.get_status(),
    }


@router.post("/api/simulation/pause")
async def pause_simulation():
    """Pauses dataset streaming without tearing down the background task."""
    await simulation_manager.pause_simulation()
    return {
        "status": "success",
        "simulation": simulation_manager.get_status(),
    }


@router.post("/api/simulation/resume")
async def resume_simulation():
    """Resumes paused dataset streaming."""
    await simulation_manager.resume_simulation()
    return {
        "status": "success",
        "simulation": simulation_manager.get_status(),
    }


@router.post("/api/simulation/stop")
async def stop_simulation():
    """Terminates the background replay worker."""
    await simulation_manager.stop_simulation()
    return {
        "status": "success",
        "simulation": simulation_manager.get_status(),
    }
