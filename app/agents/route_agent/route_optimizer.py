"""
app/agents/route_agent/route_optimizer.py
Route Optimization Agent — selects the optimal alternate route based on
risk score, cost, and estimated time when a REROUTE decision is triggered.
"""

from typing import Dict, Any, List, Optional
from app.utils.helpers import utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("route_agent")


def _score_route(route: Dict[str, Any], risk_threshold: float) -> float:
    """
    Composite route scoring function.
    Lower score = better route.
    Weighs risk (50%), time (30%), cost (20%).
    """
    risk = route.get("risk_score", 50)
    time = route.get("estimated_time_hours", 48)
    cost = route.get("freight_cost", 50000)

    # Normalise each dimension (rough ranges)
    risk_norm = risk / 100
    time_norm = time / 72           # 72h max reference
    cost_norm = cost / 100000       # ₹1L reference

    return (risk_norm * 0.50) + (time_norm * 0.30) + (cost_norm * 0.20)


def optimize_routes(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select the primary (current) and best alternate route from available options.
    Annotates routes with is_recommended flag.

    Populates:
        context["routes"]["current"]   — route with highest risk (primary path)
        context["routes"]["alternate"] — best optimised alternate route
        context["routes"]["ranked"]    — all routes sorted by composite score

    Returns:
        Updated context.
    """
    logger.info(f"[{context['trace_id']}] Route Agent started.")

    routes: List[Dict[str, Any]] = context.get("routes", {}).get("options", [])
    risk_score = context.get("risk", {}).get("risk_score", 50)

    if not routes:
        logger.warning("No routes available. Route optimisation skipped.")
        context["audit_steps"].append({
            "step_number": len(context["audit_steps"]) + 1,
            "agent": "RouteAgent",
            "action": "Optimize Routes",
            "status": "WARNING",
            "details": "No route options available in database. Using defaults.",
            "timestamp": utc_now_iso(),
        })
        return context

    # Sort routes by composite score (lower = better)
    scored = sorted(routes, key=lambda r: _score_route(r, risk_score))

    # Current route = highest risk / first in unsorted list (primary path)
    current_route = max(routes, key=lambda r: r.get("risk_score", 0))
    current_route = {**current_route, "is_recommended": False, "reason": "Primary route (current plan)"}

    # Alternate route = best scored route that isn't the current one
    alternate_route: Optional[Dict[str, Any]] = None
    for r in scored:
        if r.get("route_id") != current_route.get("route_id"):
            alternate_route = {
                **r,
                "is_recommended": True,
                "reason": (
                    f"Lower risk score ({r.get('risk_score', 0):.0f} vs "
                    f"{current_route.get('risk_score', 0):.0f}), "
                    f"faster transit ({r.get('estimated_time_hours', 0):.0f}h)"
                ),
            }
            break

    context["routes"]["current"] = current_route
    context["routes"]["alternate"] = alternate_route
    context["routes"]["ranked"] = [
        {**r, "is_recommended": r.get("route_id") == (alternate_route or {}).get("route_id")}
        for r in scored
    ]

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "RouteAgent",
        "action": "Optimize Routes",
        "status": "SUCCESS",
        "details": (
            f"{len(routes)} routes evaluated. "
            f"Current: {current_route.get('route_name', 'N/A')} (risk={current_route.get('risk_score', 0):.0f}). "
            f"Alternate: {alternate_route.get('route_name', 'None') if alternate_route else 'None'}."
        ),
        "timestamp": utc_now_iso(),
    })

    logger.info(f"[{context['trace_id']}] Route Agent completed | {len(routes)} routes evaluated.")
    return context
