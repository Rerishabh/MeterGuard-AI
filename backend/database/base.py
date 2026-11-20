"""
MeterGuard AI: Declarative Base Module
Serves as the root metadata container for SQLAlchemy ORM models.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import models below so Base.metadata contains all model definitions
from backend.app.models.db_models import (  # noqa: E402, F401
    Meter,
    HardwareReading,
    ConsumptionSequence,
    AnomalyAlert,
    InvestigationReport,
)
