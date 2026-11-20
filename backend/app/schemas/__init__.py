"""
MeterGuard AI: Schemas Package
"""

from backend.app.schemas.telemetry import TelemetryInput
from backend.app.schemas.anomaly import AnomalyAnalyzeRequest, AnomalyAnalyzeResponse
from backend.app.schemas.meter import MeterLocation, MeterListItem
from backend.app.schemas.alert import AlertItem
from backend.app.schemas.dashboard import DashboardResponse

__all__ = [
    "TelemetryInput",
    "AnomalyAnalyzeRequest",
    "AnomalyAnalyzeResponse",
    "MeterLocation",
    "MeterListItem",
    "AlertItem",
    "DashboardResponse",
]
