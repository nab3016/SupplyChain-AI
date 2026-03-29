"""
app/agents/decision_agent/decision_engine.py
Decision Engine Agent — makes the PROCEED / REROUTE autonomous decision
based on risk score, route data, and configurable thresholds.
"""

from typing import Dict, Any
from app.config.settings import get_settings
from app.utils.helpers import clamp, utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("decision_agent")
settings = get_settings()


def make_decision(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate risk score against the configured threshold and decide on action.

    Decision logic:
        if risk_score > RISK_THRESHOLD → REROUTE
        else                           → PROCEED

    Populates context["decision"] with decision, confidence_score,
    estimated_delay_days, cost_impact_inr, recommended_route.

    Returns:
        Updated context.
    """
    logger.info(f"[{context['trace_id']}] Decision Agent started.")

    risk = context.get("risk", {})
    routes = context.get("routes", {})
    shipment = context.get("shipment", {})
    supplier = context.get("supplier", {})

    risk_score = risk.get("risk_score", 0)
    delay_probability = risk.get("delay_probability", 0)
    confidence = risk.get("confidence", 0.90)

    current_route = routes.get("current", {})
    alternate_route = routes.get("alternate")
    avg_delay_days = supplier.get("avg_delay_days", 3.0)

    threshold = settings.risk_threshold

    # ── Core decision ─────────────────────────────────────────────────────────
    if risk_score > threshold:
        decision = "REROUTE"
        recommended_route = alternate_route if alternate_route else current_route
        decision_reason = (
            f"Risk score {risk_score:.0f} exceeds threshold {threshold}. "
            f"Rerouting to reduce delay probability from {delay_probability:.0%}."
        )
        # Estimated delay on alternate route is lower
        estimated_delay_days = round(avg_delay_days * (1 - 0.60), 1)
        # Cost impact = freight_cost_diff + contingency
        base_cost = current_route.get("freight_cost", 0)
        alt_cost = recommended_route.get("freight_cost", base_cost * 1.10) if recommended_route else base_cost * 1.10
        cost_impact = round(max(alt_cost - base_cost, 0) + (risk_score * 100), 0)
    else:
        decision = "PROCEED"
        recommended_route = current_route
        decision_reason = (
            f"Risk score {risk_score:.0f} is within acceptable threshold ({threshold}). "
            f"Proceeding on current route."
        )
        estimated_delay_days = round(avg_delay_days * delay_probability, 1)
        cost_impact = 0.0

    context["decision"] = {
        "decision": decision,
        "confidence_score": round(clamp(confidence, 0.75, 0.99), 3),
        "estimated_delay_days": estimated_delay_days,
        "cost_impact_inr": cost_impact,
        "recommended_route": recommended_route,
        "decision_reason": decision_reason,
        "risk_threshold_used": threshold,
    }

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "DecisionAgent",
        "action": f"Autonomous Decision: {decision}",
        "status": "SUCCESS",
        "details": decision_reason,
        "timestamp": utc_now_iso(),
    })

    logger.info(f"[{context['trace_id']}] Decision Agent completed | decision={decision} | risk={risk_score:.1f}")
    return context
