"""
app/models/shipment_model.py
Pydantic models for shipment input and parsed CSV records.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional


class ShipmentInput(BaseModel):
    """
    Represents a single shipment submitted through the API or Streamlit form.
    """
    origin: str = Field(..., min_length=2, max_length=100, description="Shipment origin city / hub")
    destination: str = Field(..., min_length=2, max_length=100, description="Shipment destination city / hub")
    supplier_name: str = Field(..., min_length=2, max_length=150, description="Name of the supplying company")
    distance_km: float = Field(..., gt=0, le=50000, description="Route distance in kilometres")
    shipment_value: float = Field(..., gt=0, description="Total shipment value in INR")
    delivery_deadline: date = Field(..., description="Expected delivery date (YYYY-MM-DD)")
    priority: str = Field(default="STANDARD", description="Shipment priority: STANDARD | HIGH | CRITICAL")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        allowed = {"STANDARD", "HIGH", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"priority must be one of {allowed}")
        return v.upper()

    @field_validator("delivery_deadline")
    @classmethod
    def deadline_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("delivery_deadline cannot be in the past")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "origin": "Mumbai",
            "destination": "Delhi",
            "supplier_name": "Apex Logistics Ltd.",
            "distance_km": 1420,
            "shipment_value": 2500000,
            "delivery_deadline": "2025-09-30",
            "priority": "HIGH",
        }
    }}


class ShipmentRecord(BaseModel):
    """
    Parsed record from shipments.csv bulk upload.
    """
    shipment_id: Optional[str] = None
    origin: str
    destination: str
    supplier_name: str
    distance_km: float
    shipment_value: float
    delivery_deadline: str
    priority: str = "STANDARD"
