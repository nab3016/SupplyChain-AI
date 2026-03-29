"""
app/agents/data_agent/data_collector.py
Data Collection Agent — orchestrates all external data fetches
(weather, supplier profile, route options) and populates the pipeline context.
"""

from typing import Dict, Any
from app.services.weather_service.weather_api import get_weather_data
from app.services.supplier_service.supplier_data import get_supplier_profile
from app.services.route_service.route_data import get_all_routes
from app.utils.helpers import utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("data_agent")


def collect_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch all required external data and enrich the pipeline context.

    Populates:
        context["weather"]   — corridor weather data
        context["supplier"]  — supplier risk profile
        context["routes"]    — available route options

    Args:
        context: Shared pipeline context dict (mutated in place).

    Returns:
        Updated context dict with weather, supplier, and route data populated.
    """
    shipment = context["shipment"]
    origin = shipment["origin"]
    destination = shipment["destination"]
    supplier_name = shipment["supplier_name"]

    logger.info(f"[{context['trace_id']}] Data Agent started | {origin} → {destination}")

    # ── 1. Weather data ──────────────────────────────────────────────────────
    try:
        weather_data = get_weather_data(origin, destination)
        context["weather"] = weather_data
        audit_status = "SUCCESS"
        audit_details = (
            f"Weather fetched: corridor_severity={weather_data['corridor_severity']:.2f}, "
            f"alerts={len(weather_data['active_alerts'])}"
        )
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        context["weather"] = {"risk_score": 50, "corridor_severity": 0.5, "active_alerts": [], "error": str(e)}
        audit_status = "WARNING"
        audit_details = f"Weather fetch failed, using defaults. Error: {e}"

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "DataAgent",
        "action": "Fetch Weather Data",
        "status": audit_status,
        "details": audit_details,
        "timestamp": utc_now_iso(),
    })

    # ── 2. Supplier profile ──────────────────────────────────────────────────
    try:
        supplier_profile = get_supplier_profile(supplier_name)
        context["supplier"] = supplier_profile
        audit_status = "SUCCESS"
        audit_details = (
            f"Supplier '{supplier_name}' loaded: reliability={supplier_profile['reliability_score']:.2f}, "
            f"tier={supplier_profile['risk_tier']}"
        )
    except Exception as e:
        logger.error(f"Supplier fetch failed: {e}")
        context["supplier"] = {"reliability_score": 0.5, "avg_delay_days": 3, "risk_tier": "MEDIUM", "error": str(e)}
        audit_status = "WARNING"
        audit_details = f"Supplier lookup failed, using defaults. Error: {e}"

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "DataAgent",
        "action": "Load Supplier Profile",
        "status": audit_status,
        "details": audit_details,
        "timestamp": utc_now_iso(),
    })

    # ── 3. Route options ─────────────────────────────────────────────────────
    try:
        routes = get_all_routes(origin, destination)
        context["routes"]["options"] = routes
        audit_status = "SUCCESS"
        audit_details = f"{len(routes)} route(s) loaded for {origin} → {destination}"
    except Exception as e:
        logger.error(f"Route fetch failed: {e}")
        context["routes"]["options"] = []
        audit_status = "WARNING"
        audit_details = f"Route fetch failed. Error: {e}"

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "DataAgent",
        "action": "Load Route Options",
        "status": audit_status,
        "details": audit_details,
        "timestamp": utc_now_iso(),
    })

    logger.info(f"[{context['trace_id']}] Data Agent completed.")
    return context
