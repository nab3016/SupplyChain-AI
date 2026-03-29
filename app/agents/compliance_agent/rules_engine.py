"""
app/agents/compliance_agent/rules_engine.py
Compliance Agent — validates the recommended decision against SLA deadlines,
cost thresholds, and business rules. Flags violations for manual review.
"""

from typing import Dict, Any, List
from datetime import date, datetime
from app.config.settings import get_settings
from app.utils.helpers import utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("compliance_agent")
settings = get_settings()


def check_compliance(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run compliance checks against SLA and cost thresholds.

    Rules checked:
        1. SLA check  — estimated_delay_days ≤ sla_max_delay_days
        2. Cost check — recommended route freight_cost ≤ max_cost_threshold
        3. Priority   — CRITICAL shipments always get a manual review flag

    Populates context["compliance"] with is_compliant, sla_check, cost_check,
    violations list, and notes.

    Returns:
        Updated context.
    """
    logger.info(f"[{context['trace_id']}] Compliance Agent started.")

    decision = context.get("decision", {})
    shipment = context.get("shipment", {})
    routes = context.get("routes", {})

    violations: List[str] = []
    notes_parts: List[str] = []

    # ── 1. SLA / Delay check ─────────────────────────────────────────────────
    estimated_delay = decision.get("estimated_delay_days", 0)
    sla_limit = settings.sla_max_delay_days
    sla_check = "PASS"

    if estimated_delay > sla_limit:
        sla_check = "FAIL"
        violations.append(
            f"Estimated delay {estimated_delay:.1f}d exceeds SLA limit of {sla_limit}d."
        )
    else:
        notes_parts.append(f"Delay within SLA ({estimated_delay:.1f}d ≤ {sla_limit}d).")

    # ── 2. Delivery deadline reachability ────────────────────────────────────
    deadline_str = shipment.get("delivery_deadline", "")
    try:
        if isinstance(deadline_str, str):
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        else:
            deadline = deadline_str
        days_remaining = (deadline - date.today()).days
        if days_remaining < estimated_delay:
            sla_check = "FAIL"
            violations.append(
                f"Deadline {deadline} cannot be met: {days_remaining}d remaining, "
                f"estimated delay {estimated_delay:.1f}d."
            )
    except Exception:
        notes_parts.append("Deadline format could not be parsed for SLA check.")

    # ── 3. Cost threshold check ──────────────────────────────────────────────
    recommended_route = decision.get("recommended_route") or routes.get("current", {})
    route_cost = recommended_route.get("freight_cost", 0) if recommended_route else 0
    max_cost = settings.max_cost_threshold
    cost_check = "PASS"

    if route_cost > max_cost:
        cost_check = "FAIL"
        violations.append(
            f"Route freight cost ₹{route_cost:,.0f} exceeds max allowed ₹{max_cost:,.0f}."
        )
    else:
        notes_parts.append(f"Route cost within threshold (₹{route_cost:,.0f} ≤ ₹{max_cost:,.0f}).")

    # ── 4. Priority escalation flag ──────────────────────────────────────────
    priority = shipment.get("priority", "STANDARD")
    if priority == "CRITICAL":
        violations.append("CRITICAL priority shipment — mandatory human review before dispatch.")
        notes_parts.append("CRITICAL shipment flagged for ops team review.")

    # ── 5. Shipment value sanity check ───────────────────────────────────────
    shipment_value = shipment.get("shipment_value", 0)
    if shipment_value > 10_000_000:
        notes_parts.append(
            f"High-value shipment (₹{shipment_value:,.0f}) — insurance verification recommended."
        )

    is_compliant = len(violations) == 0

    context["compliance"] = {
        "is_compliant": is_compliant,
        "sla_check": sla_check,
        "cost_check": cost_check,
        "violations": violations,
        "notes": " | ".join(notes_parts) if notes_parts else "All compliance checks passed.",
    }

    audit_status = "SUCCESS" if is_compliant else "WARNING"
    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "ComplianceAgent",
        "action": "Run Compliance Checks",
        "status": audit_status,
        "details": (
            f"SLA={sla_check}, Cost={cost_check}, "
            f"Compliant={is_compliant}, Violations={len(violations)}"
        ),
        "timestamp": utc_now_iso(),
    })

    logger.info(
        f"[{context['trace_id']}] Compliance Agent completed | "
        f"compliant={is_compliant} | violations={len(violations)}"
    )
    return context
