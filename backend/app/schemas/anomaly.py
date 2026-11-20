"""
MeterGuard AI: Anomaly Analysis Schemas
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class AnomalyAnalyzeRequest(BaseModel):
    """Payload for sequential consumption anomaly analysis (/api/anomaly/analyze)."""
    meter_id: str = Field(..., description="Target meter identifier")
    sequence_type: str = Field(..., description="'daily' (30 values) or 'hourly' (24 values)")
    consumption: List[Any] = Field(..., description="Sequential kWh observations")
    is_simulated: Optional[bool] = Field(default=False, description="Whether the sequence is synthetic/simulated")


class AnomalyAnalyzeResponse(BaseModel):
    """Response payload for anomaly analysis."""
    status: str
    meter_id: str
    sequence_type: str
    sequence_length: int
    reconstruction_error: Optional[float] = None
    threshold: Optional[float] = None
    threshold_99: Optional[float] = None
    is_anomaly: bool
    timestamp: str
