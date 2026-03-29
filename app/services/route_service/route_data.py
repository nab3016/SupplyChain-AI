"""
app/services/route_service/route_data.py
Loads route options from routes.csv and returns structured route objects.
"""

import pandas as pd
from typing import List, Dict, Any
from pathlib import Path
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger("route_service")
settings = get_settings()

# Fallback routes when CSV is unavailable
FALLBACK_ROUTES: List[Dict[str, Any]] = [
    {
        "route_id": "RT-001",
        "route_name": "NH-48 Primary Corridor",
        "distance_km": 1420.0,
        "estimated_time_hours": 52.0,
        "freight_cost": 42600.0,
        "highway": "NH-48",
        "toll_gates": 12,
        "risk_score": 65.0,
    },
    {
        "route_id": "RT-002",
        "route_name": "NH-44 Bypass (Surat-Vadodara)",
        "distance_km": 1535.0,
        "estimated_time_hours": 47.0,
        "freight_cost": 46050.0,
        "highway": "NH-44",
        "toll_gates": 15,
        "risk_score": 28.0,
    },
    {
        "route_id": "RT-003",
        "route_name": "Express Rail Freight",
        "distance_km": 1380.0,
        "estimated_time_hours": 36.0,
        "freight_cost": 55200.0,
        "highway": "RAIL",
        "toll_gates": 0,
        "risk_score": 20.0,
    },
]


def _load_routes() -> pd.DataFrame:
    """Load routes CSV as DataFrame."""
    path = Path(settings.routes_csv)
    if not path.exists():
        logger.warning(f"Routes CSV not found at {path}. Using fallback routes.")
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def get_all_routes(origin: str, destination: str) -> List[Dict[str, Any]]:
    """
    Retrieve all available routes between origin and destination.

    Args:
        origin: Origin location.
        destination: Destination location.

    Returns:
        List of route dicts sorted by freight_cost ascending.
    """
    df = _load_routes()

    if df.empty:
        logger.warning("Using fallback route data.")
        routes = FALLBACK_ROUTES.copy()
        for r in routes:
            r["route_name"] = f"{origin} → {destination} via {r.get('highway', 'Road')}"
        return routes

    # Filter by origin/destination if columns exist
    filtered = df.copy()
    if "origin" in df.columns and "destination" in df.columns:
        mask = (
            df["origin"].str.lower().str.contains(origin.lower(), na=False) &
            df["destination"].str.lower().str.contains(destination.lower(), na=False)
        )
        if mask.sum() > 0:
            filtered = df[mask]

    routes = filtered.to_dict(orient="records")

    # Ensure required fields exist
    for i, r in enumerate(routes):
        r.setdefault("route_id", f"RT-{i+1:03d}")
        r.setdefault("risk_score", 40.0)
        r.setdefault("toll_gates", 10)

    logger.info(f"Routes loaded | {origin}→{destination} | {len(routes)} options")
    return sorted(routes, key=lambda x: x.get("freight_cost", 0))
