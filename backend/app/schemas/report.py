"""
MeterGuard AI: Report and Tampering Simulation Schemas (Phase 3B)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Payload to request an AI forensic investigation report."""
    meter_id: str = Field(..., description="Target meter identifier")
    alert_id: Optional[int] = Field(default=None, description="Optional alert identifier to ground against")
    sequence_id: Optional[int] = Field(default=None, description="Optional consumption sequence identifier to ground against")


class ReportResponse(BaseModel):
    """Forensic report details."""
    id: int
    meter_id: str
    alert_id: Optional[int] = None
    report_markdown: str
    model_used: str
    created_at: str
    evidence: Optional[Dict[str, Any]] = None


class SimulateTamperRequest(BaseModel):
    """Payload to launch a 30-day tampering simulation scenario."""
    meter_id: str = Field(..., description="Target meter identifier")
    scenario: str = Field(..., description="Simulation scenario: normal, sudden_drop, abnormally_low_night, flatline, consumption_spike, inversion")
    auto_generate_report: Optional[bool] = Field(default=True, description="Whether to auto-generate a grounded forensic investigation report")


class SimulateTamperResponse(BaseModel):
    """Response payload for a completed tampering simulation and analysis."""
    status: str
    meter_id: str
    scenario: str
    scenario_name: str
    is_simulated: bool = True
    simulated_at: str
    sequence_length: int
    consumption: List[float]
    stats: Dict[str, Any]
    lstm_result: Dict[str, Any]
    alert: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
