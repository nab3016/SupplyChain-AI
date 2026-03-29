"""
app/services/supplier_service/supplier_data.py
Loads supplier reliability data from suppliers.csv and provides lookup methods.
"""

import pandas as pd
from typing import Dict, Any, Optional
from pathlib import Path
from app.utils.logger import get_logger
from app.config.settings import get_settings

logger = get_logger("supplier_service")
settings = get_settings()

# Fallback supplier profile when supplier is not found in CSV
DEFAULT_SUPPLIER_PROFILE: Dict[str, Any] = {
    "supplier_name": "Unknown",
    "reliability_score": 0.50,
    "avg_delay_days": 3.0,
    "on_time_rate": 0.50,
    "risk_tier": "MEDIUM",
    "incidents_last_12m": 5,
}


def _load_suppliers() -> pd.DataFrame:
    """Load and return the suppliers CSV as a DataFrame."""
    path = Path(settings.suppliers_csv)
    if not path.exists():
        logger.warning(f"Suppliers CSV not found at {path}. Using fallback data.")
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def get_supplier_profile(supplier_name: str) -> Dict[str, Any]:
    """
    Retrieve a supplier's risk profile from the CSV.

    Args:
        supplier_name: Name of the supplier.

    Returns:
        Dict containing reliability_score, avg_delay_days, on_time_rate,
        risk_tier, and incidents_last_12m.
    """
    df = _load_suppliers()

    if df.empty:
        logger.warning(f"Empty supplier database. Returning default profile for '{supplier_name}'.")
        profile = DEFAULT_SUPPLIER_PROFILE.copy()
        profile["supplier_name"] = supplier_name
        return profile

    # Case-insensitive partial match
    mask = df["supplier_name"].str.lower().str.contains(supplier_name.lower().strip(), na=False)
    match = df[mask]

    if match.empty:
        logger.warning(f"Supplier '{supplier_name}' not found in database. Using default profile.")
        profile = DEFAULT_SUPPLIER_PROFILE.copy()
        profile["supplier_name"] = supplier_name
        return profile

    row = match.iloc[0].to_dict()

    # Normalise field names and types
    profile: Dict[str, Any] = {
        "supplier_name": str(row.get("supplier_name", supplier_name)),
        "reliability_score": float(row.get("reliability_score", 0.50)),
        "avg_delay_days": float(row.get("avg_delay_days", 3.0)),
        "on_time_rate": float(row.get("on_time_rate", 0.50)),
        "risk_tier": str(row.get("risk_tier", "MEDIUM")).upper(),
        "incidents_last_12m": int(row.get("incidents_last_12m", 5)),
    }

    logger.info(f"Supplier profile loaded | {supplier_name} | reliability={profile['reliability_score']:.2f} | tier={profile['risk_tier']}")
    return profile
