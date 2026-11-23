"""
MeterGuard AI: Health Check & System Status Routes
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.services.ml_engine import ml_engine
from backend.app.services.simulation_service import simulation_manager
from backend.database.session import check_db_connection, SessionLocal
from backend.app.models.db_models import Meter

router = APIRouter(tags=["Health"])


@router.get("/")
def home():
    """Service status and health banner matching Flask root endpoint."""
    return {
        "status": "online",
        "service": "MeterGuard AI Monitoring Backend (FastAPI)",
        "message": "Backend is running.",
        "simulation_status": simulation_manager.get_status()["status"],
    }


@router.get("/api/health")
def api_health():
    """
    Health status, loaded ML model indicators, active meter count,
    and database connectivity state.
    Queries actual MySQL count when connected; handles disconnection gracefully.
    """
    db_connected, _ = check_db_connection()

    meter_count = None
    if db_connected and SessionLocal is not None:
        db = SessionLocal()
        try:
            meter_count = db.query(Meter).count()
        except Exception:
            meter_count = len(ml_engine.latest_meter_data) if ml_engine.latest_meter_data else None
        finally:
            db.close()
    elif ml_engine.latest_meter_data:
        meter_count = len(ml_engine.latest_meter_data)

    sim_info = simulation_manager.get_status()

    return {
        "status": "online",
        "model1_loaded": ml_engine.model1 is not None,
        "model2_loaded": ml_engine.model2 is not None,
        "lstm_daily_available": ml_engine.daily_lstm is not None,
        "lstm_hourly_available": ml_engine.hourly_lstm is not None,
        "database_connected": bool(db_connected),
        "meter_count": meter_count,
        "simulation_status": sim_info["status"],
        "simulation": sim_info,
    }
