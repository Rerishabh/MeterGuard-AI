"""
MeterGuard AI: Anomaly Alert Schemas
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AlertItem(BaseModel):
    id: int
    meter_id: str
    source_model: str
    fault_type: str
    severity: str
    message: Optional[str] = None
    is_resolved: bool
    created_at: str

    model_config = {
        "from_attributes": True,
    }
