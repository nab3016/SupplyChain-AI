"""
app/models/risk_model.py
Pydantic models representing the output of the Risk Agent.
"""

from pydantic import BaseModel, Field
from typing import List


class RiskFactor(BaseModel):
    """Individual contributing risk factor."""
    category: str = Field(..., description="Category: WEATHER | SUPPLIER | GEOPOLITICAL | OPERATIONAL")
    description: str = Field(..., description="Human-readable description of the risk factor")
    weight: float = Field(..., ge=0, le=1, description="Contribution weight (0–1)")
    severity: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")


class RiskResult(BaseModel):
    """Full output of the Risk Assessment Agent."""
    risk_score: float = Field(..., ge=0, le=100, description="Composite risk score 0–100")
    delay_probability: float = Field(..., ge=0, le=1, description="Probability of delay (0–1)")
    weather_risk_score: float = Field(..., ge=0, le=100)
    supplier_risk_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1, description="Model confidence in the risk estimate")
