"""
app/utils/helpers.py
General utility functions shared across the project.
"""

import uuid
from datetime import datetime
from typing import Any


def generate_trace_id() -> str:
    """Generate a unique trace ID for each pipeline run."""
    return f"SC-{uuid.uuid4().hex[:12].upper()}"


def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def format_inr(amount: float) -> str:
    """Format a number as Indian Rupees string."""
    return f"₹{amount:,.0f}"


def safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """Safe division returning fallback on zero denominator."""
    if denominator == 0:
        return fallback
    return numerator / denominator


def build_pipeline_context(trace_id: str, shipment_data: dict[str, Any]) -> dict[str, Any]:
    """
    Initialise the shared pipeline context dictionary that gets passed through
    every agent in the processing chain.
    """
    return {
        "trace_id": trace_id,
        "started_at": utc_now_iso(),
        "shipment": shipment_data,
        "weather": {},
        "supplier": {},
        "risk": {},
        "decision": {},
        "routes": {},
        "compliance": {},
        "explanation": "",
        "audit_steps": [],
    }
