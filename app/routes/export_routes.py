"""
app/routes/export_routes.py
Export endpoints — download audit logs and reports as CSV or JSON.
"""
import csv
import json
import io
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


def _load_audit_logs():
    p = Path(settings.audit_log_path)
    if not p.exists():
        return []
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


@router.get("/export/audit-logs/json", tags=["Export"])
def export_audit_logs_json():
    """Download all audit logs as a JSON file."""
    logs = _load_audit_logs()
    content = json.dumps(logs, indent=2)
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        io.StringIO(content),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/audit-logs/csv", tags=["Export"])
def export_audit_logs_csv():
    """Download all audit logs as a CSV file."""
    logs = _load_audit_logs()
    if not logs:
        return JSONResponse({"error": "No audit logs found"}, status_code=404)

    output = io.StringIO()
    fields = [
        "trace_id", "timestamp", "origin", "destination",
        "supplier_name", "decision", "risk_score", "risk_level",
        "confidence_score", "delay_days", "cost_impact_inr",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for log in logs:
        writer.writerow({
            "trace_id": log.get("trace_id", ""),
            "timestamp": log.get("timestamp", ""),
            "origin": log.get("origin", ""),
            "destination": log.get("destination", ""),
            "supplier_name": log.get("supplier_name", ""),
            "decision": log.get("decision", ""),
            "risk_score": log.get("risk_score", ""),
            "risk_level": log.get("risk_level", ""),
            "confidence_score": log.get("confidence_score", ""),
            "delay_days": log.get("estimated_delay_days", ""),
            "cost_impact_inr": log.get("cost_impact_inr", ""),
        })

    filename = f"supply_chain_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/shipments/csv", tags=["Export"])
def export_shipments_csv():
    """Download the shipments master data as CSV."""
    p = Path(settings.shipments_csv)
    if not p.exists():
        return JSONResponse({"error": "Shipments file not found"}, status_code=404)
    filename = f"shipments_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        open(p, "rb"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )