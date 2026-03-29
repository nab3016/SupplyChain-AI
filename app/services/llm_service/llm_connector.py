
"""
Live LLM connector using Google Gemini API (google-genai SDK).
Requires LLM_API_KEY in .env — set to your Google AI Studio API key.
Get a free key at: https://aistudio.google.com/app/apikey
Falls back to template-based explanation if the API call fails.
"""

import json
from typing import Dict, Any
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger("llm_service")

_MODEL = "gemini-2.5-flash"

_SYSTEM_PROMPT = (
    "You are a supply chain risk analyst AI. Given structured shipment analysis data, "
    "write a concise 3-5 sentence plain-English explanation of the risk situation and "
    "the recommended decision.\n\n"
    "Rules:\n"
    "- Be direct and factual; cite specific numbers from the data.\n"
    "- Mention the most impactful risk factors first.\n"
    "- If the decision is REROUTE, name the recommended alternate route.\n"
    "- If compliance violations exist, mention them.\n"
    "- End with the confidence score.\n"
    "- Do NOT use bullet points or headers — flowing prose only.\n"
    "- Keep the response to 4-6 complete sentences. Always finish your final sentence fully."
)


def _build_prompt(context: Dict[str, Any]) -> str:
    risk       = context.get("risk", {})
    decision   = context.get("decision", {})
    supplier   = context.get("supplier", {})
    weather    = context.get("weather", {})
    shipment   = context.get("shipment", {})
    compliance = context.get("compliance", {})

    payload = {
        "shipment": {
            "origin":      shipment.get("origin"),
            "destination": shipment.get("destination"),
            "supplier":    supplier.get("supplier_name"),
            "value_inr":   shipment.get("shipment_value"),
            "priority":    shipment.get("priority"),
        },
        "risk": {
            "score":             risk.get("risk_score"),
            "level":             risk.get("risk_level"),
            "delay_probability": f"{risk.get('delay_probability', 0):.0%}",
            "top_factors":       [f["description"] for f in risk.get("risk_factors", [])[:3]],
        },
        "weather": {
            "corridor_severity": f"{weather.get('corridor_severity', 0):.0%}",
            "active_alerts":     weather.get("active_alerts", []),
        },
        "supplier": {
            "reliability":  f"{supplier.get('reliability_score', 0):.0%}",
            "on_time_rate": f"{supplier.get('on_time_rate', 0):.0%}",
        },
        "decision": {
            "action":          decision.get("decision"),
            "confidence":      f"{decision.get('confidence_score', 0):.0%}",
            "estimated_delay": f"{decision.get('estimated_delay_days', 0):.1f} days",
            "cost_impact_inr": decision.get("cost_impact_inr", 0),
            "alternate_route": (
                decision.get("recommended_route", {}).get("route_name")
                if decision.get("recommended_route") else None
            ),
        },
        "compliance": {
            "is_compliant": compliance.get("is_compliant"),
            "violations":   compliance.get("violations", []),
        },
    }

    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Analyse this shipment and explain the decision:\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def _template_fallback(context: Dict[str, Any]) -> str:
    """Template-based explanation used as fallback when API is unavailable."""
    risk       = context.get("risk", {})
    decision   = context.get("decision", {})
    supplier   = context.get("supplier", {})
    weather    = context.get("weather", {})
    shipment   = context.get("shipment", {})
    compliance = context.get("compliance", {})

    risk_score    = risk.get("risk_score", 0)
    delay_prob    = risk.get("delay_probability", 0)
    decision_type = decision.get("decision", "PROCEED")
    confidence    = decision.get("confidence_score", 0)
    supplier_name = supplier.get("supplier_name", "the supplier")
    reliability   = supplier.get("reliability_score", 0.5)
    on_time       = supplier.get("on_time_rate", 0.5)
    origin        = shipment.get("origin", "origin")
    destination   = shipment.get("destination", "destination")
    corridor_sev  = weather.get("corridor_severity", 0)
    alerts        = weather.get("active_alerts", [])
    alt_route     = decision.get("recommended_route", {})
    est_delay     = decision.get("estimated_delay_days", 0)
    cost_impact   = decision.get("cost_impact_inr", 0)

    lines = [
        f"Shipment from {origin} to {destination} has been assessed with a risk score of "
        f"{risk_score:.0f}/100 and a delay probability of {delay_prob:.0%}."
    ]
    if alerts:
        lines.append(
            f"Active weather disruptions: {'; '.join(alerts[:2])}. "
            f"Corridor severity: {corridor_sev:.0%}."
        )
    else:
        lines.append("No major weather alerts are active along the primary corridor.")

    if reliability < 0.6:
        lines.append(
            f"{supplier_name} has a reliability score of {reliability:.0%} with an "
            f"on-time rate of {on_time:.0%}, significantly elevating delay risk."
        )
    else:
        lines.append(f"{supplier_name} maintains a reliability score of {reliability:.0%}.")

    if decision_type == "REROUTE":
        alt_name  = alt_route.get("route_name", "the alternate route") if alt_route else "the alternate route"
        alt_score = alt_route.get("risk_score", 0) if alt_route else 0
        lines.append(
            f"The system recommends REROUTING via {alt_name} (risk score {alt_score:.0f}/100). "
            f"Estimated delay: {est_delay:.1f} day(s). Additional cost: Rs.{cost_impact:,.0f}."
        )
    else:
        lines.append(
            f"Risk levels are within acceptable thresholds. PROCEEDING on current route. "
            f"Estimated delay: {est_delay:.1f} day(s)."
        )

    if compliance.get("is_compliant") is False:
        violations = compliance.get("violations", [])
        lines.append(f"Compliance violations: {'; '.join(violations)}. Manual review recommended.")

    lines.append(f"Decision confidence: {confidence:.0%}.")
    return " ".join(lines)


def generate_explanation(context: Dict[str, Any]) -> str:
    """
    Generate a plain-English explanation via Gemini API.
    Falls back to template on any API error.
    """
    settings      = get_settings()
    api_key       = settings.llm_api_key
    risk_score    = context.get("risk", {}).get("risk_score", 0)
    decision_type = context.get("decision", {}).get("decision", "PROCEED")

    try:
        import requests as _req
        # Direct REST — uses generativelanguage.googleapis.com (free tier, no billing cap)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": _build_prompt(context)}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.5},
        }
        resp = _req.post(url, params={"key": api_key}, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        explanation = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        logger.info(f"LLM explanation generated (Gemini REST) | decision={decision_type} | risk={risk_score:.0f}")
        return explanation

    except Exception as e:
        err = str(e)
        if "400" in err or "API_KEY_INVALID" in err:
            logger.error(f"Gemini key invalid — check LLM_API_KEY in .env. Detail: {err}")
        elif "429" in err:
            logger.warning(f"Gemini quota hit. Using fallback. Detail: {err}")
        else:
            logger.error(f"Gemini REST error: {err}. Using fallback.")

    explanation = _template_fallback(context)
    logger.info(f"LLM explanation generated (fallback template) | decision={decision_type} | risk={risk_score:.0f}")
    return explanation