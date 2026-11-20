"""
MeterGuard AI: Dashboard Schemas
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class DashboardResponse(BaseModel):
    status: str
    meter_count: int
    meters: List[Dict[str, Any]]
