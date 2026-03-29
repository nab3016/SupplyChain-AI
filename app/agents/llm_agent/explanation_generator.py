"""
app/agents/llm_agent/explanation_generator.py
LLM Explanation Agent — wraps the LLM service and writes the
plain-English explanation into the pipeline context.
"""

from typing import Dict, Any
from app.services.llm_service.llm_connector import generate_explanation
from app.utils.helpers import utc_now_iso
from app.utils.logger import get_logger

logger = get_logger("llm_agent")


def generate_llm_explanation(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call the LLM service to produce a human-readable decision explanation
    and store it in context["explanation"].

    Returns:
        Updated context.
    """
    logger.info(f"[{context['trace_id']}] LLM Agent started.")

    try:
        explanation = generate_explanation(context)
        context["explanation"] = explanation
        audit_status = "SUCCESS"
        audit_details = f"Explanation generated ({len(explanation)} chars)."
    except Exception as e:
        logger.error(f"LLM explanation failed: {e}")
        context["explanation"] = (
            "Explanation generation encountered an error. "
            "Please review the risk score and decision data manually."
        )
        audit_status = "WARNING"
        audit_details = f"LLM explanation failed: {e}"

    context["audit_steps"].append({
        "step_number": len(context["audit_steps"]) + 1,
        "agent": "LLMAgent",
        "action": "Generate Decision Explanation",
        "status": audit_status,
        "details": audit_details,
        "timestamp": utc_now_iso(),
    })

    logger.info(f"[{context['trace_id']}] LLM Agent completed.")
    return context
