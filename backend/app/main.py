"""
MeterGuard AI: Primary FastAPI Application
Modular, asynchronous backend with MySQL persistence, SQLAlchemy, Alembic, and Pydantic.
Preserves complete compatibility with existing React frontend and replay simulator.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure PROJECT_ROOT is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.services.ml_engine import ml_engine
from backend.app.services.simulation_service import simulation_manager
from backend.database.session import check_db_connection
from backend.app.routes import (
    health_router,
    telemetry_router,
    anomaly_router,
    dashboard_router,
    reports_router,
    simulation_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes ML models, verifies database connectivity, and starts
    the default automatic dataset replay simulation worker.
    """
    print("\n==========================================")
    print("   METERGUARD AI FASTAPI SERVER STARTUP   ")
    print("==========================================")

    # 1. Load ML models (Isolation Forest, Random Forest, Daily & Hourly LSTM)
    ml_engine.load_all_models()

    # 2. Check Database Connectivity
    db_ok, db_err = check_db_connection()
    if db_ok:
        print("[DATABASE] Successfully connected to MySQL at:", settings.DATABASE_URL.split("@")[-1])
    else:
        print("[DATABASE WARNING] MySQL connectivity check failed:", db_err)
        print("                 API will continue running; DB operations will fail gracefully.")

    # 3. Automatically start managed background dataset simulation
    await simulation_manager.start_default_simulation()
    print("[SIMULATION] Background dataset replay worker initialized automatically.")

    print(f"[FASTAPI] Listening on http://{settings.API_HOST}:{settings.API_PORT}")
    print("==========================================\n")
    yield
    print("\n[FASTAPI] MeterGuard AI server shutting down cleanly.")
    await simulation_manager.stop_simulation()
    print("[SIMULATION] Background simulation worker cleanly stopped.")


app = FastAPI(
    title="MeterGuard AI: Utility Meter Tampering Detector",
    description="Asynchronous full-stack AI system for real-time electrical tampering detection and sequential anomaly analysis.",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS Middleware (matching Flask CORS setup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(telemetry_router)
app.include_router(anomaly_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(simulation_router)


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )
