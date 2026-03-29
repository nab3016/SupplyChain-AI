"""
app/routes/fleet_routes.py
Fleet Monitor endpoints — real-time shipment fleet status.
"""
import csv
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


def _load_shipments():
    path = Path(settings.shipments_csv)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_suppliers():
    path = Path(settings.suppliers_csv)
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["supplier_name"]: r for r in csv.DictReader(f)}


STATUS_MAP = {
    "SHP-0001": "IN_TRANSIT",
    "SHP-0002": "ON_SCHEDULE",
    "SHP-0003": "DELAYED",
    "SHP-0004": "ON_SCHEDULE",
    "SHP-0005": "AT_RISK",
    "SHP-0006": "ON_SCHEDULE",
    "SHP-0007": "DELAYED",
    "SHP-0008": "ON_SCHEDULE",
    "SHP-0009": "IN_TRANSIT",
    "SHP-0010": "AT_RISK",
}

PROGRESS_MAP = {
    "SHP-0001": 68, "SHP-0002": 45, "SHP-0003": 22,
    "SHP-0004": 89, "SHP-0005": 54, "SHP-0006": 72,
    "SHP-0007": 31, "SHP-0008": 91, "SHP-0009": 60,
    "SHP-0010": 37,
}


@router.get("/fleet", tags=["Fleet"])
def get_fleet():
    """Return current fleet status for all tracked shipments."""
    shipments = _load_shipments()
    suppliers = _load_suppliers()

    fleet = []
    for s in shipments:
        sid = s.get("shipment_id", "")
        sup = suppliers.get(s.get("supplier_name", ""), {})
        status = STATUS_MAP.get(sid, "ON_SCHEDULE")
        progress = PROGRESS_MAP.get(sid, random.randint(20, 90))
        risk_tier = sup.get("risk_tier", "MEDIUM")
        eta_days = max(1, int((1 - progress / 100) * (float(s.get("distance_km", 1000)) / 600)))

        fleet.append({
            "shipment_id": sid,
            "origin": s.get("origin", ""),
            "destination": s.get("destination", ""),
            "supplier_name": s.get("supplier_name", ""),
            "priority": s.get("priority", "STANDARD"),
            "distance_km": float(s.get("distance_km", 0)),
            "shipment_value": float(s.get("shipment_value", 0)),
            "delivery_deadline": s.get("delivery_deadline", ""),
            "status": status,
            "progress_pct": progress,
            "eta_days": eta_days,
            "risk_tier": risk_tier,
            "reliability_score": float(sup.get("reliability_score", 0.75)),
            "on_time_rate": float(sup.get("on_time_rate", 0.80)),
        })

    summary = {
        "total": len(fleet),
        "on_schedule": sum(1 for f in fleet if f["status"] == "ON_SCHEDULE"),
        "in_transit": sum(1 for f in fleet if f["status"] == "IN_TRANSIT"),
        "at_risk": sum(1 for f in fleet if f["status"] == "AT_RISK"),
        "delayed": sum(1 for f in fleet if f["status"] == "DELAYED"),
        "total_value_inr": sum(f["shipment_value"] for f in fleet),
    }
    return {"summary": summary, "shipments": fleet}


@router.get("/fleet/{shipment_id}", tags=["Fleet"])
def get_shipment_detail(shipment_id: str):
    """Return detailed info for a single shipment."""
    shipments = _load_shipments()
    suppliers = _load_suppliers()
    for s in shipments:
        if s.get("shipment_id", "").upper() == shipment_id.upper():
            sup = suppliers.get(s.get("supplier_name", ""), {})
            sid = s["shipment_id"]
            return {
                **s,
                "status": STATUS_MAP.get(sid, "ON_SCHEDULE"),
                "progress_pct": PROGRESS_MAP.get(sid, 50),
                "risk_tier": sup.get("risk_tier", "MEDIUM"),
                "reliability_score": float(sup.get("reliability_score", 0.75)),
                "incidents_last_12m": int(sup.get("incidents_last_12m", 0)),
            }
    return {"error": f"Shipment {shipment_id} not found"}