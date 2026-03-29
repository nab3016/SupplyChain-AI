"""
app/routes/api_routes.py
FastAPI router — exposes POST /analyze and GET /health endpoints.
Orchestrates the full multi-agent pipeline on each analysis request.
"""

import json
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse

from app.models.shipment_model import ShipmentInput
from app.models.decision_model import AnalysisResponse, RouteOption, ComplianceResult, AuditStep

from app.agents.data_agent.data_collector import collect_data
from app.agents.risk_agent.risk_calculator import calculate_risk
from app.agents.decision_agent.decision_engine import make_decision
from app.agents.route_agent.route_optimizer import optimize_routes
from app.agents.compliance_agent.rules_engine import check_compliance
from app.agents.llm_agent.explanation_generator import generate_llm_explanation
from app.agents.audit_agent.audit_logger import persist_audit_log
from app.services.file_service.csv_parser import parse_shipment_csv

from app.utils.helpers import generate_trace_id, build_pipeline_context, utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("api_routes")
router = APIRouter()


def _run_pipeline(shipment_dict: Dict[str, Any]) -> AnalysisResponse:
    """
    Execute the full 7-agent pipeline for a single shipment.

    Agent execution order:
        1. DataAgent      → fetch weather, supplier, routes
        2. RiskAgent      → compute risk score
        3. RouteAgent     → optimise alternate routes
        4. DecisionAgent  → PROCEED / REROUTE
        5. ComplianceAgent→ SLA + cost validation
        6. LLMAgent       → generate explanation
        7. AuditAgent     → persist full trace

    Args:
        shipment_dict: Validated shipment input as plain dict.

    Returns:
        AnalysisResponse Pydantic model.
    """
    trace_id = generate_trace_id()
    context = build_pipeline_context(trace_id, shipment_dict)

    logger.info(f"Pipeline START | trace={trace_id} | {shipment_dict.get('origin')} → {shipment_dict.get('destination')}")

    # ── Agent chain ──────────────────────────────────────────────────────────
    context = collect_data(context)
    context = calculate_risk(context)
    context = optimize_routes(context)
    context = make_decision(context)
    context = check_compliance(context)
    context = generate_llm_explanation(context)
    context = persist_audit_log(context)

    logger.info(f"Pipeline END   | trace={trace_id} | decision={context['decision'].get('decision')}")

    # ── Build response ───────────────────────────────────────────────────────
    risk = context["risk"]
    decision = context["decision"]
    routes = context["routes"]
    compliance = context["compliance"]

    def _to_route_option(r: Dict) -> RouteOption:
        return RouteOption(
            route_id=str(r.get("route_id", "N/A")),
            route_name=str(r.get("route_name", "Unknown Route")),
            distance_km=float(r.get("distance_km", 0)),
            estimated_time_hours=float(r.get("estimated_time_hours", 0)),
            freight_cost=float(r.get("freight_cost", 0)),
            risk_score=float(r.get("risk_score", 0)),
            is_recommended=bool(r.get("is_recommended", False)),
            reason=str(r.get("reason", "")),
        )

    current_route_raw = routes.get("current", {})
    alternate_route_raw = routes.get("alternate")
    all_routes_raw = routes.get("ranked", routes.get("options", []))

    current_route = _to_route_option(current_route_raw) if current_route_raw else _to_route_option({
        "route_id": "RT-000", "route_name": "Default Route",
        "distance_km": shipment_dict.get("distance_km", 0),
        "estimated_time_hours": 48, "freight_cost": 0, "risk_score": 50,
    })

    alternate_route = _to_route_option(alternate_route_raw) if alternate_route_raw else None
    all_routes = [_to_route_option(r) for r in all_routes_raw] if all_routes_raw else [current_route]

    compliance_result = ComplianceResult(
        is_compliant=compliance.get("is_compliant", True),
        sla_check=compliance.get("sla_check", "PASS"),
        cost_check=compliance.get("cost_check", "PASS"),
        violations=compliance.get("violations", []),
        notes=compliance.get("notes", ""),
    )

    audit_steps = [
        AuditStep(
            step_number=s["step_number"],
            agent=s["agent"],
            action=s["action"],
            status=s["status"],
            details=s["details"],
            timestamp=s["timestamp"],
        )
        for s in context.get("audit_steps", [])
    ]

    return AnalysisResponse(
        trace_id=trace_id,
        processed_at=utc_now_iso(),
        origin=shipment_dict.get("origin", ""),
        destination=shipment_dict.get("destination", ""),
        supplier_name=shipment_dict.get("supplier_name", ""),
        distance_km=float(shipment_dict.get("distance_km", 0)),
        shipment_value=float(shipment_dict.get("shipment_value", 0)),
        risk_score=risk.get("risk_score", 0),
        risk_level=risk.get("risk_level", "UNKNOWN"),
        delay_probability=risk.get("delay_probability", 0),
        risk_factors=risk.get("risk_factors", []),
        decision=decision.get("decision", "PROCEED"),
        confidence_score=decision.get("confidence_score", 0),
        estimated_delay_days=decision.get("estimated_delay_days", 0),
        cost_impact_inr=decision.get("cost_impact_inr", 0),
        current_route=current_route,
        alternate_route=alternate_route,
        all_routes=all_routes,
        compliance=compliance_result,
        explanation=context.get("explanation", ""),
        audit_log=audit_steps,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Supply Chain AI Agent",
        "timestamp": utc_now_iso(),
    }


@router.post("/analyze", response_model=AnalysisResponse, tags=["Pipeline"])
async def analyze_shipment(shipment: ShipmentInput):
    """
    Run the full 7-agent risk analysis pipeline for a single shipment.

    - Accepts a JSON body matching the ShipmentInput schema.
    - Returns a complete AnalysisResponse with risk, decision, routes, compliance,
      explanation, and audit trail.
    """
    try:
        shipment_dict = shipment.model_dump()
        shipment_dict["delivery_deadline"] = str(shipment_dict["delivery_deadline"])
        result = _run_pipeline(shipment_dict)
        return result
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}",
        )


@router.post("/analyze/csv", tags=["Pipeline"])
async def analyze_csv(file: UploadFile = File(...)):
    """
    Bulk analysis — upload a CSV file containing multiple shipment records.
    Returns a list of AnalysisResponse objects, one per valid row.
    """
    from app.services.file_service.csv_parser import parse_shipment_csv

    content = await file.read()
    records, errors = parse_shipment_csv(content)

    if not records and errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors},
        )

    results = []
    for rec in records:
        try:
            shipment_dict = rec.model_dump()
            results.append(_run_pipeline(shipment_dict).model_dump())
        except Exception as e:
            logger.error(f"CSV row pipeline error: {e}")
            results.append({"error": str(e), "shipment_id": rec.shipment_id})

    return JSONResponse(content={
        "total_records": len(records),
        "processed": len([r for r in results if "error" not in r]),
        "errors_in_csv": errors,
        "results": results,
    })


@router.get("/audit/logs", tags=["Audit"])
async def get_audit_logs(limit: int = 50):
    """Return the last N audit log entries."""
    from pathlib import Path
    from app.config.settings import get_settings
    settings = get_settings()

    path = Path(settings.audit_log_path)
    if not path.exists():
        return {"logs": [], "total": 0}

    try:
        with open(path, "r", encoding="utf-8") as f:
            logs = json.load(f)
        logs = logs[-limit:] if len(logs) > limit else logs
        return {"logs": logs, "total": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read audit logs: {e}")
