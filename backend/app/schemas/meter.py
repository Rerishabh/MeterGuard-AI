"""
MeterGuard AI: Meter Schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class MeterLocation(BaseModel):
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MeterListItem(BaseModel):
    meter_id: str
    online: bool
    location: MeterLocation
