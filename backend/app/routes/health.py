"""
MeterGuard AI: Health Check & System Status Routes
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.services.ml_engine import ml_engine
from backend.database.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/")
def home():
    """Service status and health banner matching Flask root endpoint."""
    return {
        "status": "online",
        "service": "MeterGuard AI Monitoring Backend (FastAPI)",
        "message": "Backend is running.",
    }


@router.get("/api/health")
def api_health():
    """
    Health status, loaded ML model indicators, active meter count,
    and database connectivity state.
    """
    db_connected, _ = check_db_connection()

    return {
        "status": "online",
        "model1_loaded": ml_engine.model1 is not None,
        "model2_loaded": ml_engine.model2 is not None,
        "lstm_daily_available": ml_engine.daily_lstm is not None,
        "lstm_hourly_available": ml_engine.hourly_lstm is not None,
        "database_connected": bool(db_connected),
        "meter_count": len(ml_engine.latest_meter_data),
    }
