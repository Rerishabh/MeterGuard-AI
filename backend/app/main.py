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
from sqlalchemy.engine.url import make_url

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

    # 2. Check Database Connectivity (credentials masked safely)
    db_ok, db_err = check_db_connection()
    if db_ok:
        try:
            masked_url = make_url(settings.DATABASE_URL).render_as_string(hide_password=True)
            print(f"[DATABASE] Successfully connected to database: {masked_url}")
        except Exception:
            print("[DATABASE] Successfully connected to database.")
    else:
        print("[DATABASE WARNING] Database connectivity check failed. Check DATABASE_URL configuration.")
        print("                 API will continue running; DB operations will fail gracefully.")

    # 3. Automatically start managed background dataset simulation
    await simulation_manager.start_default_simulation()
    print("[SIMULATION] Background dataset replay worker initialized automatically.")

    print(f"[FASTAPI] Listening on http://{settings.API_HOST}:{settings.effective_port}")
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

# Explicit CORS origins: Never use wildcard ["*"] with allow_credentials=True
DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

configured_origins = []
if settings.CORS_ORIGINS and settings.CORS_ORIGINS.strip() != "*":
    configured_origins = [
        o.strip().rstrip("/")
        for o in settings.CORS_ORIGINS.split(",")
        if o.strip()
    ]

# Merge explicit origins preserving localhost development while supporting Cloudflare Pages
allowed_origins = list(dict.fromkeys(DEFAULT_DEV_ORIGINS + configured_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
        port=settings.effective_port,
        reload=False,
    )
