"""
app/agents/risk_agent/risk_calculator.py
Risk Assessment Agent — computes composite risk score, delay probability,
and enumerates individual risk factors from weather + supplier data.
"""

from typing import Dict, Any, List
from app.utils.helpers import clamp, utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("risk_agent")

# ── Risk weights ─────────────────────────────────────────────────────────────
WEATHER_WEIGHT = 0.55      # Weather is the dominant factor
SUPPLIER_WEIGHT = 0.45     # Supplier reliability is secondary
OPERATIONAL_PENALTY = 5.0  # Base operational risk (port, traffic, etc.)


def _get_risk_level(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def _get_severity_label(weight: float) -> str:
    if weight >= 0.75:
        return "CRITICAL"
    if weight >= 0.55:
        return "HIGH"
    if weight >= 0.30:
        return "MEDIUM"
    return "LOW"


def calculate_risk(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate composite risk score and delay probability.

    Formula:
        weather_risk = weather.corridor_severity * 100
        supplier_risk = (1 - supplier.reliability_score) * 100
        risk_score = (weather_risk * WEATHER_WEIGHT) + (supplier_risk * SUPPLIER_WEIGHT) + OPERATIONAL_PENALTY

    Populates:
        context["risk"] with full RiskResult-compatible dict.

    Returns:
        Updated context.
    """
    weather = context.get("weather", {})
    supplier = context.get("supplier", {})
    shipment = context.get("shipment", {})

    logger.info(f"[{context['trace_id']}] Risk Agent started.")

    # ── Component scores ──────────────────────────────────────────────────────
    corridor_severity = weather.get("corridor_severity", 0.5)
    weather_risk = corridor_severity * 100

    reliability_score = supplier.get("reliability_score", 0.5)
    supplier_risk = (1.0 - reliability_score) * 100

    # Distance-based operational penalty
    distance_km = shipment.get("distance_km", 1000)
    distance_penalty = min((distance_km / 10000) * 10, 5.0)  # max 5 pts

    # Priority escalation
    priority = shipment.get("priority", "STANDARD")
    priority_multiplier = {"STANDARD": 1.0, "HIGH": 1.05, "CRITICAL": 1.10}.get(priority, 1.0)

    raw_score = (
        (weather_risk * WEATHER_WEIGHT) +
        (supplier_risk * SUPPLIER_WEIGHT) +
        OPERATIONAL_PENALTY +
        distance_penalty
    ) * priority_multiplier

    risk_score = round(clamp(raw_score, 0, 100), 1)

    # ── Delay probability ─────────────────────────────────────────────────────
    # Sigmoid-like mapping: score 60 → ~0.55, score 80 → ~0.80
    delay_probability = round(clamp(risk_score / 110, 0.05, 0.95), 3)

    # ── Risk factors list ─────────────────────────────────────────────────────
    risk_factors: List[Dict[str, Any]] = []

    # Weather factors
    alerts = weather.get("active_alerts", [])
    for alert in alerts[:3]:
        risk_factors.append({
            "category": "WEATHER",
            "description": alert,
            "weight": round(corridor_severity, 2),
            "severity": _get_severity_label(corridor_severity),
        })

    if not alerts and corridor_severity > 0.2:
        risk_factors.append({
            "category": "WEATHER",
            "description": f"Moderate weather disruption detected on corridor (severity {corridor_severity:.0%})",
            "weight": round(corridor_severity, 2),
            "severity": _get_severity_label(corridor_severity),
        })

    # Supplier factors
    on_time_rate = supplier.get("on_time_rate", 0.5)
    avg_delay = supplier.get("avg_delay_days", 3.0)
    incidents = supplier.get("incidents_last_12m", 5)

    if reliability_score < 0.70:
        risk_factors.append({
            "category": "SUPPLIER",
            "description": (
                f"{supplier.get('supplier_name', 'Supplier')} reliability score: {reliability_score:.0%}. "
                f"On-time rate: {on_time_rate:.0%}. Avg delay: {avg_delay:.1f}d"
            ),
            "weight": round(1 - reliability_score, 2),
            "severity": _get_severity_label(1 - reliability_score),
        })

    if incidents >= 5:
        risk_factors.append({
            "category": "SUPPLIER",
            "description": f"{incidents} supply chain incidents recorded in the past 12 months",
            "weight": round(min(incidents / 20, 1.0), 2),
            "severity": _get_severity_label(min(incidents / 20, 1.0)),
        })

    # Operational factors
    if distance_km > 1000:
        risk_factors.append({
            "category": "OPERATIONAL",
            "description": f"Long-haul route ({distance_km:,.0f} km) increases exposure window",
            "weight": round(distance_penalty / 5, 2),
            "severity": "LOW" if distance_km < 2000 else "MEDIUM",
        })

    risk_level = _get_risk_level(risk_score)

    context["risk"] = {
        "risk_score": risk_score,
        "delay_probability": delay_probability,
        "weather_risk_score": round(weather_risk, 1),
        "supplier_risk_score": round(supplier_risk, 1),
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "confidence": round(clamp(0.95 - (risk_score / 500), 0.75, 0.98), 2),
    }

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "RiskAgent",
        "action": "Calculate Risk Score",
        "status": "SUCCESS",
        "details": (
            f"risk_score={risk_score}, level={risk_level}, "
            f"delay_prob={delay_probability:.0%}, factors={len(risk_factors)}"
        ),
        "timestamp": utc_now_iso(),
    })

    logger.info(f"[{context['trace_id']}] Risk Agent completed | score={risk_score} | level={risk_level}")
    return context
