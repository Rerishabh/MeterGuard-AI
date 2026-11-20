"""
MeterGuard AI: Telemetry Pydantic Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TelemetryInput(BaseModel):
    """Payload for hardware sensor telemetry (/api/meter-data)."""
    meter_id: str = Field(default="M001", description="Identifier of the meter")
    T1_CS: float = Field(..., description="Transformer 1 Current Sensor ADC")
    T1_VS: float = Field(..., description="Transformer 1 Voltage Sensor ADC")
    T2_CS: float = Field(..., description="Pole 2 Current Sensor ADC")
    T2_VS: float = Field(..., description="Pole 2 Voltage Sensor ADC")
    H1_CS: float = Field(..., description="House 1 Current Sensor ADC")
    H1_VS: float = Field(..., description="House 1 Voltage Sensor ADC")
    time_ms: Optional[int] = Field(default=None, description="ESP32 timestamp in milliseconds")

    model_config = {
        "extra": "allow",
    }
