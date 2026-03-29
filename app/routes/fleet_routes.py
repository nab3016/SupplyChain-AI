"""
app/routes/fleet_routes.py
Fleet Monitor endpoints — real-time shipment fleet status.

FIX: Removed hardcoded STATUS_MAP and PROGRESS_MAP dummy data.
Status is now derived from the most recent audit log entry for each
shipment route. Progress is computed from delivery_deadline vs today.
"""

import csv
import json
from pathlib import Path
from datetime import datetime, date, timezone
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


def _load_audit_index() -> dict:
    """
    Build a lookup of (origin, destination) -> latest audit record.
    Used to derive real-time status from actual pipeline runs.
    """
    p = Path(settings.audit_log_path)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            logs = json.load(f)
    except Exception:
        return {}

    index: dict = {}
    for log in logs:
        key = (
            (log.get("origin") or "").strip().lower(),
            (log.get("destination") or "").strip().lower(),
        )
        # Keep latest entry per route pair
        existing = index.get(key)
        if existing is None or log.get("timestamp", "") > existing.get("timestamp", ""):
            index[key] = log
    return index


def _derive_status(risk_score: float, decision: str | None) -> str:
    """Map risk score + pipeline decision to a fleet status string."""
    if decision == "REROUTE":
        return "DELAYED"
    if risk_score is None:
        return "IN_TRANSIT"
    if risk_score >= 65:
        return "AT_RISK"
    if risk_score >= 45:
        return "IN_TRANSIT"
    return "ON_SCHEDULE"


def _calc_progress(delivery_deadline_str: str) -> int:
    """
    Estimate progress % from delivery deadline.
    Assumes shipments originate 14 days before deadline.
    Clamps to [5, 95].
    """
    try:
        deadline = date.fromisoformat(delivery_deadline_str)
        today = date.today()
        total_days = 14  # assumed shipment window
        elapsed = total_days - (deadline - today).days
        pct = max(5, min(95, int(elapsed / total_days * 100)))
        return pct
    except Exception:
        return 50


@router.get("/fleet", tags=["Fleet"])
def get_fleet():
    """Return current fleet status for all tracked shipments."""
    shipments = _load_shipments()
    suppliers = _load_suppliers()
    audit_index = _load_audit_index()

    fleet = []
    for s in shipments:
        sid         = s.get("shipment_id", "")
        origin      = s.get("origin", "")
        destination = s.get("destination", "")
        sup         = suppliers.get(s.get("supplier_name", ""), {})

        # Look up most recent audit run for this route
        key         = (origin.strip().lower(), destination.strip().lower())
        audit_entry = audit_index.get(key, {})
        risk_score  = audit_entry.get("risk_score")
        decision    = audit_entry.get("decision")

        status   = _derive_status(risk_score if risk_score is not None else 50.0, decision)
        progress = _calc_progress(s.get("delivery_deadline", ""))
        eta_days = max(1, int((1 - progress / 100) * (float(s.get("distance_km", 1000)) / 600)))
        risk_tier = sup.get("risk_tier", "MEDIUM")

        fleet.append({
            "shipment_id":      sid,
            "origin":           origin,
            "destination":      destination,
            "supplier_name":    s.get("supplier_name", ""),
            "priority":         s.get("priority", "STANDARD"),
            "distance_km":      float(s.get("distance_km", 0)),
            "shipment_value":   float(s.get("shipment_value", 0)),
            "delivery_deadline": s.get("delivery_deadline", ""),
            "status":           status,
            "progress_pct":     progress,
            "eta_days":         eta_days,
            "risk_tier":        risk_tier,
            "reliability_score": float(sup.get("reliability_score", 0.75)),
            "on_time_rate":     float(sup.get("on_time_rate", 0.80)),
            # Live risk score from last audit run (None if never analysed)
            "last_risk_score":  risk_score,
            "last_decision":    decision,
        })

    summary = {
        "total":        len(fleet),
        "on_schedule":  sum(1 for f in fleet if f["status"] == "ON_SCHEDULE"),
        "in_transit":   sum(1 for f in fleet if f["status"] == "IN_TRANSIT"),
        "at_risk":      sum(1 for f in fleet if f["status"] == "AT_RISK"),
        "delayed":      sum(1 for f in fleet if f["status"] == "DELAYED"),
        "total_value_inr": sum(f["shipment_value"] for f in fleet),
    }
    return {"summary": summary, "shipments": fleet}


@router.get("/fleet/{shipment_id}", tags=["Fleet"])
def get_shipment_detail(shipment_id: str):
    """Return detailed info for a single shipment."""
    shipments = _load_shipments()
    suppliers = _load_suppliers()
    audit_index = _load_audit_index()

    for s in shipments:
        if s.get("shipment_id", "").upper() == shipment_id.upper():
            sup    = suppliers.get(s.get("supplier_name", ""), {})
            origin = s.get("origin", "")
            dest   = s.get("destination", "")
            key    = (origin.strip().lower(), dest.strip().lower())
            audit_entry = audit_index.get(key, {})
            risk_score  = audit_entry.get("risk_score")
            decision    = audit_entry.get("decision")

            return {
                **s,
                "status":            _derive_status(risk_score if risk_score is not None else 50.0, decision),
                "progress_pct":      _calc_progress(s.get("delivery_deadline", "")),
                "risk_tier":         sup.get("risk_tier", "MEDIUM"),
                "reliability_score": float(sup.get("reliability_score", 0.75)),
                "incidents_last_12m": int(sup.get("incidents_last_12m", 0)),
                "last_risk_score":   risk_score,
                "last_decision":     decision,
            }
    return {"error": f"Shipment {shipment_id} not found"}
