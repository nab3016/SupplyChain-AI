"""
app/routes/analytics_routes.py
Analytics endpoints — aggregated risk, route, supplier, and compliance metrics.
"""
import csv
import json
from pathlib import Path
from fastapi import APIRouter
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


def _load_csv(path_str):
    p = Path(path_str)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_audit_logs(limit=200):
    p = Path(settings.audit_log_path)
    if not p.exists():
        return []
    try:
        with open(p, encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-limit:]
    except Exception:
        return []


@router.get("/analytics/overview", tags=["Analytics"])
def get_analytics_overview():
    """High-level KPI summary derived from audit logs and CSV data."""
    shipments = _load_csv(settings.shipments_csv)
    suppliers = _load_csv(settings.suppliers_csv)
    routes = _load_csv(settings.routes_csv)
    logs = _load_audit_logs()

    total_shipments = len(shipments)
    total_value = sum(float(s.get("shipment_value", 0)) for s in shipments)
    high_priority = sum(1 for s in shipments if s.get("priority", "") in ("HIGH", "CRITICAL"))

    avg_reliability = (
        sum(float(s.get("reliability_score", 0)) for s in suppliers) / len(suppliers)
        if suppliers else 0
    )
    high_risk_suppliers = sum(1 for s in suppliers if s.get("risk_tier", "") in ("HIGH", "CRITICAL"))

    avg_route_risk = (
        sum(float(r.get("risk_score", 0)) for r in routes) / len(routes)
        if routes else 0
    )

    decisions = {}
    risk_total = 0
    risk_count = 0
    for log in logs:
        d = log.get("decision", "PROCEED")
        decisions[d] = decisions.get(d, 0) + 1
        rs = log.get("risk_score")
        if rs is not None:
            risk_total += float(rs)
            risk_count += 1

    avg_risk = round(risk_total / risk_count, 1) if risk_count else 0

    return {
        "shipments": {
            "total": total_shipments,
            "total_value_inr": round(total_value),
            "high_priority": high_priority,
            "standard": total_shipments - high_priority,
        },
        "suppliers": {
            "total": len(suppliers),
            "avg_reliability": round(avg_reliability, 2),
            "high_risk_count": high_risk_suppliers,
            "low_risk_count": sum(1 for s in suppliers if s.get("risk_tier") == "LOW"),
        },
        "routes": {
            "total": len(routes),
            "avg_risk_score": round(avg_route_risk, 1),
            "low_risk_routes": sum(1 for r in routes if float(r.get("risk_score", 100)) < 35),
        },
        "pipeline": {
            "total_analyzed": len(logs),
            "avg_risk_score": avg_risk,
            "decisions": decisions,
        },
    }


@router.get("/analytics/risk-distribution", tags=["Analytics"])
def get_risk_distribution():
    """Breakdown of analyzed shipments by risk level from audit logs."""
    logs = _load_audit_logs()
    dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "UNKNOWN": 0}
    for log in logs:
        lvl = str(log.get("risk_level", "UNKNOWN")).upper()
        if lvl in dist:
            dist[lvl] += 1
        else:
            dist["UNKNOWN"] += 1
    return {"distribution": dist, "total": len(logs)}


@router.get("/analytics/supplier-performance", tags=["Analytics"])
def get_supplier_performance():
    """Supplier reliability rankings from CSV."""
    suppliers = _load_csv(settings.suppliers_csv)
    ranked = sorted(
        suppliers,
        key=lambda s: float(s.get("reliability_score", 0)),
        reverse=True,
    )
    return {
        "suppliers": [
            {
                "name": s["supplier_name"],
                "reliability_score": float(s.get("reliability_score", 0)),
                "on_time_rate": float(s.get("on_time_rate", 0)),
                "avg_delay_days": float(s.get("avg_delay_days", 0)),
                "risk_tier": s.get("risk_tier", "MEDIUM"),
                "incidents": int(s.get("incidents_last_12m", 0)),
            }
            for s in ranked
        ]
    }


@router.get("/analytics/route-performance", tags=["Analytics"])
def get_route_performance():
    """Route risk and cost data from CSV."""
    routes = _load_csv(settings.routes_csv)
    return {
        "routes": [
            {
                "route_id": r.get("route_id"),
                "route_name": r.get("route_name"),
                "origin": r.get("origin"),
                "destination": r.get("destination"),
                "distance_km": float(r.get("distance_km", 0)),
                "freight_cost": float(r.get("freight_cost", 0)),
                "risk_score": float(r.get("risk_score", 0)),
                "estimated_time_hours": float(r.get("estimated_time_hours", 0)),
            }
            for r in routes
        ]
    }