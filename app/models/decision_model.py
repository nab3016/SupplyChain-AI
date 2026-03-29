"""
app/models/decision_model.py
Pydantic models for decision output and the complete pipeline API response.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class RouteOption(BaseModel):
    """Single route option with cost and time attributes."""
    route_id: str
    route_name: str
    distance_km: float
    estimated_time_hours: float
    freight_cost: float
    risk_score: float
    is_recommended: bool = False
    reason: str = ""


class DecisionResult(BaseModel):
    """Output of the Decision Agent."""
    decision: str = Field(..., description="PROCEED | REROUTE")
    confidence_score: float = Field(..., ge=0, le=1)
    estimated_delay_days: float
    cost_impact_inr: float
    recommended_route: Optional[RouteOption] = None
    decision_reason: str


class ComplianceResult(BaseModel):
    """Output of the Compliance Agent."""
    is_compliant: bool
    sla_check: str = Field(..., description="PASS | FAIL")
    cost_check: str = Field(..., description="PASS | FAIL")
    violations: List[str] = Field(default_factory=list)
    notes: str = ""


class AuditStep(BaseModel):
    """Single step entry in the audit trail."""
    step_number: int
    agent: str
    action: str
    status: str = Field(..., description="SUCCESS | WARNING | FAILED")
    details: str
    timestamp: str


class AnalysisResponse(BaseModel):
    """
    Full pipeline response returned by POST /analyze.
    This is the top-level contract between backend and frontend.
    """
    trace_id: str
    processed_at: str

    # Input echo
    origin: str
    destination: str
    supplier_name: str
    distance_km: float
    shipment_value: float

    # Risk
    risk_score: float
    risk_level: str
    delay_probability: float
    risk_factors: List[Dict[str, Any]]

    # Decision
    decision: str
    confidence_score: float
    estimated_delay_days: float
    cost_impact_inr: float

    # Routes
    current_route: RouteOption
    alternate_route: Optional[RouteOption]
    all_routes: List[RouteOption]

    # Compliance
    compliance: ComplianceResult

    # Explanation
    explanation: str

    # Audit
    audit_log: List[AuditStep]
