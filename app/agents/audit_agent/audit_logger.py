"""
app/agents/audit_agent/audit_logger.py
Audit Logger Agent — persists the full pipeline trace to audit_logs.json
and appends a final audit record to the context.

FIX: Audit records are now stored in a FLAT structure so the frontend
renderAuditHistory() and the export endpoints can read fields directly
without nested traversal.
"""

import json
import os
from typing import Dict, Any
from pathlib import Path
from app.config.settings import get_settings
from app.utils.helpers import utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("audit_agent")
settings = get_settings()


def _load_existing_logs() -> list:
    """Load existing audit log entries from JSON file."""
    path = Path(settings.audit_log_path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load existing audit logs: {e}")
        return []


def _save_logs(logs: list) -> None:
    """Persist audit log list to JSON file."""
    path = Path(settings.audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, default=str)
    except OSError as e:
        logger.error(f"Failed to write audit log: {e}")


def persist_audit_log(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialise the full pipeline context into a flat audit record
    and append it to logs/audit_logs.json.

    The record is stored FLAT so that:
      - GET /audit/logs can serve it directly to the frontend
      - GET /export/audit-logs/csv can read fields without nested traversal
      - renderAuditHistory() in index.html works without remapping

    Returns:
        Updated context with final audit step appended.
    """
    logger.info(f"[{context['trace_id']}] Audit Agent started.")

    risk       = context.get("risk", {})
    decision   = context.get("decision", {})
    compliance = context.get("compliance", {})
    shipment   = context.get("shipment", {})

    # ── FLAT audit record ────────────────────────────────────────────────────
    audit_record = {
        # Identity
        "trace_id":          context["trace_id"],
        "timestamp":         context.get("started_at", utc_now_iso()),
        "completed_at":      utc_now_iso(),

        # Shipment (flat — mirrors what the frontend reads)
        "origin":            shipment.get("origin"),
        "destination":       shipment.get("destination"),
        "supplier_name":     shipment.get("supplier_name"),
        "distance_km":       shipment.get("distance_km"),
        "shipment_value":    shipment.get("shipment_value"),
        "priority":          shipment.get("priority"),

        # Risk (flat)
        "risk_score":        risk.get("risk_score"),
        "risk_level":        risk.get("risk_level"),
        "delay_probability": risk.get("delay_probability"),

        # Decision (flat)
        "decision":          decision.get("decision"),
        "confidence_score":  decision.get("confidence_score"),
        "estimated_delay_days": decision.get("estimated_delay_days"),
        "cost_impact_inr":   decision.get("cost_impact_inr"),

        # Compliance (flat)
        "is_compliant":      compliance.get("is_compliant"),
        "violations":        compliance.get("violations", []),

        # Full pipeline trace (kept for deep-drill / raw view)
        "pipeline_steps":    context.get("audit_steps", []),
        "total_steps":       len(context.get("audit_steps", [])),
    }

    existing = _load_existing_logs()
    existing.append(audit_record)

    # Keep only last 500 records to prevent unbounded growth
    if len(existing) > 500:
        existing = existing[-500:]

    _save_logs(existing)

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent":       "AuditAgent",
        "action":      "Persist Audit Record",
        "status":      "SUCCESS",
        "details":     f"Audit record {context['trace_id']} written to {settings.audit_log_path}",
        "timestamp":   utc_now_iso(),
    })

    logger.info(f"[{context['trace_id']}] Audit Agent completed | record saved.")
    return context
