"""
MeterGuard AI: Routes Package
"""

from backend.app.routes.health import router as health_router
from backend.app.routes.telemetry import router as telemetry_router
from backend.app.routes.anomaly import router as anomaly_router
from backend.app.routes.dashboard import router as dashboard_router
from backend.app.routes.reports import router as reports_router
from backend.app.routes.simulation import router as simulation_router

__all__ = [
    "health_router",
    "telemetry_router",
    "anomaly_router",
    "dashboard_router",
    "reports_router",
    "simulation_router",
]
